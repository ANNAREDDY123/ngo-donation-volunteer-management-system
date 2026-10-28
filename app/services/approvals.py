
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project, ProjectStatus
from app.models.project_approval import ProjectApproval, ApprovalStatus
from app.models.user import User


def submit_project_for_approval(
    db: Session,
    project_id: int,
    submitted_by: User,
    comments: str | None = None,
) -> ProjectApproval:
    project = db.get(Project, project_id)

    if project is None:
        raise ValueError("Project not found")

    if project.status != ProjectStatus.DRAFT:
        raise ValueError("Only draft projects can be submitted for approval")

    existing_pending = db.scalar(
        select(ProjectApproval).where(
            ProjectApproval.project_id == project_id,
            ProjectApproval.status == ApprovalStatus.PENDING,
        )
    )

    if existing_pending:
        raise ValueError("This project already has a pending approval request")

    approval = ProjectApproval(
        project_id=project_id,
        submitted_by=submitted_by.id,
        status=ApprovalStatus.PENDING,
        submission_comments=comments,
    )

    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


def list_project_approvals(db: Session, project_id: int):
    if db.get(Project, project_id) is None:
        raise ValueError("Project not found")

    return list(
        db.scalars(
            select(ProjectApproval)
            .where(ProjectApproval.project_id == project_id)
            .order_by(ProjectApproval.submitted_at.desc(), ProjectApproval.id.desc())
        ).all()
    )


def get_approval(db: Session, approval_id: int) -> ProjectApproval:
    approval = db.get(ProjectApproval, approval_id)
    if approval is None:
        raise ValueError("Approval request not found")
    return approval


def decide_project_approval(
    db: Session,
    approval_id: int,
    reviewer: User,
    decision: ApprovalStatus,
    comments: str | None = None,
) -> ProjectApproval:
    approval = get_approval(db, approval_id)

    if approval.status != ApprovalStatus.PENDING:
        raise ValueError("This approval request has already been decided")

    if approval.submitted_by == reviewer.id:
        raise ValueError("A user cannot approve or reject their own submission")

    project = db.get(Project, approval.project_id)
    if project is None:
        raise ValueError("Project not found")

    if decision not in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED):
        raise ValueError("Decision must be approved or rejected")

    approval.status = decision
    approval.reviewed_by = reviewer.id
    approval.review_comments = comments
    approval.reviewed_at = datetime.now(timezone.utc)

    if decision == ApprovalStatus.APPROVED:
        project.status = ProjectStatus.ACTIVE

    # Rejected projects remain drafts so they can be corrected and resubmitted.
    db.commit()
    db.refresh(approval)
    return approval
