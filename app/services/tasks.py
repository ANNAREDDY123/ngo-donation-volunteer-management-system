
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.project import Project
from app.models.task import (
    Milestone,
    MilestoneStatus,
    ProjectTask,
    TaskStatus,
)
from app.schemas.task import (
    MilestoneCreate,
    MilestoneUpdate,
    TaskCreate,
    TaskUpdate,
)


def create_milestone(
    data: MilestoneCreate,
    created_by: int,
    db: Session,
) -> Milestone:
    project = db.get(Project, data.project_id)
    if project is None:
        raise ValueError("Project not found.")
    if project.status.value in {"completed", "cancelled"}:
        raise ValueError("Cannot add milestones to a closed project.")

    milestone = Milestone(
        **data.model_dump(),
        created_by=created_by,
        status=MilestoneStatus.PENDING,
    )
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return milestone


def get_milestone(milestone_id: int, db: Session) -> Milestone | None:
    return db.get(Milestone, milestone_id)


def list_milestones(
    db: Session,
    project_id: int | None = None,
    milestone_status: MilestoneStatus | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Milestone]:
    statement = select(Milestone)
    if project_id is not None:
        statement = statement.where(Milestone.project_id == project_id)
    if milestone_status is not None:
        statement = statement.where(Milestone.status == milestone_status)
    statement = statement.order_by(Milestone.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def update_milestone(
    milestone: Milestone,
    data: MilestoneUpdate,
    db: Session,
) -> Milestone:
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise ValueError("At least one field must be provided.")

    if milestone.status in {MilestoneStatus.COMPLETED, MilestoneStatus.CANCELLED}:
        raise ValueError("Completed or cancelled milestones cannot be edited.")

    for field, value in changes.items():
        setattr(milestone, field, value)
    db.commit()
    db.refresh(milestone)
    return milestone


def create_task(
    data: TaskCreate,
    created_by: int,
    db: Session,
) -> ProjectTask:
    project = db.get(Project, data.project_id)
    if project is None:
        raise ValueError("Project not found.")
    if project.status.value in {"completed", "cancelled"}:
        raise ValueError("Cannot add tasks to a closed project.")

    if data.milestone_id is not None:
        milestone = db.get(Milestone, data.milestone_id)
        if milestone is None:
            raise ValueError("Milestone not found.")
        if milestone.project_id != data.project_id:
            raise ValueError("Milestone must belong to the same project.")

    if data.assignment_id is not None:
        assignment = db.get(Assignment, data.assignment_id)
        if assignment is None:
            raise ValueError("Assignment not found.")

    task = ProjectTask(
        **data.model_dump(),
        created_by=created_by,
        status=TaskStatus.TODO,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(task_id: int, db: Session) -> ProjectTask | None:
    return db.get(ProjectTask, task_id)


def list_tasks(
    db: Session,
    project_id: int | None = None,
    milestone_id: int | None = None,
    task_status: TaskStatus | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[ProjectTask]:
    statement = select(ProjectTask)
    if project_id is not None:
        statement = statement.where(ProjectTask.project_id == project_id)
    if milestone_id is not None:
        statement = statement.where(ProjectTask.milestone_id == milestone_id)
    if task_status is not None:
        statement = statement.where(ProjectTask.status == task_status)
    statement = statement.order_by(ProjectTask.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def update_task(
    task: ProjectTask,
    data: TaskUpdate,
    db: Session,
) -> ProjectTask:
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise ValueError("At least one field must be provided.")

    if task.status in {TaskStatus.COMPLETED, TaskStatus.CANCELLED}:
        raise ValueError("Completed or cancelled tasks cannot be edited.")

    if "milestone_id" in changes and changes["milestone_id"] is not None:
        milestone = db.get(Milestone, changes["milestone_id"])
        if milestone is None:
            raise ValueError("Milestone not found.")
        if milestone.project_id != task.project_id:
            raise ValueError("Milestone must belong to the same project.")

    if "assignment_id" in changes and changes["assignment_id"] is not None:
        assignment = db.get(Assignment, changes["assignment_id"])
        if assignment is None:
            raise ValueError("Assignment not found.")

    for field, value in changes.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task
