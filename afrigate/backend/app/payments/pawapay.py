"""
PawaPay v2 - reused from the already-verified SwahiliStudio integration
(request/response shapes were confirmed against PawaPay's official docs
in that project). Used primarily for Tanzania mobile money.
"""
import httpx
from app.config import get_settings

settings = get_settings()


class PawaPayError(Exception):
    pass


async def request_deposit(deposit_id: str, amount: float, currency: str, phone_number: str,
                           correspondent: str, callback_url: str) -> dict:
    if not settings.PAWAPAY_API_TOKEN:
        raise PawaPayError("PAWAPAY_API_TOKEN not configured")

    headers = {"Authorization": f"Bearer {settings.PAWAPAY_API_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "depositId": deposit_id,
        "amount": str(int(amount)),
        "currency": currency,
        "correspondent": correspondent,
        "payer": {"type": "MSISDN", "address": {"value": phone_number}},
        "statementDescription": "AfriGate Credits"[:22],
        "callbackUrl": callback_url,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{settings.PAWAPAY_BASE_URL}/deposits", headers=headers, json=payload)
    if resp.status_code not in (200, 201, 202):
        raise PawaPayError(f"PawaPay error {resp.status_code}: {resp.text[:300]}")
    return resp.json()


async def check_deposit_status(deposit_id: str) -> dict:
    headers = {"Authorization": f"Bearer {settings.PAWAPAY_API_TOKEN}"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{settings.PAWAPAY_BASE_URL}/deposits/{deposit_id}", headers=headers)
    if resp.status_code != 200:
        raise PawaPayError(f"PawaPay error {resp.status_code}: {resp.text[:300]}")
    return resp.json()
