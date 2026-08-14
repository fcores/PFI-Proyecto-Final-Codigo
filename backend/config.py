"""
Configuracion tipada y validada del backend.
Usa pydantic-settings para cargar variables de entorno con fail-fast en produccion.
"""
from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "local"
    database_url: Optional[str] = None
    cors_origins: str = ""
    log_level: str = "INFO"

    auth_username: str = "admin"
    auth_password: str = "admin123"
    auth_display_name: str = "Administrador"

    ml_model_path: str = "ml_models/artefactos/modelo_gbm.joblib"

    encryption_key_dev: Optional[str] = None
    encryption_secret_arn: Optional[str] = None

    fabric_gateway_url: Optional[str] = None

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"local", "test", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT debe ser uno de {allowed}, recibido: {v}")
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origins_list(self) -> list:
        if not self.cors_origins:
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_production_requirements(self) -> None:
        """Fail-fast: en produccion no se puede operar sin base de datos."""
        if self.is_production and not self.database_url:
            raise RuntimeError(
                "DATABASE_URL es obligatoria en ENVIRONMENT=production. "
                "El backend no puede operar en modo in-memory en produccion."
            )


@lru_cache
def get_settings() -> Settings:
    """Retorna la instancia singleton de configuracion (cacheada)."""
    settings = Settings()
    settings.validate_production_requirements()
    return settings
