
from pydantic import BaseModel, ConfigDict


class DonationDashboard(BaseModel):
    total_count: int
    completed_count: int
    pending_count: int
    completed_amount: int


class CampaignDashboard(BaseModel):
    total_count: int
    active_count: int


class DonorDashboard(BaseModel):
    total_count: int
    active_count: int


class VolunteerDashboard(BaseModel):
    total_count: int
    active_count: int


class ProjectDashboard(BaseModel):
    total_count: int
    active_count: int
    completed_count: int


class FinanceDashboard(BaseModel):
    total_expenses: int
    total_budget_allocated: int


class BeneficiaryDashboard(BaseModel):
    total_count: int
    active_count: int


class ImpactDashboard(BaseModel):
    total_count: int
    total_target: int
    total_achieved: int
    overall_progress_percentage: float


class InventoryDashboard(BaseModel):
    item_count: int
    total_quantity: int


class DashboardResponse(BaseModel):
    donations: DonationDashboard
    campaigns: CampaignDashboard
    donors: DonorDashboard
    volunteers: VolunteerDashboard
    projects: ProjectDashboard
    finance: FinanceDashboard
    beneficiaries: BeneficiaryDashboard
    impact: ImpactDashboard
    inventory: InventoryDashboard

    model_config = ConfigDict(from_attributes=True)
