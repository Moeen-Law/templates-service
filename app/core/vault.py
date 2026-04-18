import json
import logging
import os
from functools import lru_cache
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def _is_truthy(raw: str | None) -> bool:
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_bool(
    *,
    explicit: bool | str | None,
    env_var: str,
    default: str,
) -> bool:
    if isinstance(explicit, bool):
        return explicit
    if isinstance(explicit, str):
        return _is_truthy(explicit)
    return _is_truthy(os.getenv(env_var, default))


def _resolve_str(*, explicit: str | None, env_var: str, default: str = "") -> str:
    if explicit is not None:
        return explicit.strip()
    return os.getenv(env_var, default).strip()


def _resolve_float(
    *, explicit: float | str | None, env_var: str, default: str
) -> float:
    if explicit is not None:
        return float(explicit)
    return float(os.getenv(env_var, default))


def _verify_setting(*, skip_verify: bool, ca_cert_path: str) -> str | bool:
    if ca_cert_path:
        return ca_cert_path
    return not skip_verify


def _normalize_secret_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True)


def _handle_vault_failure(message: str, *, fail_fast: bool) -> None:
    if fail_fast:
        raise RuntimeError(message)
    logger.warning("%s", message)


@lru_cache
def load_vault_secrets_into_environment(
    *,
    enabled: bool | str | None = None,
    vault_addr: str | None = None,
    vault_role_id: str | None = None,
    vault_secret_id: str | None = None,
    vault_auth_path: str | None = None,
    kv_mount: str | None = None,
    kv_path: str | None = None,
    timeout_seconds: float | str | None = None,
    namespace: str | None = None,
    fail_fast: bool | str | None = None,
    skip_verify: bool | str | None = None,
    ca_cert_path: str | None = None,
) -> None:
    resolved_enabled = _resolve_bool(
        explicit=enabled,
        env_var="VAULT_ENABLED",
        default="false",
    )
    if not resolved_enabled:
        return

    resolved_fail_fast = _resolve_bool(
        explicit=fail_fast,
        env_var="VAULT_FAIL_FAST",
        default="true",
    )
    resolved_skip_verify = _resolve_bool(
        explicit=skip_verify,
        env_var="VAULT_SKIP_VERIFY",
        default="false",
    )
    resolved_vault_addr = _resolve_str(
        explicit=vault_addr, env_var="VAULT_ADDR"
    ).rstrip("/")
    resolved_vault_role_id = _resolve_str(
        explicit=vault_role_id,
        env_var="VAULT_ROLE_ID",
    )
    resolved_vault_secret_id = _resolve_str(
        explicit=vault_secret_id,
        env_var="VAULT_SECRET_ID",
    )
    resolved_vault_auth_path = _resolve_str(
        explicit=vault_auth_path,
        env_var="VAULT_AUTH_PATH",
        default="approle",
    ).strip("/")
    resolved_kv_mount = _resolve_str(
        explicit=kv_mount,
        env_var="VAULT_KV_MOUNT",
        default="secret",
    ).strip("/")
    resolved_kv_path = _resolve_str(explicit=kv_path, env_var="VAULT_KV_PATH").strip(
        "/"
    )
    resolved_timeout_seconds = _resolve_float(
        explicit=timeout_seconds,
        env_var="VAULT_TIMEOUT_SECONDS",
        default="10",
    )
    resolved_namespace = _resolve_str(explicit=namespace, env_var="VAULT_NAMESPACE")
    resolved_ca_cert_path = _resolve_str(explicit=ca_cert_path, env_var="VAULT_CACERT")

    if not resolved_vault_addr:
        _handle_vault_failure(
            "Vault is enabled but VAULT_ADDR is not set",
            fail_fast=resolved_fail_fast,
        )
        return
    if not resolved_vault_role_id:
        _handle_vault_failure(
            "Vault is enabled but VAULT_ROLE_ID is not set",
            fail_fast=resolved_fail_fast,
        )
        return
    if not resolved_vault_secret_id:
        _handle_vault_failure(
            "Vault is enabled but VAULT_SECRET_ID is not set",
            fail_fast=resolved_fail_fast,
        )
        return
    if not resolved_kv_path:
        _handle_vault_failure(
            "Vault is enabled but VAULT_KV_PATH is not set",
            fail_fast=resolved_fail_fast,
        )
        return

    endpoint = f"{resolved_vault_addr}/v1/{resolved_kv_mount}/data/{resolved_kv_path}"
    approle_login_endpoint = (
        f"{resolved_vault_addr}/v1/auth/{resolved_vault_auth_path}/login"
    )
    headers: dict[str, str] = {}
    if resolved_namespace:
        headers["X-Vault-Namespace"] = resolved_namespace

    logger.info(
        "Loading application secrets from Vault mount=%s path=%s",
        resolved_kv_mount,
        resolved_kv_path,
    )

    try:
        with httpx.Client(
            timeout=resolved_timeout_seconds,
            verify=_verify_setting(
                skip_verify=resolved_skip_verify,
                ca_cert_path=resolved_ca_cert_path,
            ),
        ) as client:
            auth_response = client.post(
                approle_login_endpoint,
                json={
                    "role_id": resolved_vault_role_id,
                    "secret_id": resolved_vault_secret_id,
                },
                headers=headers,
            )
            auth_response.raise_for_status()
            auth_payload = auth_response.json()
            client_token = auth_payload.get("auth", {}).get("client_token")
            if not client_token:
                raise RuntimeError(
                    "Vault AppRole login response missing auth.client_token"
                )

            read_headers = {**headers, "X-Vault-Token": str(client_token)}
            response = client.get(endpoint, headers=read_headers)
            response.raise_for_status()
            response_payload = response.json()
    except Exception as exc:
        _handle_vault_failure(
            f"Failed to load secrets from Vault endpoint={endpoint}: {exc}",
            fail_fast=resolved_fail_fast,
        )
        return

    secret_map = response_payload.get("data", {}).get("data")
    if not isinstance(secret_map, dict):
        _handle_vault_failure(
            "Vault response did not contain KV v2 secret object at data.data",
            fail_fast=resolved_fail_fast,
        )
        return

    injected_keys: list[str] = []
    for raw_key, raw_value in secret_map.items():
        key = str(raw_key).strip()
        if not key:
            continue
        os.environ[key] = _normalize_secret_value(raw_value)
        injected_keys.append(key)

    logger.info("Vault secrets loaded successfully keys_count=%s", len(injected_keys))
