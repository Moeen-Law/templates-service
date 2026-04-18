from dataclasses import dataclass

from app.core import config


@dataclass
class _FakeSettings:
    vault_enabled: bool
    vault_addr: str = "https://vault.example.com"
    vault_token: str = "token"
    vault_kv_mount: str = "env"
    vault_kv_path: str = "templates/dev"
    vault_namespace: str = ""
    vault_timeout_seconds: float = 10
    vault_fail_fast: bool = True
    vault_skip_verify: bool = False
    vault_cacert: str = ""
    database_url: str = "postgresql+asyncpg://db"


def test_get_settings_uses_bootstrap_vault_values(monkeypatch):
    config.get_settings.cache_clear()

    calls: list[dict] = []
    env_calls: list[str] = []
    settings_instances = [
        _FakeSettings(vault_enabled=True, vault_token="bootstrap-token"),
        _FakeSettings(vault_enabled=True, vault_token="resolved-token"),
    ]

    def fake_get_current_environment() -> str:
        return "production"

    def fake_load_settings_for_environment(environment: str):
        env_calls.append(environment)
        return settings_instances.pop(0)

    def fake_load_vault_secrets_into_environment(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(config, "get_current_environment", fake_get_current_environment)
    monkeypatch.setattr(
        config,
        "load_settings_for_environment",
        fake_load_settings_for_environment,
    )
    monkeypatch.setattr(
        config,
        "load_vault_secrets_into_environment",
        fake_load_vault_secrets_into_environment,
    )

    resolved = config.get_settings()

    assert resolved.vault_token == "resolved-token"
    assert len(calls) == 1
    assert calls[0]["enabled"] is True
    assert calls[0]["vault_token"] == "bootstrap-token"
    assert env_calls == ["production", "production"]

    config.get_settings.cache_clear()


def test_get_settings_returns_bootstrap_when_vault_disabled(monkeypatch):
    config.get_settings.cache_clear()

    calls: list[dict] = []
    env_calls: list[str] = []
    bootstrap = _FakeSettings(vault_enabled=False, vault_token="")

    def fake_get_current_environment() -> str:
        return "development"

    def fake_load_settings_for_environment(environment: str):
        env_calls.append(environment)
        return bootstrap

    def fake_load_vault_secrets_into_environment(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(config, "get_current_environment", fake_get_current_environment)
    monkeypatch.setattr(
        config,
        "load_settings_for_environment",
        fake_load_settings_for_environment,
    )
    monkeypatch.setattr(
        config,
        "load_vault_secrets_into_environment",
        fake_load_vault_secrets_into_environment,
    )

    resolved = config.get_settings()

    assert resolved is bootstrap
    assert len(calls) == 1
    assert calls[0]["enabled"] is False
    assert env_calls == ["development"]

    config.get_settings.cache_clear()


def test_get_current_environment_prefers_process_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setattr(config, "_read_dotenv_value", lambda *_: "dev")

    assert config.get_current_environment() == "production"


def test_get_environment_env_files_maps_aliases():
    assert config.get_environment_env_files("dev") == (".env", ".env.dev")
    assert config.get_environment_env_files("production") == (".env", ".env.prod")
