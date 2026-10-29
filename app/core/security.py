import secrets
import string
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


class SecurityService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash password with bcrypt (truncate if needed)"""
        # Bcrypt has a 72 byte limit, truncate password if needed
        if len(password.encode("utf-8")) > 72:
            password = password[:72]
        return pwd_context.hash(password)

    @staticmethod
    def generate_temp_password(length: int = 16) -> str:
        alphabet = string.ascii_letters + string.digits + "!@#$%"
        while True:
            pwd = "".join(secrets.choice(alphabet) for _ in range(length))
            if (any(c.islower() for c in pwd)
                    and any(c.isupper() for c in pwd)
                    and any(c.isdigit() for c in pwd)
                    and any(c in "!@#$%" for c in pwd)):
                return pwd

    @staticmethod
    def generate_role_temp_password(role: str, identifier: Optional[str]) -> str:
        """Build a recoverable initial password from a user's role identifier."""
        if not identifier or not identifier.strip():
            raise ValueError(f"A {role} identifier is required to generate a temporary password")

        normalized_role = role.strip().lower()
        if normalized_role in {"department", "dp"}:
            phone_digits = "".join(char for char in identifier if char.isdigit())
            if len(phone_digits) < 4:
                raise ValueError("Department phone number must contain at least four digits")
            return f"SPMS#DP-{phone_digits[-4:]}"
        if normalized_role in {"staff", "faculty", "lecturer", "sf"}:
            return f"SPMS#SF-{identifier.strip()}"
        if normalized_role in {"student", "st"}:
            return f"SPMS#ST-{identifier.strip()}"

        raise ValueError(f"Unsupported role for temporary password: {role}")

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(
            to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(
            to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
