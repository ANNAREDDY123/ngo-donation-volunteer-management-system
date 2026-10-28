
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReceiptIssue(BaseModel):
    donation_id: int = Field(gt=0)


class ReceiptResponse(BaseModel):
    id: int
    receipt_number: str
    donation_id: int
    amount: int
    currency: str
    issued_by: int
    issued_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
