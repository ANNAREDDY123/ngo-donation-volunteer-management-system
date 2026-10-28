
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.db.database import get_db
from app.models.expense import ExpenseCategory
from app.models.user import User, UserRole
from app.schemas.budget import BudgetCreate, BudgetResponse, BudgetUpdate
from app.services.budgets import (
    create_budget,
    delete_budget,
    get_budget,
    list_budgets,
    update_budget,
)

router = APIRouter(prefix="/budgets", tags=["Budget Management"])

MANAGER_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.NGO_MANAGER,
    UserRole.FINANCE_OFFICER,
)


@router.post(
    "",
    response_model=BudgetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_budget_endpoint(
    payload: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    try:
        return create_budget(db, payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[BudgetResponse])
def list_budgets_endpoint(
    project_id: int | None = Query(default=None, gt=0),
    category: ExpenseCategory | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_budgets(
        db,
        project_id=project_id,
        category=category,
        skip=skip,
        limit=limit,
    )


@router.get("/{budget_id}", response_model=BudgetResponse)
def get_budget_endpoint(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return get_budget(db, budget_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{budget_id}", response_model=BudgetResponse)
def update_budget_endpoint(
    budget_id: int,
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    try:
        return update_budget(db, budget_id, payload)
    except ValueError as exc:
        message = str(exc)
        code = 404 if message in {"Budget not found", "Project not found"} else 400
        raise HTTPException(status_code=code, detail=message) from exc


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget_endpoint(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.SUPER_ADMIN, UserRole.FINANCE_OFFICER)
    ),
):
    try:
        delete_budget(db, budget_id)
    except ValueError as exc:
        message = str(exc)
        code = 404 if message == "Budget not found" else 400
        raise HTTPException(status_code=code, detail=message) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
