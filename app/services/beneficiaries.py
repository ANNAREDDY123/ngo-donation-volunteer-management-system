
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.beneficiary import (
    Beneficiary,
    BeneficiaryCategory,
    BeneficiaryStatus,
)
from app.models.user import User
from app.schemas.beneficiary import BeneficiaryCreate, BeneficiaryUpdate


def create_beneficiary(
    db: Session,
    payload: BeneficiaryCreate,
    current_user: User,
) -> Beneficiary:
    beneficiary = Beneficiary(
        **payload.model_dump(),
        created_by=current_user.id,
    )
    db.add(beneficiary)
    db.commit()
    db.refresh(beneficiary)
    return beneficiary


def get_beneficiary(db: Session, beneficiary_id: int) -> Beneficiary:
    beneficiary = db.get(Beneficiary, beneficiary_id)

    if beneficiary is None:
        raise ValueError("Beneficiary not found")

    return beneficiary


def list_beneficiaries(
    db: Session,
    category: BeneficiaryCategory | None = None,
    status: BeneficiaryStatus | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Beneficiary]:
    query = select(Beneficiary)

    if category is not None:
        query = query.where(Beneficiary.category == category)

    if status is not None:
        query = query.where(Beneficiary.status == status)

    if search:
        term = f"%{search.strip()}%"
        query = query.where(Beneficiary.full_name.ilike(term))

    query = (
        query.order_by(Beneficiary.full_name, Beneficiary.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(query).all())


def update_beneficiary(
    db: Session,
    beneficiary_id: int,
    payload: BeneficiaryUpdate,
) -> Beneficiary:
    beneficiary = get_beneficiary(db, beneficiary_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(beneficiary, field, value)

    db.commit()
    db.refresh(beneficiary)
    return beneficiary


def delete_beneficiary(db: Session, beneficiary_id: int) -> None:
    beneficiary = get_beneficiary(db, beneficiary_id)
    db.delete(beneficiary)
    db.commit()
