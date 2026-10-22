import json
import os

# normalize list env vars before importing app.core.config.Settings
for _k in ("ALLOWED_HOSTS", "CORS_ORIGINS", "ALLOWED_EXTENSIONS"):
    if _k in os.environ:
        val = os.environ.get(_k, "")
        if val is None or str(val).strip() == "":
            os.environ.pop(_k, None)
        else:
            s = str(val).strip()
            if not (s.startswith("[") or s.startswith("{")):
                items = [i.strip() for i in s.split(",") if i.strip()]
                os.environ[_k] = json.dumps(items)

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging


# build safe lists manually so TrustedHost/CORS don't depend on Settings parsing
def _parse_list_env(key: str, default: list[str]) -> list[str]:
    v = os.environ.get(key)
    if not v or not str(v).strip():
        return default
    s = str(v).strip()
    try:
        if s.startswith("[") or s.startswith("{"):
            return json.loads(s)
    except Exception:
        pass
    return [item.strip() for item in s.split(",") if item.strip()]


allowed_hosts = _parse_list_env("ALLOWED_HOSTS", ["localhost", "127.0.0.1"])
cors_origins = _parse_list_env("CORS_ORIGINS", ["http://localhost:3000"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME}...")
    setup_logging()
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Reusable FastAPI backend template",
    version=settings.API_VERSION,
    docs_url=f"/docs",
    redoc_url=f"/api/{settings.API_VERSION}/redoc",
    openapi_url=f"/api/{settings.API_VERSION}/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted Host Middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# GZip Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Exception Handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# Health Check
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "app_name": settings.APP_NAME, "version": settings.API_VERSION}


# Include API Router
app.include_router(api_router, prefix=f"/api/{settings.API_VERSION}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
