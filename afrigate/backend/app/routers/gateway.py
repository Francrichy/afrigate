"""
The core product: an OpenAI-compatible /v1/chat/completions endpoint.
A developer changes only base_url + api_key in their existing OpenAI SDK
code - nothing else - and every request here:

  1. Authenticates via API key (ag_live_...)
  2. Resolves the model string (alias + :floor/:nitro routing modifier)
  3. Debits the wallet ATOMICALLY *before* calling upstream (never let a
     user go negative under concurrent requests)
  4. Calls the resolved provider adapter, falling back through
     `fallback_entries` on any retryable AdapterError
  5. Refunds the wallet precisely if every attempt fails
  6. Logs usage for the dashboard's analytics view
"""
import time
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UsageLog, ModelRegistryEntry
from app.schemas import ChatCompletionRequest
from app.security import get_user_by_api_key
from app.adapters import get_adapter
from app.adapters.base import AdapterError
from app.utils.routing import resolve_route
from app.utils.pricing import calculate_request_cost, usd_to_credits

router = APIRouter(tags=["gateway"])
logger = logging.getLogger("gateway")

# A conservative upfront hold so we never let balance go negative under
# concurrent requests before we know the real token cost. Refunded/adjusted
# to the exact cost once the response comes back.
PROVISIONAL_HOLD_USD = 0.50


def _lock_user(db: Session, user_id: str) -> User:
    return db.execute(select(User).where(User.id == user_id).with_for_update()).scalar_one()


@router.post("/v1/chat/completions")
async def chat_completions(
    body: ChatCompletionRequest,
    user: User = Depends(get_user_by_api_key),
    db: Session = Depends(get_db),
):
    if body.stream:
        raise HTTPException(status_code=400, detail="Streaming is not yet supported on this gateway. Set stream=false.")

    route = resolve_route(db, body.model)
    if not route:
        raise HTTPException(status_code=400, detail=f"Model '{body.model}' was not found in the AfriGate registry.")

    hold_credits = usd_to_credits(PROVISIONAL_HOLD_USD)

    locked_user = _lock_user(db, user.id)
    if not route.entry.is_free and locked_user.credit_balance < hold_credits:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. You need at least {hold_credits} credits held to attempt this request.",
        )
    if not route.entry.is_free:
        locked_user.credit_balance -= hold_credits
    db.commit()

    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    attempt_chain = [route.entry] + route.fallback_entries
    last_error: str = "no route attempted"
    start = time.monotonic()

    for candidate in attempt_chain:
        adapter = get_adapter(candidate.adapter)
        try:
            result = await adapter.chat_completion(
                candidate.upstream_model_id, messages, body.temperature or 0.7, body.max_tokens or 1024
            )
            latency_ms = int((time.monotonic() - start) * 1000)

            real_cost_credits = 0
            if not candidate.is_free:
                real_cost_credits = calculate_request_cost(
                    result.prompt_tokens, result.completion_tokens,
                    candidate.input_price_per_1m, candidate.output_price_per_1m,
                )

            # Reconcile the provisional hold against the real cost, atomically.
            settle_user = _lock_user(db, user.id)
            if not candidate.is_free:
                adjustment = hold_credits - real_cost_credits  # positive = refund difference
                settle_user.credit_balance += adjustment
            else:
                settle_user.credit_balance += hold_credits  # fully refund the hold - it was free

            db.add(UsageLog(
                user_id=user.id, model_slug=body.model, resolved_slug=candidate.slug,
                prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens,
                credits_charged=real_cost_credits, routing_mode=route.routing_mode,
                latency_ms=latency_ms, status="success",
            ))
            db.commit()

            return {
                "id": f"afrigate-{int(time.time() * 1000)}",
                "object": "chat.completion",
                "model": candidate.slug,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": result.content},
                    "finish_reason": result.finish_reason,
                }],
                "usage": {
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "total_tokens": result.prompt_tokens + result.completion_tokens,
                },
            }

        except AdapterError as e:
            last_error = str(e)
            logger.warning("Adapter '%s' failed for slug '%s': %s", candidate.adapter, candidate.slug, e)
            if not e.retryable:
                break
            continue

    # Every attempt in the chain failed - refund the full hold and log the failure.
    refund_user = _lock_user(db, user.id)
    if not route.entry.is_free:
        refund_user.credit_balance += hold_credits
    db.add(UsageLog(
        user_id=user.id, model_slug=body.model, resolved_slug=route.entry.slug,
        prompt_tokens=0, completion_tokens=0, credits_charged=0,
        routing_mode=route.routing_mode, status="error",
    ))
    db.commit()

    raise HTTPException(status_code=502, detail=f"All providers failed for this request. Last error: {last_error}")
