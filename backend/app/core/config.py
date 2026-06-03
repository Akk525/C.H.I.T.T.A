from __future__ import annotations

from pydantic import BaseModel


class Settings(BaseModel):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/chitta"
    cors_origins: list[str] = ["http://localhost:3000"]
    persist_analyses: bool = False


def get_settings() -> Settings:
    import os
    from pathlib import Path
    from dotenv import load_dotenv

    env_file = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_file, override=False)

    cors = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/chitta",
        ),
        cors_origins=[o.strip() for o in cors.split(",") if o.strip()],
        persist_analyses=os.getenv("PERSIST_ANALYSES", "false").lower()
        in {"1", "true", "yes", "on"},
    )

