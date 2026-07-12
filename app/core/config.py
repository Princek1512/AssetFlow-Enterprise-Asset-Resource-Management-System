from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized application configuration.
    Values are loaded from environment variables / a .env file.
    Never hardcode secrets here — this class only defines shape + defaults.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str  # async, used by the running app (asyncpg)
    DATABASE_URL_SYNC: str = ""  # sync, used by Alembic only

    # Security / JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # App metadata
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "AssetFlow"
    API_V1_PREFIX: str = "/api/v1"

    # Bootstrap admin — created automatically on first startup if no admin exists.
    # This solves the chicken-and-egg problem: signup only ever creates Employees,
    # so the very first Admin must be seeded some other way.
    FIRST_ADMIN_EMAIL: str = "admin@assetflow.local"
    FIRST_ADMIN_PASSWORD: str = "ChangeMe123!"
    FIRST_ADMIN_NAME: str = "System Administrator"


settings = Settings()
