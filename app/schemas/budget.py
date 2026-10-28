
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.expense import ExpenseCategory


class BudgetCreate(BaseModel):
    project_id: int = Field(gt=0)
    category: ExpenseCategory
    allocated_amount: int = Field(gt=0, le=1_000_000_000)


class BudgetUpdate(BaseModel):
    allocated_amount: int = Field(gt=0, le=1_000_000_000)


class BudgetResponse(BaseModel):
    id: int
    project_id: int
    category: ExpenseCategory
    allocated_amount: int
    spent_amount: int
    remaining_amount: int
    utilization_percentage: float
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
