"""The only module allowed to read environment variables (architecture.md §2,
enforced by tests/backend/test_config.py).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    mode: str = Field("local", validation_alias="AUSHADHI_MODE")  # local | cloud
    gcp_project: str = Field("REPLACE_ME", validation_alias="GCP_PROJECT")
    gemini_api_key: str = Field("REPLACE_ME", validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-2.0-flash", validation_alias="GEMINI_MODEL")
    twilio_account_sid: str = Field("REPLACE_ME", validation_alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field("REPLACE_ME", validation_alias="TWILIO_AUTH_TOKEN")
    twilio_whatsapp_from: str = Field("whatsapp:+14155238886", validation_alias="TWILIO_WHATSAPP_FROM")
    firestore_emulator_host: str = Field("localhost:8080", validation_alias="FIRESTORE_EMULATOR_HOST")
    bigquery_project: str = Field("REPLACE_ME", validation_alias="BIGQUERY_PROJECT")
    signing_key: str = Field("REPLACE_ME", validation_alias="SIGNING_KEY")
    maps_api_key: str = Field("REPLACE_ME", validation_alias="MAPS_API_KEY")

    duckdb_path: str = Field(":memory:", validation_alias="DUCKDB_PATH")

    confidence_threshold: float = Field(0.85, validation_alias="CONFIDENCE_THRESHOLD")
    geofence_radius_m: float = Field(200.0, validation_alias="GEOFENCE_RADIUS_M")
    max_upload_mb: int = Field(10, validation_alias="MAX_UPLOAD_MB")
    allowed_mime: str = Field(
        "image/jpeg,image/png,audio/ogg,audio/amr,audio/mpeg",
        validation_alias="ALLOWED_MIME",
    )
    escalation_hours: int = Field(24, validation_alias="ESCALATION_HOURS")
    cors_allowed_origins: str = Field(
        "http://localhost:3000,http://127.0.0.1:3000", validation_alias="CORS_ALLOWED_ORIGINS"
    )

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def allowed_mime_set(self) -> set[str]:
        return {m.strip() for m in self.allowed_mime.split(",") if m.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
