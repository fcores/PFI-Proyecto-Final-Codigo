"""
Configuracion tipada y validada del backend.
Usa pydantic-settings para cargar variables de entorno con fail-fast en produccion.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "local"
    database_url: str | None = None
    cors_origins: str = ""
    log_level: str = "INFO"

    ml_model_path: str = "ml_models/artefactos/modelo_gbm.joblib"

    encryption_key_dev: str | None = None
    encryption_secret_arn: str | None = None

    # Puente hacia la red Fabric (fabric-gateway-svc). La red es la unica
    # fuente de verdad de las prescripciones: ambas variables son obligatorias
    # en produccion.
    fabric_gateway_url: str | None = None
    gateway_auth_token: str | None = None
    # CA (PEM) contra la que se valida el certificado del puente cuando la URL
    # es https. Es la CA propia de fabric/scripts/gateway-tls.sh.
    fabric_gateway_ca_pem: str | None = None

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
        """Fail-fast: en produccion no se puede operar sin base ni sin la red Fabric."""
        if not self.is_production:
            return
        if not self.database_url:
            raise RuntimeError(
                "DATABASE_URL es obligatoria en ENVIRONMENT=production. "
                "El backend no puede operar en modo in-memory en produccion."
            )
        if not self.fabric_gateway_url:
            raise RuntimeError(
                "FABRIC_GATEWAY_URL es obligatoria en ENVIRONMENT=production: "
                "las prescripciones viven exclusivamente en la red Fabric."
            )
        if not self.gateway_auth_token:
            raise RuntimeError(
                "GATEWAY_AUTH_TOKEN es obligatorio en ENVIRONMENT=production "
                "(autenticacion del puente fabric-gateway-svc)."
            )
        if not self.fabric_gateway_url.lower().startswith("https://"):
            raise RuntimeError(
                "FABRIC_GATEWAY_URL debe ser https:// en ENVIRONMENT=production: el tramo "
                "hacia el puente lleva datos de salud y no puede viajar en claro."
            )
        if not self.fabric_gateway_ca_pem:
            raise RuntimeError(
                "FABRIC_GATEWAY_CA_PEM es obligatoria cuando FABRIC_GATEWAY_URL es https: "
                "el certificado del puente lo emite la CA propia del proyecto."
            )


@lru_cache
def get_settings() -> Settings:
    """Retorna la instancia singleton de configuracion (cacheada)."""
    settings = Settings()
    settings.validate_production_requirements()
    return settings
