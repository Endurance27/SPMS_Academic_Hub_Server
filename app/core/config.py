import json
import os
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Backend Template"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str
    API_VERSION: str = "v1"
    ALLOWED_EXTENSIONS: str = "pdf,jpg,jpeg,png,doc,docx"

    # ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]

    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str
    REDIS_DB: int = 0
    REDIS_URL: str

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 2FA
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    OTP_EXPIRE_MINUTES: int = 5

    # External APIs
    XDS_DATA_API_KEY: Optional[str] = None
    XDS_DATA_BASE_URL: Optional[str] = None
    GHANA_CARD_API_KEY: Optional[str] = None
    GHANA_CARD_BASE_URL: Optional[str] = None
    GHANA_POST_GPS_BASE_URL: Optional[str] = None
    GOOGLE_MAPS_API_KEY: Optional[str] = None

    # File Upload
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    # ALLOWED_EXTENSIONS: List[str] = ["pdf", "jpg", "jpeg", "png", "doc", "docx"]
    UPLOAD_DIR: str = "./uploads"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOGSTASH_HOST: str = "logstash"
    LOGSTASH_PORT: int = 5000

    # Email
    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    EMAIL_FROM: str

    RABBITMQ_USER: str = "app_rmq"
    RABBITMQ_PASS: str = "rmq_pass"
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672

    # Security
    BCRYPT_ROUNDS: int = 12
    SESSION_TIMEOUT_MINUTES: int = 60
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30

    SUPPORT_EMAIL: str = "support@example.com"

    # CORS
    # CORS_ORIGINS: str = ["http://localhost:3000"]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    FRONTEND_URL: str = "http://localhost:3000"

    CORS_ORIGINS: Optional[str] = None
    ALLOWED_HOSTS: Optional[str] = None

    # Email / third-party keys
    SENDGRID_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

    @staticmethod
    def _parse_list_str(value: Optional[str], default: List[str]) -> List[str]:
        if not value or not str(value).strip():
            return default
        s = str(value).strip()
        try:
            if s.startswith("[") or s.startswith("{"):
                return json.loads(s)
        except Exception:
            pass
        return [item.strip() for item in s.split(",") if item.strip()]

    @property
    def cors_origins(self) -> List[str]:
        return self._parse_list_str(self.CORS_ORIGINS, ["http://localhost:3000"])

    @property
    def allowed_hosts(self) -> List[str]:
        return self._parse_list_str(self.ALLOWED_HOSTS, ["localhost", "127.0.0.1"])

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    for k in ("CORS_ORIGINS", "ALLOWED_HOSTS", "ALLOWED_EXTENSIONS"):
        if k in os.environ and os.environ.get(k, "").strip() == "":
            os.environ.pop(k, None)
    return Settings()


settings = get_settings()
