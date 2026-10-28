
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project, ProjectStatus
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.audit_logs import stage_audit_log


def create_project(
    data: ProjectCreate,
    created_by: int,
    db: Session,
) -> Project:
    project = Project(
        **data.model_dump(),
        created_by=created_by,
        status=ProjectStatus.DRAFT,
    )
    db.add(project)
    db.flush()

    stage_audit_log(
        db,
        action="CREATE",
        entity_type="Project",
        user_id=created_by,
        entity_id=project.id,
        details={"title": project.title},
    )

    db.commit()
    db.refresh(project)
    return project


def get_project(
    project_id: int,
    db: Session,
) -> Project | None:
    return db.get(Project, project_id)


def list_projects(
    db: Session,
    search: str | None = None,
    project_status: ProjectStatus | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Project]:
    statement = select(Project)

    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            Project.title.ilike(pattern)
            | Project.description.ilike(pattern)
            | Project.location.ilike(pattern)
        )

    if project_status is not None:
        statement = statement.where(Project.status == project_status)

    statement = statement.order_by(Project.id.desc())
    statement = statement.offset(skip).limit(limit)

    return list(db.scalars(statement).all())


def update_project(
    project: Project,
    data: ProjectUpdate,
    db: Session,
    actor_id: int | None = None,
) -> Project:
    changes = data.model_dump(exclude_unset=True)

    if not changes:
        raise ValueError("At least one field must be provided.")

    terminal_statuses = {
        ProjectStatus.COMPLETED,
        ProjectStatus.CANCELLED,
    }

    if project.status in terminal_statuses:
        raise ValueError(
            "Completed or cancelled projects cannot be edited."
        )

    proposed_start = changes.get("start_date", project.start_date)
    proposed_end = changes.get("end_date", project.end_date)

    if (
        proposed_start is not None
        and proposed_end is not None
        and proposed_end < proposed_start
    ):
        raise ValueError("End date cannot be before start date.")

    new_status = changes.get("status")

    if new_status is not None and new_status != project.status:
        allowed_transitions = {
            ProjectStatus.DRAFT: {
                ProjectStatus.ACTIVE,
                ProjectStatus.CANCELLED,
            },
            ProjectStatus.ACTIVE: {
                ProjectStatus.ON_HOLD,
                ProjectStatus.COMPLETED,
                ProjectStatus.CANCELLED,
            },
            ProjectStatus.ON_HOLD: {
                ProjectStatus.ACTIVE,
                ProjectStatus.CANCELLED,
            },
            ProjectStatus.COMPLETED: set(),
            ProjectStatus.CANCELLED: set(),
        }

        if new_status not in allowed_transitions[project.status]:
            raise ValueError(
                f"Cannot change project status from "
                f"{project.status.value} to {new_status.value}."
            )

    changed_fields = []

    for field, value in changes.items():
        if getattr(project, field) != value:
            setattr(project, field, value)
            changed_fields.append(field)

    if not changed_fields:
        return project

    stage_audit_log(
        db,
        action="UPDATE",
        entity_type="Project",
        user_id=actor_id,
        entity_id=project.id,
        details={"changed_fields": changed_fields},
    )

    db.commit()
    db.refresh(project)
    return project


def delete_project(
    project: Project,
    db: Session,
    actor_id: int | None = None,
) -> None:
    if project.status != ProjectStatus.DRAFT:
        raise ValueError("Only draft projects can be deleted.")

    stage_audit_log(
        db,
        action="DELETE",
        entity_type="Project",
        user_id=actor_id,
        entity_id=project.id,
        details={"title": project.title},
    )

    db.delete(project)
    db.commit()
