
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.expense import Expense
from app.models.project import Project, ProjectStatus
from app.models.user import User
from app.schemas.budget import BudgetCreate, BudgetUpdate


def get_spent_amount(
    db: Session,
    project_id: int,
    category,
) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.project_id == project_id,
            Expense.category == category,
        )
    )
    return int(total or 0)


def budget_to_dict(db: Session, budget: Budget) -> dict:
    spent = get_spent_amount(
        db,
        budget.project_id,
        budget.category,
    )
    remaining = budget.allocated_amount - spent
    utilization = round(
        (spent / budget.allocated_amount) * 100,
        2,
    )

    return {
        "id": budget.id,
        "project_id": budget.project_id,
        "category": budget.category,
        "allocated_amount": budget.allocated_amount,
        "spent_amount": spent,
        "remaining_amount": remaining,
        "utilization_percentage": utilization,
        "created_by": budget.created_by,
        "created_at": budget.created_at,
        "updated_at": budget.updated_at,
    }


def create_budget(
    db: Session,
    payload: BudgetCreate,
    current_user: User,
) -> dict:
    project = db.get(Project, payload.project_id)

    if project is None:
        raise ValueError("Project not found")

    if project.status in (ProjectStatus.COMPLETED, ProjectStatus.CANCELLED):
        raise ValueError("Cannot create a budget for a completed or cancelled project")

    existing = db.scalar(
        select(Budget).where(
            Budget.project_id == payload.project_id,
            Budget.category == payload.category,
        )
    )

    if existing is not None:
        raise ValueError("A budget already exists for this project and category")

    budget = Budget(
        **payload.model_dump(),
        created_by=current_user.id,
    )
    db.add(budget)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "A budget already exists for this project and category"
        ) from exc

    db.refresh(budget)
    return budget_to_dict(db, budget)


def get_budget(db: Session, budget_id: int) -> dict:
    budget = db.get(Budget, budget_id)

    if budget is None:
        raise ValueError("Budget not found")

    return budget_to_dict(db, budget)


def list_budgets(
    db: Session,
    project_id: int | None = None,
    category=None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    query = select(Budget)

    if project_id is not None:
        query = query.where(Budget.project_id == project_id)

    if category is not None:
        query = query.where(Budget.category == category)

    query = query.order_by(Budget.project_id, Budget.category)
    query = query.offset(skip).limit(limit)

    budgets = db.scalars(query).all()
    return [budget_to_dict(db, budget) for budget in budgets]


def update_budget(
    db: Session,
    budget_id: int,
    payload: BudgetUpdate,
) -> dict:
    budget = db.get(Budget, budget_id)

    if budget is None:
        raise ValueError("Budget not found")

    project = db.get(Project, budget.project_id)

    if project is None:
        raise ValueError("Project not found")

    if project.status in (ProjectStatus.COMPLETED, ProjectStatus.CANCELLED):
        raise ValueError("Cannot update a budget for a completed or cancelled project")

    spent = get_spent_amount(db, budget.project_id, budget.category)

    if payload.allocated_amount < spent:
        raise ValueError(
            f"Allocated amount cannot be less than recorded spending ({spent})"
        )

    budget.allocated_amount = payload.allocated_amount
    db.commit()
    db.refresh(budget)

    return budget_to_dict(db, budget)


def delete_budget(db: Session, budget_id: int) -> None:
    budget = db.get(Budget, budget_id)

    if budget is None:
        raise ValueError("Budget not found")

    spent = get_spent_amount(db, budget.project_id, budget.category)

    if spent > 0:
        raise ValueError("Cannot delete a budget that has recorded expenses")

    db.delete(budget)
    db.commit()
