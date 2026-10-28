
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.db.database import get_db
from app.models.project import ProjectStatus
from app.models.user import User, UserRole
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.projects import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)

router = APIRouter(prefix="/projects", tags=["NGO Projects"])

PROJECT_MANAGERS = (
    UserRole.SUPER_ADMIN,
    UserRole.NGO_MANAGER,
)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_endpoint(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*PROJECT_MANAGERS)),
):
    return create_project(data, current_user.id, db)


@router.get("", response_model=list[ProjectResponse])
def list_projects_endpoint(
    search: str | None = Query(default=None, max_length=200),
    project_status: ProjectStatus | None = Query(
        default=None, alias="status"
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_projects(
        db,
        search=search,
        project_status=project_status,
        skip=skip,
        limit=limit,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project(project_id, db)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project_endpoint(
    project_id: int,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*PROJECT_MANAGERS)),
):
    project = get_project(project_id, db)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    try:
        return update_project(project, data, db, actor_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*PROJECT_MANAGERS)),
):
    project = get_project(project_id, db)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    try:
       delete_project(project, db, actor_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
