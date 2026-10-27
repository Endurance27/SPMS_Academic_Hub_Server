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
from app.models.role import Permission, Role, RoleTemplate, role_permissions, user_roles
from app.models.user import User
from app.utils.constants import Permission as PermEnum, PERMISSION_MODULES, ROLE_PERMISSIONS


async def seed_permissions(db: AsyncSession) -> dict[str, Permission]:
    """Seed all permissions from constants"""
    # Build permissions data from Permission enum
    permissions_data = []
    for perm in PermEnum:
        # Determine module from permission code
        module = perm.value.split('.')[0] if '.' in perm.value else 'general'
        for mod_name, mod_perms in PERMISSION_MODULES.items():
            if perm in mod_perms:
                module = mod_name
                break

        permissions_data.append({
            "name": perm.value.replace('.', ' ').title(),
            "code": perm.value,
            "module": module,
            "description": f"Permission to {perm.value}"
        })

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
    return existing_by_code


async def seed_role_templates(db: AsyncSession, permissions_by_code: dict[str, Permission]) -> None:
    """Seed role templates with predefined permission sets"""
    for role_name, perm_codes in ROLE_PERMISSIONS.items():
        # Find or create role template
        result = await db.execute(
            select(RoleTemplate).where(RoleTemplate.role == role_name)
        )
        template = result.scalar_one_or_none()

        if template is None:
            template = RoleTemplate(
                name=f"{role_name.title()} Template",
                role=role_name,
                permissions=perm_codes
            )
            db.add(template)
            await db.flush()
            logger.info(f"Created role template for {role_name}")
        else:
            # Update permissions
            template.permissions = perm_codes
            logger.info(f"Updated role template for {role_name}")

    await db.commit()


async def seed_roles(db: AsyncSession, permissions_by_code: dict[str, Permission]) -> None:
    """Seed roles and assign permissions based on role"""
    for role_name, perm_codes in ROLE_PERMISSIONS.items():
        # Find or create role
        result = await db.execute(select(Role).where(Role.code == role_name))
        role = result.scalar_one_or_none()

        if role is None:
            role = Role(
                name=f"{role_name.title()}",
                code=role_name,
                description=f"{role_name.title()} role",
                is_system_role=True,
                is_admin_role=(role_name == "super"),
                is_active=True,
            )
            db.add(role)
            await db.flush()
            logger.info(f"Created role: {role_name}")
        else:
            role.is_system_role = True
            role.is_admin_role = (role_name == "super")
            role.is_active = True
            logger.info(f"Updated role: {role_name}")

        # Assign permissions to role
        role_perm_rows = []
        for perm_code in perm_codes:
            if perm_code in permissions_by_code:
                role_perm_rows.append({
                    "role_id": role.id,
                    "permission_id": permissions_by_code[perm_code].id
                })

        if role_perm_rows:
            stmt = pg_insert(role_permissions).values(role_perm_rows)
            stmt = stmt.on_conflict_do_nothing(index_elements=["role_id", "permission_id"])
            await db.execute(stmt)
            logger.info(f"Assigned {len(role_perm_rows)} permissions to {role_name}")

    # Assign super role to admin user
    admin_result = await db.execute(select(User.id).where(User.email == "admin@example.com"))
    admin_user_id = admin_result.scalar_one_or_none()
    if admin_user_id:
        super_role_result = await db.execute(select(Role).where(Role.code == "super"))
        super_role = super_role_result.scalar_one_or_none()
        if super_role:
            stmt = pg_insert(user_roles).values(
                {"user_id": admin_user_id, "role_id": super_role.id}
            )
            stmt = stmt.on_conflict_do_nothing(index_elements=["user_id", "role_id"])
            await db.execute(stmt)
            logger.info("Assigned Super role to admin user")
    else:
        logger.warning("Admin user not found; skipping role assignment")

    await db.commit()


async def seed_permissions_and_roles() -> None:
    async with AsyncSessionLocal() as db:
        try:
            logger.info("Seeding permissions and roles...")
            permissions_by_code = await seed_permissions(db)
            await seed_role_templates(db, permissions_by_code)
            await seed_roles(db, permissions_by_code)
            logger.info("Permissions and roles seeded successfully")
        except Exception as e:
            logger.error(f"Error seeding permissions and roles: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_permissions_and_roles())
