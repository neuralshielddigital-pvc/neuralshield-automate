from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.tenant import Tenant
from app.models.user import TenantUser, User


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower()).strip() or "tenant"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update a NeuralShieldDigital admin user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--tenant-name", default="NeuralShieldDigital")
    parser.add_argument("--tenant-slug", default="neuralshielddigital")
    parser.add_argument("--super-admin", action="store_true")
    args = parser.parse_args()

    role = UserRole.SUPER_ADMIN if args.super_admin else UserRole.ADMIN
    email = args.email.lower()

    db = SessionLocal()
    try:
        tenant_slug = slugify(args.tenant_slug)
        tenant = db.scalar(select(Tenant).where(Tenant.slug == tenant_slug))
        if tenant is None:
            tenant = Tenant(name=args.tenant_name, slug=tenant_slug)
            db.add(tenant)
            db.flush()

        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(args.password),
                is_active=True,
                role=role,
                tenant_id=tenant.id,
            )
            db.add(user)
            db.flush()
        else:
            user.password_hash = hash_password(args.password)
            user.is_active = True
            user.role = role
            user.tenant_id = tenant.id

        tenant_user = db.scalar(
            select(TenantUser).where(TenantUser.user_id == user.id, TenantUser.tenant_id == tenant.id)
        )
        if tenant_user is None:
            db.add(TenantUser(user_id=user.id, tenant_id=tenant.id, role=role))
        else:
            tenant_user.role = role

        db.commit()
        print(f"Admin user ready: {email} ({role.value})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
