
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.volunteer import Volunteer, VolunteerStatus
from app.schemas.volunteer import VolunteerCreate, VolunteerUpdate


def create_volunteer(data: VolunteerCreate, db: Session) -> Volunteer:
    user = db.get(User, data.user_id)

    if user is None:
        raise ValueError("User not found.")

    if user.role != UserRole.VOLUNTEER:
        raise ValueError("The account must have the volunteer role.")

    existing = db.scalar(
        select(Volunteer).where(Volunteer.user_id == data.user_id)
    )
    if existing is not None:
        raise ValueError("A volunteer profile already exists for this user.")

    volunteer = Volunteer(**data.model_dump())
    db.add(volunteer)
    db.commit()
    db.refresh(volunteer)
    return volunteer


def get_volunteer(volunteer_id: int, db: Session) -> Volunteer | None:
    return db.get(Volunteer, volunteer_id)


def list_volunteers(
    db: Session,
    search: str | None = None,
    volunteer_status: VolunteerStatus | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Volunteer]:
    statement = select(Volunteer)

    if search:
        pattern = f"%{search.strip()}%"
        matching_user_ids = select(User.id).where(
            User.full_name.ilike(pattern)
            | User.email.ilike(pattern)
        )
        statement = statement.where(
            Volunteer.user_id.in_(matching_user_ids)
        )

    if volunteer_status is not None:
        statement = statement.where(
            Volunteer.status == volunteer_status
        )

    statement = statement.order_by(Volunteer.id.desc())
    statement = statement.offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def update_volunteer(
    volunteer: Volunteer,
    data: VolunteerUpdate,
    db: Session,
) -> Volunteer:
    changes = data.model_dump(exclude_unset=True)

    if not changes:
        raise ValueError("At least one field must be provided.")

    for field, value in changes.items():
        setattr(volunteer, field, value)

    db.commit()
    db.refresh(volunteer)
    return volunteer


def delete_volunteer(volunteer: Volunteer, db: Session) -> None:
    db.delete(volunteer)
    db.commit()
