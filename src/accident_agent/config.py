"""Configuracion de la aplicacion leida de variables de entorno y de `.env`."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: SecretStr = SecretStr("")

    openrouter_api_key: SecretStr = SecretStr("")
    # NoDecode: el valor llega como "a,b,c" y no como JSON.
    openrouter_models: Annotated[list[str], NoDecode] = Field(default_factory=list)

    langfuse_public_key: SecretStr = SecretStr("")
    langfuse_secret_key: SecretStr = SecretStr("")
    langfuse_host: str = ""

    orch_max_iterations: int = Field(default=5, ge=1, le=20)
    orch_max_tool_calls_per_iteration: int = Field(default=4, ge=1, le=10)
    llm_timeout_seconds: float = Field(default=30, gt=0)
    tool_timeout_time_seconds: float = Field(default=2, gt=0)
    tool_timeout_search_seconds: float = Field(default=10, gt=0)
    tool_timeout_report_seconds: float = Field(default=15, gt=0)
    memory_max_turns: int = Field(default=10, ge=1)

    default_timezone: str = "America/Guayaquil"
    log_level: str = "INFO"

    data_file: Path = Path("data/siniestros_raw.json")
    reports_dir: Path = Path("reports")
    logs_dir: Path = Path("logs")

    @field_validator("openrouter_models", mode="before")
    @classmethod
    def _split_models(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("default_timezone")
    @classmethod
    def _check_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Zona horaria IANA invalida: {value}") from exc
        return value

    @property
    def langfuse_enabled(self) -> bool:
        return bool(
            self.langfuse_public_key.get_secret_value()
            and self.langfuse_secret_key.get_secret_value()
            and self.langfuse_host
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
