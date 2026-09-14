from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    company_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    credit_balance: int


class CreateApiKeyRequest(BaseModel):
    label: Optional[str] = "default"


class ApiKeyResponse(BaseModel):
    id: str
    key_prefix: str
    label: Optional[str]
    is_active: bool
    last_used_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class NewApiKeyResponse(BaseModel):
    full_key: str  # shown ONCE at creation time only
    key: ApiKeyResponse


class ChatMessage(BaseModel):
    role: str
    content: Any


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible request body for POST /v1/chat/completions."""
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024
    stream: Optional[bool] = False


class ModelCatalogEntry(BaseModel):
    slug: str
    display_name: str
    context_window: int
    input_price_per_1m: float
    output_price_per_1m: float
    is_free: bool
    tier: str
    supports_streaming: bool

    class Config:
        from_attributes = True


class AdminModelEntry(BaseModel):
    """Superset of ModelCatalogEntry used on admin endpoints - includes
    fields developers on the public catalog never need to see."""
    slug: str
    display_name: str
    adapter: str
    upstream_model_id: str
    input_price_per_1m: float
    output_price_per_1m: float
    context_window: int
    supports_streaming: bool
    is_alias: bool
    points_to_slug: Optional[str] = None
    is_free: bool
    tier: str
    is_enabled: bool
    deprecated_at: Optional[datetime] = None
    sunset_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminModelUpsertRequest(BaseModel):
    slug: str
    display_name: str
    adapter: str
    upstream_model_id: str
    input_price_per_1m: float = 0.0
    output_price_per_1m: float = 0.0
    context_window: int = 8192
    supports_streaming: bool = True
    is_free: bool = False
    tier: str = "cheap"
    is_enabled: bool = True


class AdminAliasRequest(BaseModel):
    alias_slug: str
    points_to_slug: str


class DepositRequest(BaseModel):
    provider: str = Field(..., pattern="^(pawapay|flutterwave|paystack)$")
    amount_local: float = Field(..., gt=0)
    currency: str = Field(..., pattern="^(TZS|KES|NGN|GHS|UGX)$")
    phone_number: Optional[str] = None
    network: Optional[str] = None  # e.g. MPESA, MTN, AIRTEL - provider-specific


class DepositResponse(BaseModel):
    reference: str
    status: str
    credits_pending: int
    message: str
    checkout_url: Optional[str] = None


class WalletResponse(BaseModel):
    credit_balance: int
    credit_balance_usd: float


class ModelSuggestionResponse(BaseModel):
    id: str
    adapter: str
    upstream_model_id: str
    suggestion_note: str
    status: str
    first_seen_at: datetime

    class Config:
        from_attributes = True


class PlatformSettingsResponse(BaseModel):
    topup_fee_percent: float
    usd_to_tzs: float
    usd_to_kes: float
    usd_to_ngn: float
    usd_to_ghs: float
    usd_to_ugx: float
    fx_auto_update_enabled: bool
    fx_last_synced_at: Optional[datetime] = None
    fx_source: Optional[str] = None

    class Config:
        from_attributes = True


class UpdatePlatformSettingsRequest(BaseModel):
    topup_fee_percent: Optional[float] = Field(None, ge=0, le=50)


class UpdateFxRatesRequest(BaseModel):
    usd_to_tzs: Optional[float] = Field(None, gt=0)
    usd_to_kes: Optional[float] = Field(None, gt=0)
    usd_to_ngn: Optional[float] = Field(None, gt=0)
    usd_to_ghs: Optional[float] = Field(None, gt=0)
    usd_to_ugx: Optional[float] = Field(None, gt=0)


class SetFxAutoUpdateRequest(BaseModel):
    enabled: bool
