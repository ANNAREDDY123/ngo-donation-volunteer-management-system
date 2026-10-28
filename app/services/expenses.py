
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.expense import Expense
from app.models.project import Project, ProjectStatus
from app.models.user import User
from app.schemas.expense import ExpenseCreate, ExpenseUpdate
from app.services.audit_logs import stage_audit_log


def validate_project_for_expense(
    db: Session,
    project_id: int,
) -> Project:
    project = db.get(Project, project_id)

    if project is None:
       raise ValueError("Project not found")

    if project.status in {
        ProjectStatus.COMPLETED,
        ProjectStatus.CANCELLED,
    }:
        raise ValueError(
            "Expenses cannot be added to completed or cancelled projects."
        )

    return project


def create_expense(
    db: Session,
    payload: ExpenseCreate,
    current_user: User,
) -> Expense:
    validate_project_for_expense(db, payload.project_id)

    expense = Expense(
        **payload.model_dump(),
        created_by=current_user.id,
    )

    db.add(expense)
    db.flush()

    stage_audit_log(
        db=db,
        action="CREATE",
        entity_type="expense",
        entity_id=str(expense.id),
        user_id=current_user.id,
        details={
            "amount": str(expense.amount),
            "category": expense.category.value,
            "project_id": expense.project_id,
        },
    )

    db.commit()
    db.refresh(expense)
    return expense


def get_expense(
    db: Session,
    expense_id: int,
) -> Expense:
    expense = db.get(Expense, expense_id)

    if expense is None:
        raise ValueError("Expense not found.")

    return expense


def list_expenses(
    db: Session,
    project_id: int | None = None,
    category=None,
    start_date=None,
    end_date=None,
    skip: int = 0,
    limit: int = 100,
):
    query = select(Expense)

    if project_id is not None:
        query = query.where(Expense.project_id == project_id)

    if category is not None:
        query = query.where(Expense.category == category)

    if start_date is not None:
        query = query.where(Expense.expense_date >= start_date)

    if end_date is not None:
        query = query.where(Expense.expense_date <= end_date)

    query = query.order_by(
        Expense.expense_date.desc(),
        Expense.id.desc(),
    )
    query = query.offset(skip).limit(limit)

    return list(db.scalars(query).all())


def update_expense(
    db: Session,
    expense_id: int,
    payload: ExpenseUpdate,
    actor_id: int | None = None,
) -> Expense:
    expense = db.get(Expense, expense_id)

    if expense is None:
        raise HTTPException(
            status_code=404,
            detail="Expense not found",
        )

    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=400,
            detail="At least one field must be provided.",
        )

    target_project_id = changes.get(
        "project_id",
        expense.project_id,
    )

    project = db.get(Project, target_project_id)

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    if project.status in {
        ProjectStatus.COMPLETED,
        ProjectStatus.CANCELLED,
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "Expenses cannot be created or updated for "
                "completed or cancelled projects."
            ),
        )

    changed_fields = []

    for field, value in changes.items():
        if getattr(expense, field) != value:
            setattr(expense, field, value)
            changed_fields.append(field)

    if not changed_fields:
        return expense

    stage_audit_log(
        db=db,
        action="UPDATE",
        entity_type="expense",
        entity_id=str(expense.id),
        user_id=actor_id,
        details={"changed_fields": changed_fields},
    )

    db.commit()
    db.refresh(expense)
    return expense


def delete_expense(
    db: Session,
    expense_id: int,
    actor_id: int | None = None,
) -> None:
    expense = db.get(Expense, expense_id)

    if expense is None:
        raise HTTPException(
            status_code=404,
            detail="Expense not found",
        )

    stage_audit_log(
        db=db,
        action="DELETE",
        entity_type="expense",
        entity_id=str(expense.id),
        user_id=actor_id,
        details={
            "amount": str(expense.amount),
            "category": expense.category.value,
            "project_id": expense.project_id,
        },
    )

    db.delete(expense)
    db.commit()
