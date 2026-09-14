import logging
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import Base, engine, SessionLocal
from app.models import ModelRegistryEntry
from app.routers import auth, gateway, keys, wallet, billing, webhooks, admin, catalog

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("afrigate")

app = FastAPI(title="AfriGate API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://afrigate-1front-end.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Simple in-process per-IP rate limiter (Phase 1). Move to Redis before
# running more than one backend instance.
# ---------------------------------------------------------------------------
_request_log: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/webhook/"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = _request_log[client_ip]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= settings.RATE_LIMIT_PER_MINUTE:
        return JSONResponse(status_code=429, content={"detail": "Too many requests. Please slow down."})
    window.append(now)
    return await call_next(request)


SEED_MODELS = [
    # --- Professional tier ---
    dict(slug="openai/gpt-4o-mini", display_name="GPT-4o mini", adapter="openai",
         upstream_model_id="gpt-4o-mini", input_price_per_1m=0.15, output_price_per_1m=0.60,
         context_window=128_000, tier="cheap"),
    dict(slug="openai/gpt-4o", display_name="GPT-4o", adapter="openai",
         upstream_model_id="gpt-4o", input_price_per_1m=2.5, output_price_per_1m=10.0,
         context_window=128_000, tier="professional"),
    dict(slug="anthropic/claude-haiku-4.5", display_name="Claude Haiku 4.5", adapter="anthropic",
         upstream_model_id="claude-haiku-4-5-20251001", input_price_per_1m=1.0, output_price_per_1m=5.0,
         context_window=200_000, tier="cheap"),
    dict(slug="anthropic/claude-sonnet-4.5", display_name="Claude Sonnet 4.5", adapter="anthropic",
         upstream_model_id="claude-sonnet-4-5-20250929", input_price_per_1m=3.0, output_price_per_1m=15.0,
         context_window=200_000, tier="professional"),
    dict(slug="mistral/mistral-large", display_name="Mistral Large", adapter="mistral",
         upstream_model_id="mistral-large-latest", input_price_per_1m=2.0, output_price_per_1m=6.0,
         context_window=128_000, tier="professional"),
    dict(slug="gemini/gemini-3.1-pro", display_name="Gemini 3.1 Pro", adapter="gemini",
         upstream_model_id="gemini-3.1-pro", input_price_per_1m=2.0, output_price_per_1m=12.0,
         context_window=1_000_000, tier="professional"),

    # --- Cheap tier ---
    dict(slug="deepseek/deepseek-chat", display_name="DeepSeek V3", adapter="deepseek",
         upstream_model_id="deepseek-chat", input_price_per_1m=0.28, output_price_per_1m=0.42,
         context_window=64_000, tier="cheap"),
    dict(slug="qwen/qwen-plus", display_name="Qwen Plus", adapter="qwen",
         upstream_model_id="qwen-plus", input_price_per_1m=0.40, output_price_per_1m=1.20,
         context_window=131_000, tier="cheap"),
    dict(slug="mistral/mistral-small", display_name="Mistral Small", adapter="mistral",
         upstream_model_id="mistral-small-latest", input_price_per_1m=0.20, output_price_per_1m=0.60,
         context_window=128_000, tier="cheap"),
    dict(slug="gemini/gemini-3-flash", display_name="Gemini 3 Flash", adapter="gemini",
         upstream_model_id="gemini-3-flash", input_price_per_1m=0.50, output_price_per_1m=3.0,
         context_window=1_000_000, tier="cheap"),
    dict(slug="groq/llama-3.1-70b", display_name="Llama 3.1 70B (Groq)", adapter="groq",
         upstream_model_id="llama-3.1-70b-versatile", input_price_per_1m=0.59, output_price_per_1m=0.79,
         context_window=131_000, tier="cheap"),

    # --- Free tier ---
    dict(slug="groq/llama-3.1-8b-free", display_name="Llama 3.1 8B (Free via Groq)", adapter="groq",
         upstream_model_id="llama-3.1-8b-instant", input_price_per_1m=0.0, output_price_per_1m=0.0,
         context_window=131_000, is_free=True, tier="free"),
    dict(slug="cerebras/llama-3.3-70b-free", display_name="Llama 3.3 70B (Free via Cerebras)", adapter="cerebras",
         upstream_model_id="llama3.3-70b", input_price_per_1m=0.0, output_price_per_1m=0.0,
         context_window=128_000, is_free=True, tier="free"),
    dict(slug="gemini/gemini-3-flash-lite-free", display_name="Gemini 3 Flash-Lite (Free)", adapter="gemini",
         upstream_model_id="gemini-3-flash-lite", input_price_per_1m=0.0, output_price_per_1m=0.0,
         context_window=1_000_000, is_free=True, tier="free"),
    dict(slug="oxalpha/ox-alpha-free", display_name="Ox Alpha (Free)", adapter="oxalpha",
         upstream_model_id="stealth/ox-alpha", input_price_per_1m=0.0, output_price_per_1m=0.0,
         context_window=32_000, is_free=True, tier="free"),
]


def _seed_models_if_empty():
    db = SessionLocal()
    try:
        if db.query(ModelRegistryEntry).count() == 0:
            for m in SEED_MODELS:
                db.add(ModelRegistryEntry(**m))
            db.commit()
            logger.info("Seeded %d starter models into the registry.", len(SEED_MODELS))
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    _seed_models_if_empty()
    from app.scheduler import start_scheduler
    start_scheduler()
    logger.info("AfriGate API starting in '%s' mode.", settings.ENV)


app.include_router(auth.router)
app.include_router(gateway.router)
app.include_router(keys.router)
app.include_router(wallet.router)
app.include_router(billing.router)
app.include_router(webhooks.router)
app.include_router(admin.router)
app.include_router(admin.misc_router)
app.include_router(catalog.router)


@app.get("/")
def health():
    return {"status": "ok", "service": "AfriGate API"}
