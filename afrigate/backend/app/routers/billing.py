"""
Single top-up endpoint that dispatches to whichever of the 3 payment
adapters the client selects. Country is inferred from currency for
Flutterwave/Paystack's country-specific charge types; PawaPay uses an
explicit correspondent code (see COUNTRY_TO_PAWAPAY_CORRESPONDENT).
"""
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.models import User, Deposit, DepositStatus
from app.schemas import DepositRequest, DepositResponse
from app.security import get_current_user
from app.payments import pawapay, flutterwave, paystack
from app.utils.pricing import calculate_topup_credits
from app.utils.settings import get_platform_settings

router = APIRouter(prefix="/api/billing", tags=["billing"])
logger = logging.getLogger("billing")
settings = get_settings()

CURRENCY_TO_COUNTRY = {"TZS": "TZ", "KES": "KE", "NGN": "NG", "GHS": "GH", "UGX": "UG"}

CURRENCY_NETWORK_TO_PAWAPAY_CORRESPONDENT = {
    ("TZS", "MPESA"): "MPESA_TZA", ("TZS", "TIGO"): "TIGO_TZA",
    ("TZS", "AIRTEL"): "AIRTEL_TZA", ("TZS", "HALOTEL"): "HALOTEL_TZA",
    ("UGX", "MTN"): "MTN_MOMO_UGA", ("UGX", "AIRTEL"): "AIRTEL_UGA",
}


@router.post("/deposit", response_model=DepositResponse)
async def create_deposit(body: DepositRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    platform_settings = get_platform_settings(db)
    net_credits, fee_credits = calculate_topup_credits(body.amount_local, body.currency, platform_settings.topup_fee_percent)
    reference = f"ag_{uuid.uuid4().hex}"
    country_code = CURRENCY_TO_COUNTRY.get(body.currency)

    checkout_url = None

    try:
        if body.provider == "pawapay":
            if not body.phone_number or not body.network:
                raise HTTPException(status_code=400, detail="phone_number and network are required for PawaPay.")
            correspondent = CURRENCY_NETWORK_TO_PAWAPAY_CORRESPONDENT.get((body.currency, body.network.upper()))
            if not correspondent:
                raise HTTPException(status_code=400, detail=f"No PawaPay correspondent mapped for {body.currency}/{body.network}.")
            result = await pawapay.request_deposit(
                deposit_id=reference, amount=body.amount_local, currency=body.currency,
                phone_number=body.phone_number, correspondent=correspondent,
                callback_url=f"{settings.BACKEND_PUBLIC_URL}/webhook/pawapay",
            )
            if result.get("status") != "success":
                raise HTTPException(status_code=400, detail=result.get("message", "PawaPay could not start this deposit."))

        elif body.provider == "flutterwave":
            if not country_code:
                raise HTTPException(status_code=400, detail=f"Flutterwave: no country mapped for currency '{body.currency}'.")
            if not body.phone_number:
                raise HTTPException(status_code=400, detail="phone_number is required for Flutterwave.")
            result = await flutterwave.request_charge(
                tx_ref=reference, amount=body.amount_local, currency=body.currency,
                email=user.email, phone_number=body.phone_number,
                fullname=user.company_name or user.email, country_code=country_code, network=body.network,
            )
            checkout_url = (result.get("meta") or {}).get("authorization", {}).get("redirect")

        elif body.provider == "paystack":
            if not country_code:
                raise HTTPException(status_code=400, detail=f"Paystack: no country mapped for currency '{body.currency}'.")
            if not body.phone_number or not body.network:
                raise HTTPException(status_code=400, detail="phone_number and network are required for Paystack.")
            result = await paystack.request_charge(
                reference=reference, amount_local=body.amount_local, currency=body.currency,
                email=user.email, phone_number=body.phone_number,
                provider=body.network.lower(), country_code=country_code,
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown provider '{body.provider}'.")

    except (pawapay.PawaPayError, flutterwave.FlutterwaveError, paystack.PaystackError) as e:
        logger.error("Payment provider error (%s): %s", body.provider, e)
        raise HTTPException(status_code=502, detail=str(e))

    db.add(Deposit(
        reference=reference, user_id=user.id, provider=body.provider,
        amount_local=body.amount_local, currency=body.currency, phone_number=body.phone_number,
        credits_purchased=net_credits, fee_credits=fee_credits, status=DepositStatus.PENDING, credited=False,
    ))
    db.commit()

    return DepositResponse(
        reference=reference, status="PENDING", credits_pending=net_credits,
        message="Check your phone to authorize the payment via your Mobile Money PIN."
                if not checkout_url else "Complete the payment at the link provided.",
        checkout_url=checkout_url,
    )


@router.get("/deposit/{reference}")
def deposit_status(reference: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dep = db.query(Deposit).filter(Deposit.reference == reference, Deposit.user_id == user.id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="Deposit not found.")
    return {"status": dep.status.value, "credited": dep.credited, "credits_purchased": dep.credits_purchased}
