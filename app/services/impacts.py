
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.beneficiary import Beneficiary
from app.models.impact import ProjectImpact, ImpactStatus
from app.models.project import Project
from app.models.user import User
from app.schemas.impact import ImpactCreate, ImpactUpdate


def calculate_status(target_value: int, actual_value: int) -> ImpactStatus:
    if actual_value >= target_value:
        return ImpactStatus.ACHIEVED
    return ImpactStatus.IN_PROGRESS


def impact_to_dict(impact: ProjectImpact) -> dict:
    progress = round(
        (impact.actual_value / impact.target_value) * 100,
        2,
    )
    return {
        "id": impact.id,
        "project_id": impact.project_id,
        "beneficiary_id": impact.beneficiary_id,
        "metric_name": impact.metric_name,
        "description": impact.description,
        "unit": impact.unit,
        "target_value": impact.target_value,
        "actual_value": impact.actual_value,
        "progress_percentage": progress,
        "status": impact.status,
        "recorded_by": impact.recorded_by,
        "created_at": impact.created_at,
        "updated_at": impact.updated_at,
    }


def validate_project_and_beneficiary(
    db: Session,
    project_id: int,
    beneficiary_id: int | None,
) -> None:
    if db.get(Project, project_id) is None:
        raise ValueError("Project not found")

    if beneficiary_id is not None and db.get(Beneficiary, beneficiary_id) is None:
        raise ValueError("Beneficiary not found")


def create_impact(
    db: Session,
    payload: ImpactCreate,
    current_user: User,
) -> dict:
    validate_project_and_beneficiary(
        db,
        payload.project_id,
        payload.beneficiary_id,
    )

    data = payload.model_dump()
    data["status"] = calculate_status(
        data["target_value"],
        data["actual_value"],
    )

    impact = ProjectImpact(
        **data,
        recorded_by=current_user.id,
    )
    db.add(impact)
    db.commit()
    db.refresh(impact)
    return impact_to_dict(impact)


def get_impact(db: Session, impact_id: int) -> dict:
    impact = db.get(ProjectImpact, impact_id)
    if impact is None:
        raise ValueError("Impact record not found")
    return impact_to_dict(impact)


def list_impacts(
    db: Session,
    project_id: int | None = None,
    beneficiary_id: int | None = None,
    metric_name: str | None = None,
    impact_status: ImpactStatus | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    query = select(ProjectImpact)

    if project_id is not None:
        query = query.where(ProjectImpact.project_id == project_id)

    if beneficiary_id is not None:
        query = query.where(ProjectImpact.beneficiary_id == beneficiary_id)

    if metric_name:
        query = query.where(
            ProjectImpact.metric_name.ilike(f"%{metric_name.strip()}%")
        )

    if impact_status is not None:
        query = query.where(ProjectImpact.status == impact_status)

    query = query.order_by(ProjectImpact.created_at.desc(), ProjectImpact.id.desc())
    query = query.offset(skip).limit(limit)

    return [impact_to_dict(row) for row in db.scalars(query).all()]


def update_impact(
    db: Session,
    impact_id: int,
    payload: ImpactUpdate,
) -> dict:
    impact = db.get(ProjectImpact, impact_id)
    if impact is None:
        raise ValueError("Impact record not found")

    changes = payload.model_dump(exclude_unset=True)

    beneficiary_id = changes.get("beneficiary_id", impact.beneficiary_id)
    if beneficiary_id is not None and db.get(Beneficiary, beneficiary_id) is None:
        raise ValueError("Beneficiary not found")

    target_value = changes.get("target_value", impact.target_value)
    actual_value = changes.get("actual_value", impact.actual_value)

    for field, value in changes.items():
        setattr(impact, field, value)

    impact.status = calculate_status(target_value, actual_value)

    db.commit()
    db.refresh(impact)
    return impact_to_dict(impact)


def delete_impact(db: Session, impact_id: int) -> None:
    impact = db.get(ProjectImpact, impact_id)
    if impact is None:
        raise ValueError("Impact record not found")

    db.delete(impact)
    db.commit()
