
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.db.database import get_db
from app.models.expense import ExpenseCategory
from app.models.user import User, UserRole
from app.schemas.expense import ExpenseCreate, ExpenseResponse, ExpenseUpdate
from app.services.expenses import (
    create_expense,
    delete_expense,
    get_expense,
    list_expenses,
    update_expense,
)

router = APIRouter(prefix="/expenses", tags=["Expense Management"])

MANAGER_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.NGO_MANAGER,
    UserRole.FINANCE_OFFICER,
)


@router.post(
    "",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_expense_endpoint(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    try:
        return create_expense(db, payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[ExpenseResponse])
def list_expenses_endpoint(
    project_id: int | None = Query(default=None, gt=0),
    category: ExpenseCategory | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date cannot be later than end_date",
        )

    return list_expenses(
        db,
        project_id=project_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )


@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense_endpoint(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return get_expense(db, expense_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{expense_id}", response_model=ExpenseResponse)
def update_expense_endpoint(
    expense_id: int,
    payload: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    try:
        return update_expense(db, expense_id, payload, actor_id=current_user.id)
    except ValueError as exc:
        message = str(exc)
        code = 404 if message == "Expense not found" else 400
        raise HTTPException(status_code=code, detail=message) from exc


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense_endpoint(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.SUPER_ADMIN, UserRole.FINANCE_OFFICER)
    ),
):
    try:
        delete_expense(db, expense_id, actor_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
