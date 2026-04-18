from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.vault import load_vault_secrets_into_environment


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    service_name: str = Field(default="template-service", alias="SERVICE_NAME")
    version: str = Field(default="0.1.0", alias="VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=9000, alias="PORT")
    debug: bool = Field(default=False, alias="DEBUG")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="text", alias="LOG_FORMAT")
    log_file_path: str = Field(
        default="logs/template-service.log", alias="LOG_FILE_PATH"
    )
    log_overwrite_on_start: bool = Field(default=True, alias="LOG_OVERWRITE_ON_START")

    api_v1_prefix: str = Field(default="/v1", alias="API_V1_PREFIX")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/template_service",
        alias="DATABASE_URL",
        description="Async SQLAlchemy URL (PostgreSQL recommended)",
    )

    vault_enabled: bool = Field(default=False, alias="VAULT_ENABLED")
    vault_addr: str = Field(default="", alias="VAULT_ADDR")
    vault_token: str = Field(default="", alias="VAULT_TOKEN")
    vault_kv_mount: str = Field(default="secret", alias="VAULT_KV_MOUNT")
    vault_kv_path: str = Field(default="", alias="VAULT_KV_PATH")
    vault_namespace: str = Field(default="", alias="VAULT_NAMESPACE")
    vault_timeout_seconds: float = Field(default=10, alias="VAULT_TIMEOUT_SECONDS")
    vault_fail_fast: bool = Field(default=True, alias="VAULT_FAIL_FAST")
    vault_skip_verify: bool = Field(default=False, alias="VAULT_SKIP_VERIFY")
    vault_cacert: str = Field(default="", alias="VAULT_CACERT")

    files_service_base_url: str = Field(
        default="http://localhost:8001",
        alias="FILES_SERVICE_BASE_URL",
    )
    files_service_download_path_template: str = Field(
        default="/files/{file_id}",
        alias="FILES_SERVICE_DOWNLOAD_PATH_TEMPLATE",
    )
    files_service_upload_url_path: str = Field(
        default="/upload",
        alias="FILES_SERVICE_UPLOAD_URL_PATH",
    )
    files_service_auth_token: str = Field(default="", alias="FILES_SERVICE_AUTH_TOKEN")
    files_service_timeout_seconds: int = Field(
        default=20,
        alias="FILES_SERVICE_TIMEOUT_SECONDS",
    )
    files_service_verify_tls: bool = Field(
        default=True, alias="FILES_SERVICE_VERIFY_TLS"
    )
    files_service_upload_bucket: str = Field(
        default="AI_DOCUMENTS",
        alias="FILES_SERVICE_UPLOAD_BUCKET",
    )
    files_service_uploader_id: str = Field(
        default="", alias="FILES_SERVICE_UPLOADER_ID"
    )

    template_cache_ttl_seconds: int = Field(
        default=300, alias="TEMPLATE_CACHE_TTL_SECONDS"
    )
    auto_create_tables: bool = Field(default=True, alias="AUTO_CREATE_TABLES")


@lru_cache
def get_settings() -> Settings:
    bootstrap_settings = Settings()
    load_vault_secrets_into_environment(
        enabled=bootstrap_settings.vault_enabled,
        vault_addr=bootstrap_settings.vault_addr,
        vault_token=bootstrap_settings.vault_token,
        kv_mount=bootstrap_settings.vault_kv_mount,
        kv_path=bootstrap_settings.vault_kv_path,
        timeout_seconds=bootstrap_settings.vault_timeout_seconds,
        namespace=bootstrap_settings.vault_namespace,
        fail_fast=bootstrap_settings.vault_fail_fast,
        skip_verify=bootstrap_settings.vault_skip_verify,
        ca_cert_path=bootstrap_settings.vault_cacert,
    )
    if bootstrap_settings.vault_enabled:
        return Settings()
    return bootstrap_settings
