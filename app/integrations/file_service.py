from io import BytesIO
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

    async def download_template(self, file_id: str) -> bytes:
        url = (
            f"{self._settings.files_service_base_url}"
            f"{self._settings.files_service_download_path_template.format(file_id=file_id)}"
        )
        logger.info(
            "Downloading template from file service file_id=%s url=%s", file_id, url
        )
        async with httpx.AsyncClient(
            timeout=self._settings.files_service_timeout_seconds,
            verify=self._settings.files_service_verify_tls,
        ) as client:
            response = await client.get(url, headers=self._default_headers())
        if response.status_code >= 400:
            logger.error(
                "Template download failed file_id=%s status=%s",
                file_id,
                response.status_code,
            )
            raise FileServiceError(
                f"Failed to download template file '{file_id}' from File Service"
            )
        logger.info(
            "Template downloaded file_id=%s status=%s size_bytes=%s",
            file_id,
            response.status_code,
            len(response.content),
        )
        return response.content

    async def upload_document(self, filename: str, content: bytes) -> str:
        url = (
            f"{self._settings.files_service_base_url}"
            f"{self._settings.files_service_upload_url_path}"
        )
        logger.info(
            "Uploading generated document filename=%s size_bytes=%s url=%s",
            filename,
            len(content),
            url,
        )
        files = {
            "file": (
                filename,
                BytesIO(content),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        form_data = {
            "bucket": self._settings.files_service_upload_bucket,
            "uploader_id": self._settings.files_service_uploader_id,
        }
        async with httpx.AsyncClient(
            timeout=self._settings.files_service_timeout_seconds,
            verify=self._settings.files_service_verify_tls,
        ) as client:
            response = await client.post(
                url,
                files=files,
                data=form_data,
                headers=self._default_headers(),
            )
        if response.status_code >= 400:
            logger.error("Document upload failed status=%s", response.status_code)
            raise FileServiceError(
                "Failed to upload generated contract to File Service"
            )

        payload = response.json()
        file_id = payload.get("file_id")
        if not file_id:
            logger.error("Document upload response missing file_id")
            raise FileServiceError("File Service response missing 'file_id'")
        logger.info("Generated document uploaded file_id=%s", file_id)
        return file_id
