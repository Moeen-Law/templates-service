import os

import pytest

from app.core import vault


@pytest.fixture(autouse=True)
def reset_vault_env(monkeypatch: pytest.MonkeyPatch):
    vault.load_vault_secrets_into_environment.cache_clear()
    keys_to_clear = [
        "VAULT_ENABLED",
        "VAULT_ADDR",
        "VAULT_ROLE_ID",
        "VAULT_SECRET_ID",
        "VAULT_AUTH_PATH",
        "VAULT_KV_MOUNT",
        "VAULT_KV_PATH",
        "VAULT_NAMESPACE",
        "VAULT_TIMEOUT_SECONDS",
        "VAULT_FAIL_FAST",
        "VAULT_SKIP_VERIFY",
        "VAULT_CACERT",
        "DATABASE_URL",
        "FILES_SERVICE_AUTH_TOKEN",
        "FILES_SERVICE_BASE_URL",
        "NESTED",
    ]
    for key in keys_to_clear:
        monkeypatch.delenv(key, raising=False)
    yield
    vault.load_vault_secrets_into_environment.cache_clear()


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_loads_kv_v2_secret_into_environment(monkeypatch: pytest.MonkeyPatch):
    class _FakeClient:
        def __init__(self, timeout: float, verify: bool):
            assert timeout == 15.0
            assert verify is True

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(
            self, url: str, json: dict[str, str], headers: dict[str, str]
        ) -> _FakeResponse:
            assert url == "https://vault.example.com/v1/auth/approle/login"
            assert json["role_id"] == "role-id-value"
            assert json["secret_id"] == "secret-id-value"
            assert "X-Vault-Token" not in headers
            return _FakeResponse(
                {
                    "auth": {
                        "client_token": "client-token-value",
                    }
                }
            )

        def get(self, url: str, headers: dict[str, str]) -> _FakeResponse:
            assert url == "https://vault.example.com/v1/env/data/templates/dev"
            assert headers["X-Vault-Token"] == "client-token-value"
            return _FakeResponse(
                {
                    "data": {
                        "data": {
                            "DATABASE_URL": "postgresql+asyncpg://db",
                            "FILES_SERVICE_AUTH_TOKEN": "abc123",
                            "NESTED": {"feature": True},
                        }
                    }
                }
            )

    monkeypatch.setenv("VAULT_ENABLED", "true")
    monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com")
    monkeypatch.setenv("VAULT_ROLE_ID", "role-id-value")
    monkeypatch.setenv("VAULT_SECRET_ID", "secret-id-value")
    monkeypatch.setenv("VAULT_KV_MOUNT", "env")
    monkeypatch.setenv("VAULT_KV_PATH", "templates/dev")
    monkeypatch.setenv("VAULT_TIMEOUT_SECONDS", "15")
    monkeypatch.setattr(vault.httpx, "Client", _FakeClient)

    vault.load_vault_secrets_into_environment()

    assert os.environ["DATABASE_URL"] == "postgresql+asyncpg://db"
    assert os.environ["FILES_SERVICE_AUTH_TOKEN"] == "abc123"
    assert os.environ["NESTED"] == '{"feature":true}'


def test_raises_when_required_secret_id_is_missing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VAULT_ENABLED", "true")
    monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com")
    monkeypatch.setenv("VAULT_ROLE_ID", "role-id-value")
    monkeypatch.setenv("VAULT_KV_MOUNT", "env")
    monkeypatch.setenv("VAULT_KV_PATH", "templates/dev")
    monkeypatch.setenv("VAULT_FAIL_FAST", "true")

    with pytest.raises(RuntimeError, match="VAULT_SECRET_ID"):
        vault.load_vault_secrets_into_environment()


def test_does_not_raise_when_fail_fast_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VAULT_ENABLED", "true")
    monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com")
    monkeypatch.setenv("VAULT_ROLE_ID", "role-id-value")
    monkeypatch.setenv("VAULT_KV_MOUNT", "env")
    monkeypatch.setenv("VAULT_KV_PATH", "templates/dev")
    monkeypatch.setenv("VAULT_FAIL_FAST", "false")

    vault.load_vault_secrets_into_environment()
