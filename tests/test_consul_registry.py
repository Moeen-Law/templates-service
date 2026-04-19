from types import SimpleNamespace

import pytest

from app.integrations.consul_registry import ConsulServiceRegistry


class _FakeResponse:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code = status_code
        self.text = text


def _build_settings() -> SimpleNamespace:
    return SimpleNamespace(
        consul_host="discovery.moeenlaw.com",
        consul_port=443,
        consul_scheme="https",
        consul_secure=True,
        consul_token="test-token",
        consul_service_name="template-service",
        consul_service_id="",
        consul_service_address="",
        consul_check_http="",
        consul_check_interval="15s",
        consul_check_timeout="5s",
        consul_check_deregister_critical_service_after="1m",
        service_name="template-service",
        host="0.0.0.0",
        port=9000,
    )


@pytest.mark.asyncio
async def test_register_service_uses_expected_payload(monkeypatch):
    calls: list[tuple[str, str, dict | None, dict | None, dict | None]] = []

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def put(
            self,
            url: str,
            params: dict | None = None,
            json: dict | None = None,
            headers: dict | None = None,
        ):
            calls.append(("PUT", url, params, json, headers))
            return _FakeResponse(status_code=200)

    monkeypatch.setattr(
        "app.integrations.consul_registry.httpx.AsyncClient", _FakeAsyncClient
    )

    registry = ConsulServiceRegistry(settings=_build_settings())
    await registry.register()

    assert len(calls) == 1
    method, url, params, payload, headers = calls[0]

    assert method == "PUT"
    assert url == "https://discovery.moeenlaw.com:443/v1/agent/service/register"
    assert params == {"replace-existing-checks": "true"}
    assert payload is not None
    assert payload["Name"] == "template-service"
    assert payload["Port"] == 9000
    assert payload["Check"] == {
        "HTTP": "http://127.0.0.1:9000/health",
        "Interval": "15s",
        "Timeout": "5s",
        "DeregisterCriticalServiceAfter": "1m",
    }
    assert headers == {
        "X-Consul-Token": "test-token",
        "Content-Type": "application/json",
    }


@pytest.mark.asyncio
async def test_deregister_service_calls_expected_endpoint(monkeypatch):
    calls: list[tuple[str, str, dict | None]] = []

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def put(
            self,
            url: str,
            headers: dict | None = None,
            params: dict | None = None,
            json: dict | None = None,
        ):
            calls.append(("PUT", url, headers))
            return _FakeResponse(status_code=200)

    monkeypatch.setattr(
        "app.integrations.consul_registry.httpx.AsyncClient", _FakeAsyncClient
    )

    registry = ConsulServiceRegistry(settings=_build_settings())
    await registry.deregister()

    assert len(calls) == 1
    method, url, headers = calls[0]
    assert method == "PUT"
    assert "/v1/agent/service/deregister/template-service-" in url
    assert headers == {
        "X-Consul-Token": "test-token",
        "Content-Type": "application/json",
    }


@pytest.mark.asyncio
async def test_register_raises_on_consul_error(monkeypatch):
    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def put(
            self,
            url: str,
            params: dict | None = None,
            json: dict | None = None,
            headers: dict | None = None,
        ):
            return _FakeResponse(status_code=403, text="permission denied")

    monkeypatch.setattr(
        "app.integrations.consul_registry.httpx.AsyncClient", _FakeAsyncClient
    )

    registry = ConsulServiceRegistry(settings=_build_settings())

    with pytest.raises(RuntimeError, match="Failed to register service with Consul"):
        await registry.register()
