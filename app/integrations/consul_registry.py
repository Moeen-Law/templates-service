import logging
import socket
from urllib.parse import quote

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class ConsulServiceRegistry:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._service_name = (
            self._settings.consul_service_name or self._settings.service_name
        ).strip()
        if not self._service_name:
            raise RuntimeError("Consul service name is required")

        explicit_service_id = self._settings.consul_service_id.strip()
        self._service_id = (
            explicit_service_id or f"{self._service_name}-{socket.gethostname()}"
        )

    def _base_url(self) -> str:
        host = self._settings.consul_host.strip()
        if not host:
            raise RuntimeError("Consul host is required when CONSUL is enabled")

        scheme = (
            "https" if self._settings.consul_secure else self._settings.consul_scheme
        )
        return f"{scheme}://{host}:{self._settings.consul_port}"

    def _default_headers(self) -> dict[str, str]:
        if not self._settings.consul_token.strip():
            raise RuntimeError("Consul token is required when CONSUL is enabled")

        return {
            "X-Consul-Token": self._settings.consul_token,
            "Content-Type": "application/json",
        }

    def _resolve_service_address(self) -> str:
        if self._settings.consul_service_address.strip():
            return self._settings.consul_service_address.strip()

        candidate = self._settings.host.strip()
        if candidate and candidate not in {"0.0.0.0", "::"}:
            return candidate
        return ""

    def _resolve_check_http(self) -> str:
        if self._settings.consul_check_http.strip():
            return self._settings.consul_check_http.strip()

        return f"http://127.0.0.1:{self._settings.port}/health"

    def _register_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "ID": self._service_id,
            "Name": self._service_name,
            "Port": self._settings.port,
            "Tags": self._settings.consul_registration_tags,
            "Check": {
                "HTTP": self._resolve_check_http(),
                "Interval": self._settings.consul_check_interval,
                "Timeout": self._settings.consul_check_timeout,
                "DeregisterCriticalServiceAfter": self._settings.consul_check_deregister_critical_service_after,
            },
        }

        service_address = self._resolve_service_address()
        if service_address:
            payload["Address"] = service_address

        return payload

    async def register(self) -> None:
        endpoint = f"{self._base_url()}/v1/agent/service/register"
        payload = self._register_payload()

        logger.info(
            "Registering service in Consul service_id=%s service_name=%s consul_host=%s",
            self._service_id,
            self._service_name,
            self._settings.consul_host,
        )

        async with httpx.AsyncClient(timeout=10.0, verify=True) as client:
            response = await client.put(
                endpoint,
                params={"replace-existing-checks": "true"},
                json=payload,
                headers=self._default_headers(),
            )

        if response.status_code >= 400:
            raise RuntimeError(
                "Failed to register service with Consul "
                f"status={response.status_code} response={response.text}"
            )

        logger.info("Consul registration completed service_id=%s", self._service_id)

    async def deregister(self) -> None:
        endpoint = (
            f"{self._base_url()}/v1/agent/service/deregister/"
            f"{quote(self._service_id, safe='')}"
        )
        logger.info("Deregistering service from Consul service_id=%s", self._service_id)

        async with httpx.AsyncClient(timeout=10.0, verify=True) as client:
            response = await client.put(endpoint, headers=self._default_headers())

        if response.status_code >= 400:
            raise RuntimeError(
                "Failed to deregister service from Consul "
                f"status={response.status_code} response={response.text}"
            )

        logger.info("Consul deregistration completed service_id=%s", self._service_id)
