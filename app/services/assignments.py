
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assignment import Assignment, AssignmentStatus
from app.models.user import User
from app.models.volunteer import Volunteer, VolunteerStatus
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate


def create_assignment(
    data: AssignmentCreate,
    created_by: int,
    db: Session,
) -> Assignment:
    volunteer = db.get(Volunteer, data.volunteer_id)

    if volunteer is None:
        raise ValueError("Volunteer profile not found.")

    if volunteer.status != VolunteerStatus.ACTIVE:
        raise ValueError("Assignments require an active volunteer.")

    assignment = Assignment(
        **data.model_dump(),
        created_by=created_by,
        status=AssignmentStatus.ASSIGNED,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def get_assignment(
    assignment_id: int,
    db: Session,
) -> Assignment | None:
    return db.get(Assignment, assignment_id)


def list_assignments(
    db: Session,
    volunteer_id: int | None = None,
    assignment_status: AssignmentStatus | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Assignment]:
    statement = select(Assignment)

    if volunteer_id is not None:
        statement = statement.where(
            Assignment.volunteer_id == volunteer_id
        )

    if assignment_status is not None:
        statement = statement.where(
            Assignment.status == assignment_status
        )

    if search:
        statement = statement.where(
            Assignment.title.ilike(f"%{search.strip()}%")
        )

    statement = statement.order_by(Assignment.id.desc())
    statement = statement.offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def update_assignment(
    assignment: Assignment,
    data: AssignmentUpdate,
    db: Session,
) -> Assignment:
    changes = data.model_dump(exclude_unset=True)

    if not changes:
        raise ValueError("At least one field must be provided.")

    new_status = changes.get("status")
    current_status = assignment.status

    allowed_transitions = {
        AssignmentStatus.ASSIGNED: {
            AssignmentStatus.IN_PROGRESS,
            AssignmentStatus.COMPLETED,
            AssignmentStatus.CANCELLED,
        },
        AssignmentStatus.IN_PROGRESS: {
            AssignmentStatus.COMPLETED,
            AssignmentStatus.CANCELLED,
        },
        AssignmentStatus.COMPLETED: set(),
        AssignmentStatus.CANCELLED: set(),
    }

    if new_status is not None and new_status != current_status:
        if new_status not in allowed_transitions[current_status]:
            raise ValueError(
                f"Cannot change assignment status from "
                f"{current_status.value} to {new_status.value}."
            )

    due_date = changes.get("due_date", assignment.due_date)
    if due_date is not None and due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)
        changes["due_date"] = due_date

    if assignment.status in {
        AssignmentStatus.COMPLETED,
        AssignmentStatus.CANCELLED,
    } and any(
        key in changes for key in ("title", "description", "priority", "due_date")
    ):
        raise ValueError(
            "Completed or cancelled assignments cannot be edited."
        )

    for field, value in changes.items():
        setattr(assignment, field, value)

    db.commit()
    db.refresh(assignment)
    return assignment


def delete_assignment(assignment: Assignment, db: Session) -> None:
    if assignment.status != AssignmentStatus.ASSIGNED:
        raise ValueError("Only assigned, not-started assignments can be deleted.")

    db.delete(assignment)
    db.commit()


def volunteer_owns_assignment(
    assignment: Assignment,
    user: User,
    db: Session,
) -> bool:
    volunteer = db.scalar(
        select(Volunteer).where(Volunteer.user_id == user.id)
    )
    return volunteer is not None and volunteer.id == assignment.volunteer_id
