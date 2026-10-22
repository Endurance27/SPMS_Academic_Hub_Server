# ============================================================================
# scripts/create_admin.py
# ============================================================================
"""
Simple script to create an administrator user
Usage: python scripts/create_admin.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import asyncio
from getpass import getpass

from loguru import logger
import pyotp
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import SecurityService
from app.models.role import Role
from app.models.user import User, UserRole

# Email: admin@company.com
#   Name: John Doe
#   Phone: +15551234567
#   Role: Super Administrator
# Password: Password@12123


def validate_email(email: str) -> bool:
    """Validate email format"""
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one digit"

    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(char.islower() for char in password):
        return False, "Password must contain at least one lowercase letter"

    return True, "Password is valid"


async def create_admin_user():
    """Interactive admin user creation"""
    print("=" * 60)
    print("Backend Template - Create Administrator User")
    print("=" * 60)
    print()

    async with AsyncSessionLocal() as db:
        try:
            # Get email
            while True:
                email = input("Email address: ").strip()

                if not email:
                    print("❌ Email is required")
                    continue

                if not validate_email(email):
                    print("❌ Invalid email format")
                    continue

                # Check if user exists
                result = await db.execute(select(User).where(User.email == email))
                if result.scalar_one_or_none():
                    print(f"❌ User with email '{email}' already exists")
                    continue

                break

            # Get password
            while True:
                password = getpass("Password (min 8 chars, 1 uppercase, 1 digit): ")

                if not password:
                    print("❌ Password is required")
                    continue

                is_valid, message = validate_password(password)
                if not is_valid:
                    print(f"❌ {message}")
                    continue

                password_confirm = getpass("Confirm password: ")

                if password != password_confirm:
                    print("❌ Passwords do not match")
                    continue

                break

            # Get first name
            while True:
                first_name = input("First name: ").strip()
                if first_name:
                    break
                print("❌ First name is required")

            # Get last name
            while True:
                last_name = input("Last name: ").strip()
                if last_name:
                    break
                print("❌ Last name is required")

            # Get phone number (optional)
            phone_number = input("Phone number (optional, e.g., +15550000000): ").strip() or None

            # Confirm
            print()
            print("-" * 60)
            print("Please confirm the following details:")
            print(f"  Email: {email}")
            print(f"  Name: {first_name} {last_name}")
            print(f"  Phone: {phone_number or 'Not provided'}")
            print(f"  Role: Super Administrator")
            print("-" * 60)

            confirm = input("Create this user? (yes/no): ").strip().lower()

            if confirm not in ["yes", "y"]:
                print("❌ User creation cancelled")
                return

            # Create user
            logger.info("Creating admin user...")
            security = SecurityService()
            totp_secret = pyotp.random_base32()

            user = User(
                email=email,
                hashed_password=security.get_password_hash(password),
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                role=UserRole.ADMINISTRATOR,
                is_active=True,
                is_verified=True,
                two_factor_enabled=True,
                two_factor_method="totp",
                two_factor_secret=totp_secret,
            )

            db.add(user)
            await db.commit()
            await db.refresh(user)

            # Assign Super Admin role if it exists
            result = await db.execute(select(Role).where(Role.code == "super_admin"))
            super_admin_role = result.scalar_one_or_none()

            if super_admin_role:
                # Insert into user_roles junction table directly
                from sqlalchemy import insert

                from app.models.role import user_roles

                stmt = insert(user_roles).values(user_id=user.id, role_id=super_admin_role.id)
                await db.execute(stmt)
                await db.commit()
                logger.info("Assigned Super Administrator role")
            else:
                logger.warning("Super Admin role not found. User created without custom role.")
                logger.warning("Run 'python scripts/seed_permissions.py' to create roles.")

            print()
            print("=" * 60)
            print("✅ Administrator user created successfully!")
            print("=" * 60)
            print(f"User ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Name: {user.first_name} {user.last_name}")
            print(f"Role: {user.role}")
            if super_admin_role:
                print(f"Custom Roles: Super Administrator")
            print("2FA: Enabled (TOTP)")
            print(f"TOTP Secret: {totp_secret}")
            print()
            print("You can now login with these credentials.")
            print("=" * 60)

        except KeyboardInterrupt:
            print("\n\n❌ User creation cancelled")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error creating admin user: {e}")
            print(f"\n❌ Error: {e}")
            sys.exit(1)


def main():
    """Main function"""
    asyncio.run(create_admin_user())


if __name__ == "__main__":
    main()
