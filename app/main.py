import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1 import admin, asset_categories, assets, auth
from app.core.config import settings
from app.core.database import AsyncSessionLocal, Base, engine
from app.core.security import hash_password
from app.models import User  # noqa: F401  (import ensures all models are registered on Base.metadata)
from app.models.enums import RoleEnum

logger = logging.getLogger("assetflow")
logging.basicConfig(level=logging.INFO)


async def _bootstrap_first_admin() -> None:
    """
    Creates the initial Admin account on first startup if none exists yet.
    Necessary because signup only ever produces Employee accounts, and the
    promotion endpoint itself requires an existing Admin to call it.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.role == RoleEnum.ADMIN))
        existing_admin = result.scalar_one_or_none()
        if existing_admin is not None:
            return

        result = await session.execute(
            select(User).where(User.email == settings.FIRST_ADMIN_EMAIL.lower())
        )
        if result.scalar_one_or_none() is not None:
            logger.warning(
                "FIRST_ADMIN_EMAIL already registered as a non-admin user; skipping bootstrap. "
                "Promote manually via SQL or the admin API once an admin exists."
            )
            return

        admin_user = User(
            full_name=settings.FIRST_ADMIN_NAME,
            email=settings.FIRST_ADMIN_EMAIL.lower(),
            hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
            role=RoleEnum.ADMIN,
        )
        session.add(admin_user)
        await session.commit()
        logger.info("Bootstrapped first Admin account: %s", settings.FIRST_ADMIN_EMAIL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Hackathon-speed bootstrap: create tables directly from ORM metadata.
    # Swap for `alembic upgrade head` in any environment where migration
    # history / rollback safety matters.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _bootstrap_first_admin()
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Asset & Resource Management System API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before production deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Unhandled database error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "A database error occurred. Please try again."},
    )


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.PROJECT_NAME}


app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(asset_categories.router, prefix=settings.API_V1_PREFIX)
app.include_router(assets.router, prefix=settings.API_V1_PREFIX)
