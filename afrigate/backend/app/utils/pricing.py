"""
Wallet/credit math. 1 credit = $0.00001 USD (integer "USD micro-units")
so we never lose precision on tiny per-token charges - everything is
integer arithmetic, no floats touch the actual ledger.
"""

CREDITS_PER_USD = 100_000  # 1 credit = $0.00001


def usd_to_credits(usd: float) -> int:
    return int(round(usd * CREDITS_PER_USD))


def credits_to_usd(credits: int) -> float:
    return credits / CREDITS_PER_USD


def local_currency_to_usd(platform_settings, amount_local: float, currency: str) -> float:
    """
    `platform_settings` is the PlatformSettings row (see utils/settings.py) -
    rates live in the database now, refreshed daily by utils/fx_rates.py,
    so this reflects today's real rate instead of whatever was hardcoded
    in .env at deploy time.
    """
    rate = {
        "TZS": platform_settings.usd_to_tzs,
        "KES": platform_settings.usd_to_kes,
        "NGN": platform_settings.usd_to_ngn,
        "GHS": platform_settings.usd_to_ghs,
        "UGX": platform_settings.usd_to_ugx,
    }.get(currency)
    if not rate:
        raise ValueError(f"No FX rate configured for currency '{currency}'.")
    return amount_local / rate


def calculate_topup_credits(platform_settings, amount_local: float, currency: str) -> tuple[int, int]:
    """
    Returns (net_credits_to_wallet, fee_credits_kept_by_platform), using
    today's FX rate and the admin-configured fee percent - both pulled
    from PlatformSettings so this always reflects current values with no
    redeploy needed.
    """
    usd = local_currency_to_usd(platform_settings, amount_local, currency)
    gross_credits = usd_to_credits(usd)
    fee_credits = int(round(gross_credits * platform_settings.topup_fee_percent / 100))
    net_credits = gross_credits - fee_credits
    return net_credits, fee_credits


def calculate_request_cost(prompt_tokens: int, completion_tokens: int,
                            input_price_per_1m: float, output_price_per_1m: float) -> int:
    """Pass-through pricing - no per-token markup (matches OpenRouter's
    proven model). Margin is captured once, at top-up, via topup_fee_percent."""
    usd_cost = (prompt_tokens / 1_000_000) * input_price_per_1m + \
               (completion_tokens / 1_000_000) * output_price_per_1m
    return usd_to_credits(usd_cost)
