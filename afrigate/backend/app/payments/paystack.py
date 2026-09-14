"""
Paystack Charge API - mobile money collections.

Verified pattern (docs, Sept 2026):
  POST {base}/charge
  Authorization: Bearer PAYSTACK_SECRET_KEY
  Body: {email, amount (in subunit - kobo/cents), currency,
         mobile_money: {phone, provider}}

Mobile Money via Paystack is officially supported ONLY in Ghana, Kenya,
and Côte d'Ivoire (confirmed in their docs) - route Nigeria/other
countries through Flutterwave or PawaPay instead. `provider` is one of:
mtn | atl | vod | mpesa | orange | wave.

Webhook: Paystack POSTs a `charge.success` (or failure) event to your
webhook URL, signed via an `x-paystack-signature` HMAC-SHA512 header
using your secret key - verify this before trusting any webhook body.
"""
import hmac
import hashlib
import httpx
from app.config import get_settings

settings = get_settings()

SUPPORTED_COUNTRIES = {"GH", "KE", "CI"}


class PaystackError(Exception):
    pass


async def request_charge(reference: str, amount_local: float, currency: str, email: str,
                          phone_number: str, provider: str, country_code: str) -> dict:
    if not settings.PAYSTACK_SECRET_KEY:
        raise PaystackError("PAYSTACK_SECRET_KEY not configured")
    if country_code.upper() not in SUPPORTED_COUNTRIES:
        raise PaystackError(
            f"Paystack Mobile Money isn't available in '{country_code}' - route via Flutterwave or PawaPay."
        )

    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}
    # Paystack amounts are in the currency's smallest subunit (kobo/pesewas/cents)
    payload = {
        "email": email,
        "amount": str(int(round(amount_local * 100))),
        "currency": currency,
        "reference": reference,
        "mobile_money": {"phone": phone_number, "provider": provider},
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{settings.PAYSTACK_BASE_URL}/charge", headers=headers, json=payload)
    if resp.status_code not in (200, 201):
        raise PaystackError(f"Paystack error {resp.status_code}: {resp.text[:300]}")
    return resp.json()


async def verify_transaction(reference: str) -> dict:
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}", headers=headers)
    if resp.status_code != 200:
        raise PaystackError(f"Paystack verify error {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def verify_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
    if not settings.PAYSTACK_SECRET_KEY or not signature_header:
        return False
    computed = hmac.new(settings.PAYSTACK_SECRET_KEY.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, signature_header)
