import logging

import httpx

from app.core.config import get_settings
from app.core.exceptions import FileServiceError

logger = logging.getLogger(__name__)


class FileServiceClient:
    def __init__(self):
        self._settings = get_settings()

    def _default_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._settings.files_service_auth_token:
            headers["Authorization"] = (
                f"Bearer {self._settings.files_service_auth_token}"
            )
        return headers

    async def upload_document(self, filename: str, content: bytes) -> str:
        content_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        upload_target = await self._request_upload_url(
            filename=filename,
            content_type=content_type,
        )

        method = upload_target["http_method"].upper()
        if method not in {"PUT", "POST"}:
            logger.error(
                "Unsupported upload method from file service method=%s", method
            )
            raise FileServiceError(
                f"Unsupported upload method returned by File Service: '{method}'"
            )

        logger.info(
            "Uploading generated document to storage file_id=%s method=%s filename=%s size_bytes=%s",
            upload_target["file_id"],
            method,
            filename,
            len(content),
        )
        async with httpx.AsyncClient(
            timeout=self._settings.files_service_timeout_seconds,
            verify=self._settings.files_service_verify_tls,
        ) as client:
            response = await client.request(
                method,
                upload_target["upload_url"],
                content=content,
                headers={"Content-Type": content_type},
            )

        if response.status_code >= 400:
            logger.error(
                "Document upload to storage failed file_id=%s status=%s",
                upload_target["file_id"],
                response.status_code,
            )
            raise FileServiceError(
                "Failed to upload generated contract to File Service"
            )

        logger.info("Generated document uploaded file_id=%s", upload_target["file_id"])
        return upload_target["file_id"]

    async def _request_upload_url(
        self, filename: str, content_type: str
    ) -> dict[str, str]:
        url = (
            f"{self._settings.files_service_base_url}"
            f"{self._settings.files_service_upload_url_path}"
        )
        payload = {
            "fileName": filename,
            "mimeType": content_type,
            "bucket": self._settings.files_service_upload_bucket,
        }
        if self._settings.files_service_uploader_id:
            payload["uploaderId"] = self._settings.files_service_uploader_id
            payload["uploader_id"] = self._settings.files_service_uploader_id

        logger.info("Requesting upload URL filename=%s", filename)
        async with httpx.AsyncClient(
            timeout=self._settings.files_service_timeout_seconds,
            verify=self._settings.files_service_verify_tls,
        ) as client:
            response = await client.post(
                url,
                json=payload,
                headers=self._default_headers(),
            )

        if response.status_code >= 400:
            logger.error(
                "Upload URL request failed status=%s response=%s",
                response.status_code,
                response.text,
            )
            raise FileServiceError("Failed to get upload URL from File Service")

        data = response.json()
        file_id = data.get("fileId") or data.get("file_id")
        upload_url = data.get("uploadUrl") or data.get("upload_url")
        http_method = data.get("httpMethod") or data.get("http_method") or "PUT"

        if not file_id or not upload_url:
            logger.error("Upload URL response missing required fields payload=%s", data)
            raise FileServiceError("Upload URL response missing fileId or uploadUrl")

        return {
            "file_id": str(file_id),
            "upload_url": str(upload_url),
            "http_method": str(http_method),
        }
