"""Load LLM settings explicitly, without network calls or import side effects."""

import os
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    api_key: SecretStr

    @field_validator("provider", "model", mode="before")
    @classmethod
    def strip_setting(cls, value: str) -> str:
        return value.strip()

    @field_validator("api_key")
    @classmethod
    def require_api_key(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("API_KEY must not be blank")
        return value


def load_settings(env_file: Path | None = None) -> Settings:
    """Read the repository .env; existing environment variables take priority."""
    if env_file is None:
        env_file = Path(__file__).resolve().parents[2] / ".env"
    values = {**dotenv_values(env_file), **os.environ}
    return Settings(
        provider=values.get("PROVIDER") or "",
        model=values.get("MODEL") or "",
        api_key=SecretStr(values.get("API_KEY") or ""),
    )
