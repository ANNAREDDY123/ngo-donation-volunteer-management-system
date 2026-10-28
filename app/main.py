from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.auth import router as auth_router
from app.api.donors import router as donors_router
from app.core.config import settings
from app.db.database import Base, engine
from app.models import Donor, User
from app.api.campaigns import router as campaigns_router
from app.api.donations import router as donations_router
from app.api.volunteers import router as volunteers_router
from app.api.assignments import router as assignments_router
from app.api.projects import router as projects_router
from app.api.tasks import router as tasks_router
from app.api.approvals import router as approvals_router
from app.api.expenses import router as expenses_router
from app.api.budgets import router as budgets_router
from app.api.inventory import router as inventory_router
from app.api.beneficiaries import router as beneficiaries_router
from app.api.impacts import router as impacts_router
from app.api.notifications import router as notifications_router
from app.api.receipts import router as receipts_router
from app.api.dashboard import router as dashboard_router
from app.api.reports import router as reports_router
from app.api.audit_logs import router as audit_logs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    description="NGO donations, fundraising, volunteers, and projects API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(donors_router)
app.include_router(campaigns_router)
app.include_router(donations_router)
app.include_router(volunteers_router)
app.include_router(assignments_router)
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(approvals_router)
app.include_router(expenses_router)
app.include_router(budgets_router)
app.include_router(inventory_router)
app.include_router(beneficiaries_router)
app.include_router(impacts_router)
app.include_router(notifications_router)
app.include_router(receipts_router)
app.include_router(dashboard_router)
app.include_router(reports_router)
app.include_router(audit_logs_router)


@app.get("/", tags=["Health"])
def root():
    return {
        "message": "NGO Management System API is running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}