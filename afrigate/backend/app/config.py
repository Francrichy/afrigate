from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 30
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_PUBLIC_URL: str = "http://localhost:8000"

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/afrigate"

    # --- Pricing / wallet ---
    # Internal accounting peg: 1 credit = 1 USD-cent equivalent, converted
    # to a display currency at TOP-UP time only (never re-converted after,
    # to avoid retroactively changing a user's balance value on FX moves).
    TOPUP_FEE_PERCENT: float = 12.0  # covers Mobile Money settlement float + FX risk (seed default only - see PlatformSettings for the live, admin-editable value)
    # FX rates (USD_TO_TZS etc.) now live in PlatformSettings (models.py),
    # auto-synced daily from open.er-api.com by utils/fx_rates.py, and
    # editable by an admin from the dashboard. Nothing to configure here.

    # --- AI provider keys (server-side, used for non-BYOK requests) ---
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    GROQ_API_KEY: str = ""
    CEREBRAS_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""
    OXALPHA_API_KEY: str = ""
    OXALPHA_BASE_URL: str = "https://tokenra.io/v1"

    # --- Payments ---
    PAWAPAY_API_TOKEN: str = ""
    PAWAPAY_BASE_URL: str = "https://api.sandbox.pawapay.io"
    PAWAPAY_CALLBACK_URL: str = ""

    FLUTTERWAVE_SECRET_KEY: str = ""
    FLUTTERWAVE_BASE_URL: str = "https://api.flutterwave.com/v3"
    FLUTTERWAVE_WEBHOOK_HASH: str = ""  # "verif-hash" value you set on the FLW dashboard

    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_BASE_URL: str = "https://api.paystack.co"

    RATE_LIMIT_PER_MINUTE: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
