import os
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.vault import load_vault_secrets_into_environment

_ENVIRONMENT_ALIASES: dict[str, str] = {
    "dev": "development",
    "development": "development",
    "prod": "production",
    "production": "production",
}


def _normalize_environment(raw_value: str | None) -> str:
    if raw_value is None:
        return "development"

    value = raw_value.strip().lower()
    if not value:
        return "development"

    normalized = _ENVIRONMENT_ALIASES.get(value)
    if normalized is None:
        allowed = ", ".join(sorted(_ENVIRONMENT_ALIASES.keys()))
        raise ValueError(
            f"Unsupported ENVIRONMENT value '{raw_value}'. Allowed values: {allowed}"
        )
    return normalized


def _read_dotenv_value(file_path: str, key: str) -> str | None:
    env_path = Path(file_path)
    if not env_path.exists():
        return None

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, raw_value = stripped.split("=", 1)
        if name.strip() != key:
            continue
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        return value
    return None


def _read_consul_blob_from_environment() -> dict[str, Any] | None:
    raw_consul = os.getenv("CONSUL")
    if raw_consul is None:
        raw_consul = os.getenv("consul")

    if raw_consul is None or not raw_consul.strip():
        return None

    try:
        payload = json.loads(raw_consul)
    except json.JSONDecodeError as exc:
        raise ValueError("CONSUL/consul must be a valid JSON object") from exc

    if not isinstance(payload, dict):
        raise ValueError("CONSUL/consul must be a JSON object")

    return payload


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []

        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError("Expected a JSON array or comma-separated string") from exc
            return _normalize_string_list(parsed)

        return [item.strip() for item in stripped.split(",") if item.strip()]

    if isinstance(value, (list, tuple, set)):
        normalized: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                normalized.append(text)
        return normalized

    raise ValueError("Expected a list of strings")


def _default_consul_tag_for_environment(environment: str) -> str:
    return "prod" if environment == "production" else "dev"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None,
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

    vault_enabled: bool = Field(default=True, alias="VAULT_ENABLED")
    vault_addr: str = Field(default="", alias="VAULT_ADDR")
    vault_role_id: str = Field(default="", alias="VAULT_ROLE_ID")
    vault_secret_id: str = Field(default="", alias="VAULT_SECRET_ID")
    vault_auth_path: str = Field(default="approle", alias="VAULT_AUTH_PATH")
    vault_kv_mount: str = Field(default="env", alias="VAULT_KV_MOUNT")
    vault_kv_path: str = Field(default="templates/dev", alias="VAULT_KV_PATH")
    vault_namespace: str = Field(default="", alias="VAULT_NAMESPACE")
    vault_timeout_seconds: float = Field(default=10, alias="VAULT_TIMEOUT_SECONDS")
    vault_fail_fast: bool = Field(default=True, alias="VAULT_FAIL_FAST")
    vault_skip_verify: bool = Field(default=False, alias="VAULT_SKIP_VERIFY")
    vault_cacert: str = Field(default="", alias="VAULT_CACERT")

    files_service_base_url: str = Field(
        default="http://localhost:8001",
        alias="FILES_SERVICE_BASE_URL",
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

    consul_enabled: bool = Field(default=False, alias="CONSUL_ENABLED")
    consul_fail_fast: bool = Field(default=True, alias="CONSUL_FAIL_FAST")
    consul_host: str = Field(default="", alias="CONSUL_HOST")
    consul_port: int = Field(default=8500, alias="CONSUL_PORT")
    consul_scheme: str = Field(default="http", alias="CONSUL_SCHEME")
    consul_secure: bool = Field(default=False, alias="CONSUL_SECURE")
    consul_token: str = Field(default="", alias="CONSUL_TOKEN")
    consul_service_name: str = Field(default="", alias="CONSUL_SERVICE_NAME")
    consul_service_id: str = Field(default="", alias="CONSUL_SERVICE_ID")
    consul_service_address: str = Field(default="", alias="CONSUL_SERVICE_ADDRESS")
    consul_registration_tags: list[str] = Field(
        default_factory=list, alias="CONSUL_REGISTRATION_TAGS"
    )
    consul_query_tags: list[str] = Field(
        default_factory=list, alias="CONSUL_QUERY_TAGS"
    )
    consul_check_http: str = Field(default="", alias="CONSUL_CHECK_HTTP")
    consul_check_interval: str = Field(default="15s", alias="CONSUL_CHECK_INTERVAL")
    consul_check_timeout: str = Field(default="5s", alias="CONSUL_CHECK_TIMEOUT")
    consul_check_deregister_critical_service_after: str = Field(
        default="1m",
        alias="CONSUL_CHECK_DEREGISTER_CRITICAL_SERVICE_AFTER",
    )

    @model_validator(mode="after")
    def _merge_consul_blob(self):
        consul_blob = _read_consul_blob_from_environment()
        fields_set = set(self.model_fields_set)
        if consul_blob is None:
            consul_blob = {}

        def apply_if_unset(field_name: str, value: Any) -> None:
            if value is None or field_name in fields_set:
                return
            setattr(self, field_name, value)

        check = consul_blob.get("check", {})
        if not isinstance(check, dict):
            check = {}

        if consul_blob:
            apply_if_unset("consul_enabled", True)
            apply_if_unset("consul_host", consul_blob.get("host"))

            raw_port = consul_blob.get("port")
            if raw_port is not None and "consul_port" not in fields_set:
                apply_if_unset("consul_port", int(raw_port))

            apply_if_unset("consul_scheme", consul_blob.get("schema"))
            apply_if_unset("consul_secure", consul_blob.get("secure"))
            apply_if_unset("consul_service_name", consul_blob.get("serviceName"))
            apply_if_unset("consul_token", consul_blob.get("token"))
            apply_if_unset("consul_registration_tags", consul_blob.get("tags"))
            apply_if_unset("consul_query_tags", consul_blob.get("queryTags"))
            apply_if_unset("consul_check_http", check.get("http"))
            apply_if_unset("consul_check_interval", check.get("interval"))
            apply_if_unset("consul_check_timeout", check.get("timeout"))
            apply_if_unset(
                "consul_check_deregister_critical_service_after",
                check.get("deregisterCriticalServiceAfter"),
            )

        default_tag = _default_consul_tag_for_environment(self.environment)
        if (
            "consul_registration_tags" not in fields_set
            and not self.consul_registration_tags
        ):
            self.consul_registration_tags = [default_tag]
        if "consul_query_tags" not in fields_set and not self.consul_query_tags:
            self.consul_query_tags = [default_tag]

        return self

    @field_validator("environment", mode="before")
    @classmethod
    def _normalize_environment_field(cls, value: str | None) -> str:
        return _normalize_environment(value)

    @field_validator("consul_scheme", mode="before")
    @classmethod
    def _normalize_consul_scheme(cls, value: str | None) -> str:
        if value is None:
            return "http"
        normalized = value.strip().lower()
        if normalized not in {"http", "https"}:
            raise ValueError("CONSUL_SCHEME must be either 'http' or 'https'")
        return normalized

    @field_validator("consul_registration_tags", "consul_query_tags", mode="before")
    @classmethod
    def _normalize_consul_tags(cls, value: Any) -> list[str]:
        return _normalize_string_list(value)


def get_current_environment() -> str:
    environment = os.getenv("ENVIRONMENT")
    if environment:
        return _normalize_environment(environment)

    dotenv_environment = _read_dotenv_value(".env", "ENVIRONMENT")
    return _normalize_environment(dotenv_environment)


def get_environment_env_files(environment: str | None = None) -> tuple[str, str]:
    resolved_environment = (
        _normalize_environment(environment)
        if environment is not None
        else get_current_environment()
    )
    suffix = "dev" if resolved_environment == "development" else "prod"
    return ".env", f".env.{suffix}"


def load_settings_for_environment(environment: str | None = None) -> Settings:
    env_files = get_environment_env_files(environment)
    return Settings(_env_file=env_files, _env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    current_environment = get_current_environment()
    bootstrap_settings = load_settings_for_environment(current_environment)
    load_vault_secrets_into_environment(
        enabled=bootstrap_settings.vault_enabled,
        vault_addr=bootstrap_settings.vault_addr,
        vault_role_id=bootstrap_settings.vault_role_id,
        vault_secret_id=bootstrap_settings.vault_secret_id,
        vault_auth_path=bootstrap_settings.vault_auth_path,
        kv_mount=bootstrap_settings.vault_kv_mount,
        kv_path=bootstrap_settings.vault_kv_path,
        timeout_seconds=bootstrap_settings.vault_timeout_seconds,
        namespace=bootstrap_settings.vault_namespace,
        fail_fast=bootstrap_settings.vault_fail_fast,
        skip_verify=bootstrap_settings.vault_skip_verify,
        ca_cert_path=bootstrap_settings.vault_cacert,
    )
    if bootstrap_settings.vault_enabled:
        return load_settings_for_environment(current_environment)
    return bootstrap_settings
