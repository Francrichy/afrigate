"""
Flutterwave v3 Charges API - mobile money collections.

Verified pattern (docs + SDK source, Sept 2026):
  POST {base}/charges?type=mobile_money_{country}
  Authorization: Bearer FLUTTERWAVE_SECRET_KEY
  Body: {tx_ref, amount, currency, email, phone_number, fullname, network?}

IMPORTANT: the exact `type` suffix and whether a `network` field is
required varies per country (confirmed values include mobile_money_uganda,
mobile_money_rwanda, mobile_money_ghana, mobile_money_franco/zambia, and
Kenya M-Pesa is typically its own `type=mpesa`). Confirm the exact string
for each country you launch in against your Flutterwave dashboard/docs
before going live - do not assume the mapping below is exhaustive.

Flutterwave is also migrating to a v4 OAuth2 API; v3 (static secret key)
remains supported and is what's implemented here for simplicity.
"""
import httpx
from app.config import get_settings

settings = get_settings()

COUNTRY_TO_CHARGE_TYPE = {
    "KE": "mpesa",
    "UG": "mobile_money_uganda",
    "GH": "mobile_money_ghana",
    "ZM": "mobile_money_zambia",
    "RW": "mobile_money_rwanda",
    "TZ": "mobile_money_tanzania",
}


class FlutterwaveError(Exception):
    pass


async def request_charge(tx_ref: str, amount: float, currency: str, email: str,
                          phone_number: str, fullname: str, country_code: str,
                          network: str | None = None) -> dict:
    if not settings.FLUTTERWAVE_SECRET_KEY:
        raise FlutterwaveError("FLUTTERWAVE_SECRET_KEY not configured")

    charge_type = COUNTRY_TO_CHARGE_TYPE.get(country_code.upper())
    if not charge_type:
        raise FlutterwaveError(f"No Flutterwave mobile money charge type mapped for country '{country_code}'.")

    headers = {"Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}", "Content-Type": "application/json"}
    payload = {
        "tx_ref": tx_ref,
        "amount": str(amount),
        "currency": currency,
        "email": email,
        "phone_number": phone_number,
        "fullname": fullname,
    }
    if network:
        payload["network"] = network

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{settings.FLUTTERWAVE_BASE_URL}/charges?type={charge_type}",
                                  headers=headers, json=payload)
    if resp.status_code not in (200, 201):
        raise FlutterwaveError(f"Flutterwave error {resp.status_code}: {resp.text[:300]}")
    return resp.json()


async def verify_transaction(transaction_id: str) -> dict:
    headers = {"Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{settings.FLUTTERWAVE_BASE_URL}/transactions/{transaction_id}/verify", headers=headers
        )
    if resp.status_code != 200:
        raise FlutterwaveError(f"Flutterwave verify error {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def verify_webhook_signature(received_hash: str) -> bool:
    """Flutterwave sends the value you configured as 'verif-hash' in your
    dashboard back in the 'verif-hash' request header - compare directly."""
    return bool(settings.FLUTTERWAVE_WEBHOOK_HASH) and received_hash == settings.FLUTTERWAVE_WEBHOOK_HASH
