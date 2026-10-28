
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.db.database import get_db
from app.models.task import MilestoneStatus, TaskStatus
from app.models.user import User, UserRole
from app.schemas.task import (
    MilestoneCreate,
    MilestoneResponse,
    MilestoneUpdate,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.services.tasks import (
    create_milestone,
    create_task,
    get_milestone,
    get_task,
    list_milestones,
    list_tasks,
    update_milestone,
    update_task,
)

router = APIRouter(tags=["Project Milestones and Tasks"])
PROJECT_STAFF = (UserRole.SUPER_ADMIN, UserRole.NGO_MANAGER)


@router.post("/milestones", response_model=MilestoneResponse, status_code=201)
def create_milestone_endpoint(
    data: MilestoneCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*PROJECT_STAFF)),
):
    try:
        return create_milestone(data, current_user.id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/milestones", response_model=list[MilestoneResponse])
def list_milestones_endpoint(
    project_id: int | None = Query(default=None, gt=0),
    milestone_status: MilestoneStatus | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_milestones(
        db, project_id, milestone_status, skip, limit
    )


@router.get("/milestones/{milestone_id}", response_model=MilestoneResponse)
def get_milestone_endpoint(
    milestone_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    milestone = get_milestone(milestone_id, db)
    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone not found.")
    return milestone


@router.patch("/milestones/{milestone_id}", response_model=MilestoneResponse)
def update_milestone_endpoint(
    milestone_id: int,
    data: MilestoneUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*PROJECT_STAFF)),
):
    milestone = get_milestone(milestone_id, db)
    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone not found.")
    try:
        return update_milestone(milestone, data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tasks", response_model=TaskResponse, status_code=201)
def create_task_endpoint(
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*PROJECT_STAFF)),
):
    try:
        return create_task(data, current_user.id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tasks", response_model=list[TaskResponse])
def list_tasks_endpoint(
    project_id: int | None = Query(default=None, gt=0),
    milestone_id: int | None = Query(default=None, gt=0),
    task_status: TaskStatus | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_tasks(db, project_id, milestone_id, task_status, skip, limit)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = get_task(task_id, db)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task_endpoint(
    task_id: int,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*PROJECT_STAFF)),
):
    task = get_task(task_id, db)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    try:
        return update_task(task, data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
