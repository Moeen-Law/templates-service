import json
from dataclasses import dataclass

from app.core import config


@dataclass
class _FakeSettings:
    vault_enabled: bool
    vault_addr: str = "https://vault.example.com"
    vault_role_id: str = "role-id"
    vault_secret_id: str = "secret-id"
    vault_auth_path: str = "approle"
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
        _FakeSettings(vault_enabled=True, vault_role_id="bootstrap-role"),
        _FakeSettings(vault_enabled=True, vault_role_id="resolved-role"),
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

    assert resolved.vault_role_id == "resolved-role"
    assert len(calls) == 1
    assert calls[0]["enabled"] is True
    assert calls[0]["vault_role_id"] == "bootstrap-role"
    assert env_calls == ["production", "production"]

    config.get_settings.cache_clear()


def test_get_settings_returns_bootstrap_when_vault_disabled(monkeypatch):
    config.get_settings.cache_clear()

    calls: list[dict] = []
    env_calls: list[str] = []
    bootstrap = _FakeSettings(
        vault_enabled=False,
        vault_role_id="",
        vault_secret_id="",
    )

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


def test_settings_supports_nested_consul_blob(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("CONSUL_ENABLED", raising=False)
    monkeypatch.delenv("CONSUL_HOST", raising=False)
    monkeypatch.delenv("CONSUL_PORT", raising=False)
    monkeypatch.delenv("CONSUL_SCHEME", raising=False)
    monkeypatch.delenv("CONSUL_SERVICE_NAME", raising=False)
    monkeypatch.delenv("CONSUL_TOKEN", raising=False)
    monkeypatch.delenv("CONSUL_REGISTRATION_TAGS", raising=False)
    monkeypatch.delenv("CONSUL_QUERY_TAGS", raising=False)
    monkeypatch.delenv("consul", raising=False)
    monkeypatch.delenv("CONSUL", raising=False)

    monkeypatch.setenv(
        "consul",
        json.dumps(
            {
                "host": "discovery.moeenlaw.com",
                "port": "443",
                "schema": "https",
                "secure": True,
                "serviceName": "template-service",
                "token": "test-token",
                "tags": ["dev"],
                "queryTags": ["dev"],
                "check": {
                    "deregisterCriticalServiceAfter": "1m",
                    "http": "",
                    "interval": "15s",
                    "timeout": "5s",
                },
            }
        ),
    )

    settings = config.Settings()

    assert settings.consul_enabled is True
    assert settings.consul_host == "discovery.moeenlaw.com"
    assert settings.consul_port == 443
    assert settings.consul_scheme == "https"
    assert settings.consul_secure is True
    assert settings.consul_service_name == "template-service"
    assert settings.consul_token == "test-token"
    assert settings.consul_registration_tags == ["dev"]
    assert settings.consul_query_tags == ["dev"]
    assert settings.consul_check_interval == "15s"
    assert settings.consul_check_timeout == "5s"
    assert settings.consul_check_deregister_critical_service_after == "1m"


def test_flat_consul_env_overrides_nested_blob(monkeypatch):
    monkeypatch.setenv(
        "consul",
        json.dumps(
            {
                "host": "discovery.moeenlaw.com",
                "port": "443",
                "schema": "https",
            }
        ),
    )
    monkeypatch.setenv("CONSUL_HOST", "consul-override.moeenlaw.com")

    settings = config.Settings()

    assert settings.consul_host == "consul-override.moeenlaw.com"


def test_settings_default_consul_tags_follow_environment(monkeypatch):
    monkeypatch.delenv("CONSUL_REGISTRATION_TAGS", raising=False)
    monkeypatch.delenv("CONSUL_QUERY_TAGS", raising=False)
    monkeypatch.delenv("consul", raising=False)
    monkeypatch.delenv("CONSUL", raising=False)

    monkeypatch.setenv("ENVIRONMENT", "dev")
    development_settings = config.Settings()

    monkeypatch.setenv("ENVIRONMENT", "production")
    production_settings = config.Settings()

    assert development_settings.consul_registration_tags == ["dev"]
    assert development_settings.consul_query_tags == ["dev"]
    assert production_settings.consul_registration_tags == ["prod"]
    assert production_settings.consul_query_tags == ["prod"]


def test_flat_consul_tag_env_overrides_profile_defaults(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CONSUL_REGISTRATION_TAGS", "blue,green")
    monkeypatch.setenv("CONSUL_QUERY_TAGS", '["canary"]')
    monkeypatch.delenv("consul", raising=False)
    monkeypatch.delenv("CONSUL", raising=False)

    settings = config.Settings()

    assert settings.consul_registration_tags == ["blue", "green"]
    assert settings.consul_query_tags == ["canary"]
