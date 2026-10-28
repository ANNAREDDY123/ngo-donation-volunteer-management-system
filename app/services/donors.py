from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.donor import Donor
from app.schemas.donor import DonorCreate, DonorUpdate


def create_donor(data: DonorCreate, created_by: int, db: Session) -> Donor:
    email = str(data.email).strip().lower()

    existing = db.scalar(
        select(Donor).where(Donor.email == email)
    )
    if existing:
        raise ValueError("A donor with this email already exists.")

    donor = Donor(
        **data.model_dump(exclude={"email"}),
        email=email,
        created_by=created_by,
    )

    db.add(donor)
    db.commit()
    db.refresh(donor)
    return donor


def get_donor(donor_id: int, db: Session) -> Donor | None:
    return db.get(Donor, donor_id)


def list_donors(
    db: Session,
    search: str | None = None,
    donor_type: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Donor]:
    query = select(Donor)

    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            Donor.full_name.ilike(term)
            | Donor.email.ilike(term)
            | Donor.phone.ilike(term)
        )

    if donor_type:
        query = query.where(Donor.donor_type == donor_type)

    if status:
        query = query.where(Donor.status == status)

    query = query.order_by(Donor.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(query).all())


def update_donor(
    donor: Donor,
    data: DonorUpdate,
    db: Session,
) -> Donor:
    changes = data.model_dump(exclude_unset=True)

    if "email" in changes and changes["email"] is not None:
        changes["email"] = str(changes["email"]).strip().lower()

        existing = db.scalar(
            select(Donor).where(
                Donor.email == changes["email"],
                Donor.id != donor.id,
            )
        )
        if existing:
            raise ValueError("A donor with this email already exists.")

    for field, value in changes.items():
        setattr(donor, field, value)

    db.commit()
    db.refresh(donor)
    return donor


def delete_donor(donor: Donor, db: Session) -> None:
    db.delete(donor)
    db.commit()