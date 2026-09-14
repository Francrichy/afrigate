from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, ApiKey
from app.schemas import CreateApiKeyRequest, ApiKeyResponse, NewApiKeyResponse
from app.security import get_current_user, generate_api_key

router = APIRouter(prefix="/api/keys", tags=["keys"])


@router.get("", response_model=list[ApiKeyResponse])
def list_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ApiKey).filter(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc()).all()


@router.post("", response_model=NewApiKeyResponse, status_code=201)
def create_key(body: CreateApiKeyRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    full_key, key_prefix, key_hash = generate_api_key()
    row = ApiKey(user_id=user.id, key_prefix=key_prefix, key_hash=key_hash, label=body.label or "default")
    db.add(row)
    db.commit()
    db.refresh(row)
    # full_key is returned exactly once - we never store or show it again.
    return NewApiKeyResponse(full_key=full_key, key=row)


@router.delete("/{key_id}", status_code=204)
def revoke_key(key_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="API key not found.")
    row.is_active = False
    db.commit()
