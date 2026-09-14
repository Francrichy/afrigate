import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Deposit, DepositStatus, WebhookEvent
from app.payments import flutterwave, paystack

router = APIRouter(prefix="/webhook", tags=["webhooks"])
logger = logging.getLogger("webhooks")


def _record_event_once(db: Session, source: str, external_event_id: str, raw_payload: str) -> bool:
    db.add(WebhookEvent(source=source, external_event_id=external_event_id, payload=raw_payload))
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def _credit_wallet(db: Session, deposit: Deposit) -> None:
    """Atomic credit + mark-credited, guarded by the deposit's unique
    `reference` so a duplicated webhook delivery can never double-credit."""
    user = db.execute(select(User).where(User.id == deposit.user_id).with_for_update()).scalar_one_or_none()
    dep_locked = db.execute(
        select(Deposit).where(Deposit.reference == deposit.reference).with_for_update()
    ).scalar_one_or_none()

    if user and dep_locked and not dep_locked.credited:
        user.credit_balance += dep_locked.credits_purchased
        dep_locked.status = DepositStatus.COMPLETED
        dep_locked.credited = True
        db.commit()
        logger.info("Credited user %s with %s credits (deposit %s)", user.id, dep_locked.credits_purchased, deposit.reference)


@router.post("/pawapay")
async def pawapay_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    deposit_id = payload.get("depositId")
    remote_status = payload.get("status")
    if not deposit_id:
        raise HTTPException(status_code=400, detail="depositId missing.")

    if not _record_event_once(db, "pawapay", f"{deposit_id}:{remote_status}", str(payload)):
        return {"ok": True, "duplicate": True}

    dep = db.query(Deposit).filter(Deposit.reference == deposit_id).first()
    if not dep:
        return {"ok": True}

    if remote_status == "COMPLETED":
        _credit_wallet(db, dep)
    elif remote_status == "FAILED":
        dep.status = DepositStatus.FAILED
        db.commit()

    return {"ok": True}


@router.post("/flutterwave")
async def flutterwave_webhook(
    request: Request, db: Session = Depends(get_db),
    verif_hash: str = Header(None, alias="verif-hash"),
):
    if not flutterwave.verify_webhook_signature(verif_hash or ""):
        raise HTTPException(status_code=403, detail="Invalid webhook signature.")

    payload = await request.json()
    data = payload.get("data", {})
    tx_ref = data.get("tx_ref")
    remote_status = data.get("status")  # "successful" | "failed"
    if not tx_ref:
        raise HTTPException(status_code=400, detail="tx_ref missing.")

    if not _record_event_once(db, "flutterwave", f"{tx_ref}:{remote_status}", str(payload)):
        return {"ok": True, "duplicate": True}

    dep = db.query(Deposit).filter(Deposit.reference == tx_ref).first()
    if not dep:
        return {"ok": True}

    if remote_status == "successful":
        _credit_wallet(db, dep)
    elif remote_status == "failed":
        dep.status = DepositStatus.FAILED
        db.commit()

    return {"ok": True}


@router.post("/paystack")
async def paystack_webhook(
    request: Request, db: Session = Depends(get_db),
    x_paystack_signature: str = Header(None, alias="x-paystack-signature"),
):
    raw_body = await request.body()
    if not paystack.verify_webhook_signature(raw_body, x_paystack_signature or ""):
        raise HTTPException(status_code=403, detail="Invalid webhook signature.")

    payload = await request.json()
    event = payload.get("event")  # "charge.success" | other
    data = payload.get("data", {})
    reference = data.get("reference")
    if not reference:
        raise HTTPException(status_code=400, detail="reference missing.")

    if not _record_event_once(db, "paystack", f"{reference}:{event}", str(payload)):
        return {"ok": True, "duplicate": True}

    dep = db.query(Deposit).filter(Deposit.reference == reference).first()
    if not dep:
        return {"ok": True}

    if event == "charge.success":
        _credit_wallet(db, dep)
    elif event == "charge.failed":
        dep.status = DepositStatus.FAILED
        db.commit()

    return {"ok": True}
