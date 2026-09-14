import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, ForeignKey, Text, Float,
    Enum as SAEnum, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class DepositStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)

    # Credits are stored as integer USD-millicents (1 credit = $0.00001)
    # for precise, rounding-free arithmetic across many tiny token charges.
    credit_balance = Column(Integer, nullable=False, default=0)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    deposits = relationship("Deposit", back_populates="user", cascade="all, delete-orphan")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key_prefix = Column(String(16), nullable=False)  # shown in UI, e.g. "ag_live_9f2a"
    key_hash = Column(String(255), nullable=False)   # sha256 of the full key - full key never stored
    label = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="api_keys")


class ModelRegistryEntry(Base):
    """
    The Model Registry. `slug` is what developers put in their request
    (e.g. "anthropic/claude-sonnet-4.5" or an alias like "claude-latest").
    `is_alias`+`points_to_slug` implements version aliasing so admins can
    upgrade a model for everyone without breaking pinned integrations.
    """
    __tablename__ = "model_registry"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    slug = Column(String(120), unique=True, nullable=False, index=True)
    display_name = Column(String(150), nullable=False)
    adapter = Column(String(40), nullable=False)  # "openai" | "anthropic" | "deepseek" | "qwen" | "groq"
    upstream_model_id = Column(String(150), nullable=False)  # the real model id sent to the provider

    input_price_per_1m = Column(Float, nullable=False, default=0.0)   # USD per 1M input tokens
    output_price_per_1m = Column(Float, nullable=False, default=0.0)  # USD per 1M output tokens
    context_window = Column(Integer, nullable=False, default=8192)
    supports_streaming = Column(Boolean, default=True, nullable=False)

    is_alias = Column(Boolean, default=False, nullable=False)
    points_to_slug = Column(String(120), nullable=True)

    is_free = Column(Boolean, default=False, nullable=False)
    tier = Column(String(20), nullable=False, default="cheap")  # "free" | "cheap" | "professional" - catalog grouping only, doesn't affect billing math
    is_enabled = Column(Boolean, default=True, nullable=False)
    deprecated_at = Column(DateTime, nullable=True)
    sunset_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class UsageLog(Base):
    __tablename__ = "usage_log"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    model_slug = Column(String(120), nullable=False)
    resolved_slug = Column(String(120), nullable=False)  # after alias resolution
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    credits_charged = Column(Integer, nullable=False, default=0)
    routing_mode = Column(String(20), nullable=True)  # "default" | "floor" | "nitro"
    latency_ms = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="success")  # success | error
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class Deposit(Base):
    __tablename__ = "deposits"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    reference = Column(String(80), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    provider = Column(String(20), nullable=False)  # "pawapay" | "flutterwave" | "paystack"
    amount_local = Column(Float, nullable=False)
    currency = Column(String(6), nullable=False)   # TZS | KES | NGN | GHS ...
    phone_number = Column(String(20), nullable=True)

    credits_purchased = Column(Integer, nullable=False)  # gross credits before fee
    fee_credits = Column(Integer, nullable=False, default=0)

    status = Column(SAEnum(DepositStatus, name="deposit_status"), nullable=False, default=DepositStatus.PENDING)
    credited = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="deposits")


class WebhookEvent(Base):
    """Idempotency ledger - every inbound payment webhook is recorded here
    BEFORE processing, so a retried delivery from any of the 3 payment
    providers can never double-credit a wallet."""
    __tablename__ = "webhook_events"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    source = Column(String(20), nullable=False)  # "pawapay" | "flutterwave" | "paystack"
    external_event_id = Column(String(150), nullable=False)
    payload = Column(Text, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("source", "external_event_id", name="uq_webhook_source_event"),
    )


class ModelSuggestion(Base):
    """
    Populated by the daily model-discovery job (see utils/model_discovery.py).
    When a provider's own model list contains an id we don't have in our
    ModelRegistryEntry yet, we record it here with a short plain-language
    note so a non-technical admin can decide whether to add it - without
    needing to read provider changelogs themselves.
    """
    __tablename__ = "model_suggestions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    adapter = Column(String(40), nullable=False)
    upstream_model_id = Column(String(150), nullable=False)
    suggestion_note = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="new")  # "new" | "added" | "dismissed"
    first_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("adapter", "upstream_model_id", name="uq_suggestion_adapter_model"),
    )


class PlatformSettings(Base):
    """
    Single-row table of platform-wide settings an admin can change from the
    dashboard (no redeploy, no .env edit, no code). Row id is always
    'default' - see utils/settings.py for the get-or-create helper.
    """
    __tablename__ = "platform_settings"

    id = Column(String(20), primary_key=True, default="default")
    topup_fee_percent = Column(Float, nullable=False, default=12.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
