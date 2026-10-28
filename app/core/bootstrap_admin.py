
import os
import sys

from sqlalchemy import select

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.user import User, UserRole


def bootstrap_admin() -> None:
    """Promote one explicitly designated existing user to Super Admin."""

    admin_email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()

    if not admin_email:
        print("ERROR: BOOTSTRAP_ADMIN_EMAIL is not set.")
        print(
            "Set it to the email address of an existing account "
            "before running this utility."
        )
        sys.exit(1)

    db = SessionLocal()

    try:
        user = db.scalar(
            select(User).where(User.email == admin_email)
        )

        if user is None:
            print(f"ERROR: No account found for {admin_email}.")
            print("Register this account first, then run the utility again.")
            sys.exit(1)

        if not user.is_active:
            print("ERROR: This account is inactive.")
            print("Activate the account before promoting it.")
            sys.exit(1)

        if user.role == UserRole.SUPER_ADMIN:
            print(f"{admin_email} is already a Super Admin.")
            return

        user.role = UserRole.SUPER_ADMIN
        db.commit()

        print("Super Admin role assigned successfully.")
        print(f"Account: {admin_email}")
        print("No password was changed.")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    bootstrap_admin()
