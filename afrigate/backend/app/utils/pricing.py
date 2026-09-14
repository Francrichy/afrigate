"""
Wallet/credit math. 1 credit = $0.00001 USD (integer "USD micro-units")
so we never lose precision on tiny per-token charges - everything is
integer arithmetic, no floats touch the actual ledger.
"""
from app.config import get_settings

settings = get_settings()

CREDITS_PER_USD = 100_000  # 1 credit = $0.00001


def usd_to_credits(usd: float) -> int:
    return int(round(usd * CREDITS_PER_USD))


def credits_to_usd(credits: int) -> float:
    return credits / CREDITS_PER_USD


def local_currency_to_usd(amount_local: float, currency: str) -> float:
    rate = {
        "TZS": settings.USD_TO_TZS,
        "KES": settings.USD_TO_KES,
        "NGN": settings.USD_TO_NGN,
    }.get(currency)
    if not rate:
        raise ValueError(f"No FX rate configured for currency '{currency}'.")
    return amount_local / rate


def calculate_topup_credits(amount_local: float, currency: str, fee_percent: float | None = None) -> tuple[int, int]:
    """
    Returns (net_credits_to_wallet, fee_credits_kept_by_platform).
    `fee_percent` should come from PlatformSettings (see utils/settings.py)
    so an admin can change it from the dashboard without touching .env or
    redeploying. Falls back to the .env default only if not provided.
    """
    usd = local_currency_to_usd(amount_local, currency)
    gross_credits = usd_to_credits(usd)
    effective_fee_percent = settings.TOPUP_FEE_PERCENT if fee_percent is None else fee_percent
    fee_credits = int(round(gross_credits * effective_fee_percent / 100))
    net_credits = gross_credits - fee_credits
    return net_credits, fee_credits


def calculate_request_cost(prompt_tokens: int, completion_tokens: int,
                            input_price_per_1m: float, output_price_per_1m: float) -> int:
    """Pass-through pricing - no per-token markup (matches OpenRouter's
    proven model). Margin is captured once, at top-up, via TOPUP_FEE_PERCENT."""
    usd_cost = (prompt_tokens / 1_000_000) * input_price_per_1m + \
               (completion_tokens / 1_000_000) * output_price_per_1m
    return usd_to_credits(usd_cost)
