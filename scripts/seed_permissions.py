import asyncio
import sys
from pathlib import Path

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import AsyncSessionLocal
from app.models.role import Permission, Role, role_permissions, user_roles
from app.models.user import User


async def seed_permissions(db: AsyncSession) -> list[Permission]:
    permissions_data = [
        {"name": "Create User", "code": "user.create", "module": "users"},
        {"name": "View User", "code": "user.view", "module": "users"},
        {"name": "Update User", "code": "user.update", "module": "users"},
        {"name": "Delete User", "code": "user.delete", "module": "users"},
        {"name": "Create Role", "code": "role.create", "module": "roles"},
        {"name": "View Role", "code": "role.view", "module": "roles"},
        {"name": "Update Role", "code": "role.update", "module": "roles"},
        {"name": "Delete Role", "code": "role.delete", "module": "roles"},
        {"name": "View Notifications", "code": "notification.view", "module": "notifications"},
        {"name": "Manage Notifications", "code": "notification.manage", "module": "notifications"},
        {"name": "View Audit Logs", "code": "audit.view", "module": "audit"},
    ]

    codes = [perm["code"] for perm in permissions_data]
    existing = await db.execute(select(Permission).where(Permission.code.in_(codes)))
    existing_by_code = {perm.code: perm for perm in existing.scalars().all()}

    created_count = 0
    for perm_data in permissions_data:
        if perm_data["code"] not in existing_by_code:
            permission = Permission(**perm_data)
            db.add(permission)
            existing_by_code[perm_data["code"]] = permission
            created_count += 1

    await db.commit()
    logger.info(f"Created {created_count} permissions")
    return [existing_by_code[perm["code"]] for perm in permissions_data]


async def seed_roles(db: AsyncSession, permissions: list[Permission]) -> None:
    result = await db.execute(select(Role).where(Role.code == "super_admin"))
    super_admin_role = result.scalar_one_or_none()

    if super_admin_role is None:
        super_admin_role = Role(
            name="Super Administrator",
            code="super_admin",
            description="Full system access",
            is_system_role=True,
            is_admin_role=True,
            is_active=True,
        )
        db.add(super_admin_role)
        await db.flush()
    else:
        super_admin_role.name = "Super Administrator"
        super_admin_role.description = "Full system access"
        super_admin_role.is_system_role = True
        super_admin_role.is_admin_role = True
        super_admin_role.is_active = True

    role_perm_rows = [
        {"role_id": super_admin_role.id, "permission_id": permission.id}
        for permission in permissions
    ]
    if role_perm_rows:
        stmt = pg_insert(role_permissions).values(role_perm_rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=["role_id", "permission_id"])
        await db.execute(stmt)

    admin_result = await db.execute(select(User.id).where(User.email == "admin@example.com"))
    admin_user_id = admin_result.scalar_one_or_none()
    if admin_user_id:
        stmt = pg_insert(user_roles).values(
            {"user_id": admin_user_id, "role_id": super_admin_role.id}
        )
        stmt = stmt.on_conflict_do_nothing(index_elements=["user_id", "role_id"])
        await db.execute(stmt)
        logger.info("Assigned Super Admin role to admin user")
    else:
        logger.warning("Admin user not found; skipping role assignment")

    await db.commit()


async def seed_permissions_and_roles() -> None:
    async with AsyncSessionLocal() as db:
        try:
            logger.info("Seeding permissions and roles...")
            permissions = await seed_permissions(db)
            await seed_roles(db, permissions)
            logger.info("Permissions and roles seeded successfully")
        except Exception as e:
            logger.error(f"Error seeding permissions and roles: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_permissions_and_roles())
