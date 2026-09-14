from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ModelRegistryEntry
from app.schemas import ModelCatalogEntry

router = APIRouter(prefix="/api/models", tags=["catalog"])


@router.get("", response_model=list[ModelCatalogEntry])
def list_models(db: Session = Depends(get_db)):
    """Public catalog - what developers browse to pick a model. Aliases
    are excluded here since they're not a 'real' model to choose from
    (they resolve to one of these at request time)."""
    return (
        db.query(ModelRegistryEntry)
        .filter(ModelRegistryEntry.is_enabled.is_(True), ModelRegistryEntry.is_alias.is_(False))
        .order_by(ModelRegistryEntry.input_price_per_1m)
        .all()
    )
