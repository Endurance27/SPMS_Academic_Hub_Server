import asyncio

from loguru import logger
import pyotp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import SecurityService
from app.models.user import User, UserRole


async def create_admin_user(db: AsyncSession) -> User:
    security = SecurityService()
    totp_secret = pyotp.random_base32()
    admin = User(
        email="admin@example.com",
        hashed_password=security.get_password_hash("Admin@123"),
        first_name="System",
        last_name="Administrator",
        role=UserRole.ADMINISTRATOR,
        is_active=True,
        is_verified=True,
        two_factor_enabled=True,
        two_factor_method="totp",
        two_factor_secret=totp_secret,
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return admin


async def ensure_default_admin_2fa(db: AsyncSession, admin: User) -> None:
    should_update = False

    if not admin.two_factor_enabled:
        admin.two_factor_enabled = True
        should_update = True
    if admin.two_factor_method != "totp":
        admin.two_factor_method = "totp"
        should_update = True
    if not admin.two_factor_secret:
        admin.two_factor_secret = pyotp.random_base32()
        should_update = True

    if should_update:
        await db.commit()
        logger.info("Updated default admin with TOTP 2FA settings")
        logger.info(
            "Default admin TOTP secret (add to authenticator app): "
            f"{admin.two_factor_secret}"
        )


async def seed_database() -> None:
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(User).where(User.email == "admin@example.com"))
            admin_user = result.scalar_one_or_none()

            if admin_user:
                await ensure_default_admin_2fa(db, admin_user)
                logger.info("Default admin already exists. Ensured 2FA is enabled.")
                return

            admin_user = await create_admin_user(db)
            logger.info("Database seeded successfully")
            logger.info("Default admin: admin@example.com / Admin@123")
            logger.info(
                "Default admin TOTP secret (add to authenticator app): "
                f"{admin_user.two_factor_secret}"
            )
        except Exception as e:
            logger.error(f"Error seeding database: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_database())
