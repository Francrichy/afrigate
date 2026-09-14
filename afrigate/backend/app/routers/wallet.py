from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UsageLog
from app.schemas import WalletResponse
from app.security import get_current_user
from app.utils.pricing import credits_to_usd

router = APIRouter(prefix="/api/wallet", tags=["wallet"])


@router.get("", response_model=WalletResponse)
def get_wallet(user: User = Depends(get_current_user)):
    return WalletResponse(credit_balance=user.credit_balance, credit_balance_usd=credits_to_usd(user.credit_balance))


@router.get("/usage")
def get_usage(user: User = Depends(get_current_user), db: Session = Depends(get_db), limit: int = 100):
    rows = (
        db.query(UsageLog)
        .filter(UsageLog.user_id == user.id)
        .order_by(UsageLog.created_at.desc())
        .limit(min(limit, 500))
        .all()
    )
    return [
        {
            "model_slug": r.model_slug,
            "resolved_slug": r.resolved_slug,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "credits_charged": r.credits_charged,
            "cost_usd": credits_to_usd(r.credits_charged),
            "routing_mode": r.routing_mode,
            "latency_ms": r.latency_ms,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
