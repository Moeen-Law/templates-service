import logging
import mimetypes
from urllib.parse import urljoin, urlparse

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
        metadata_url = (
            f"{self._settings.files_service_base_url}"
            f"{self._settings.files_service_download_path_template.format(file_id=file_id)}"
        )
        logger.info(
            "Downloading template from file service file_id=%s url=%s",
            file_id,
            metadata_url,
        )
        async with httpx.AsyncClient(
            timeout=self._settings.files_service_timeout_seconds,
            verify=self._settings.files_service_verify_tls,
        ) as client:
            response = await client.get(metadata_url, headers=self._default_headers())
            if response.status_code >= 400:
                logger.error(
                    "Template download failed file_id=%s status=%s",
                    file_id,
                    response.status_code,
                )
                raise FileServiceError(
                    f"Failed to download template file '{file_id}' from File Service"
                )

            if self._looks_like_docx(response.content):
                logger.info(
                    "Template downloaded file_id=%s status=%s size_bytes=%s",
                    file_id,
                    response.status_code,
                    len(response.content),
                )
                return response.content

            download_url = self._extract_download_url(response)
            if not download_url:
                logger.error(
                    "Template response is not DOCX and has no download URL file_id=%s content_type=%s",
                    file_id,
                    response.headers.get("content-type", ""),
                )
                raise FileServiceError(
                    f"Failed to resolve template download URL for file '{file_id}'"
                )

            resolved_download_url = self._resolve_download_url(download_url)
            logger.info(
                "Resolved template download URL file_id=%s url=%s",
                file_id,
                resolved_download_url,
            )
            file_response = await client.get(
                resolved_download_url,
                headers=self._download_headers_for_url(resolved_download_url),
            )

        if file_response.status_code >= 400:
            logger.error(
                "Template binary download failed file_id=%s status=%s",
                file_id,
                file_response.status_code,
            )
            raise FileServiceError(
                f"Failed to download template file '{file_id}' from resolved URL"
            )

        if not self._looks_like_docx(file_response.content):
            logger.error(
                "Template binary download is not DOCX file_id=%s status=%s content_type=%s size_bytes=%s",
                file_id,
                file_response.status_code,
                file_response.headers.get("content-type", ""),
                len(file_response.content),
            )
            raise FileServiceError(
                f"Downloaded template file '{file_id}' is not a valid DOCX document"
            )

        logger.info(
            "Template downloaded file_id=%s status=%s size_bytes=%s",
            file_id,
            file_response.status_code,
            len(file_response.content),
        )
        return file_response.content

    @staticmethod
    def _looks_like_docx(content: bytes) -> bool:
        # DOCX files are ZIP containers and start with ZIP magic bytes.
        return len(content) >= 4 and content[:4] == b"PK\x03\x04"

    @staticmethod
    def _extract_download_url(response: httpx.Response) -> str | None:
        try:
            payload = response.json()
        except ValueError:
            return None
        return FileServiceClient._find_download_url(payload)

    @staticmethod
    def _find_download_url(payload: object) -> str | None:
        preferred_keys = (
            "downloadUrl",
            "download_url",
            "fileUrl",
            "file_url",
            "signedUrl",
            "signed_url",
            "presignedUrl",
            "presigned_url",
            "publicUrl",
            "public_url",
            "url",
        )

        queue: list[object] = [payload]
        while queue:
            current = queue.pop(0)
            if isinstance(current, dict):
                for key in preferred_keys:
                    value = current.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
                for value in current.values():
                    if isinstance(value, (dict, list)):
                        queue.append(value)
            elif isinstance(current, list):
                for value in current:
                    if isinstance(value, (dict, list)):
                        queue.append(value)
        return None

    def _resolve_download_url(self, download_url: str) -> str:
        candidate = download_url.strip()
        if urlparse(candidate).scheme:
            return candidate

        base_url = self._settings.files_service_base_url.rstrip("/") + "/"
        return urljoin(base_url, candidate.lstrip("/"))

    def _download_headers_for_url(self, download_url: str) -> dict[str, str]:
        target_host = urlparse(download_url).netloc
        base_host = urlparse(self._settings.files_service_base_url).netloc
        if not target_host or target_host == base_host:
            return self._default_headers()
        return {}

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

    async def upload_template_file(
        self,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> str:
        resolved_content_type = (
            content_type
            or mimetypes.guess_type(filename)[0]
            or "application/octet-stream"
        )
        upload_target = await self._request_upload_url(
            filename=filename,
            content_type=resolved_content_type,
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
            "Uploading template bytes to storage file_id=%s method=%s",
            upload_target["file_id"],
            method,
        )
        async with httpx.AsyncClient(
            timeout=self._settings.files_service_timeout_seconds,
            verify=self._settings.files_service_verify_tls,
        ) as client:
            response = await client.request(
                method,
                upload_target["upload_url"],
                content=content,
                headers={"Content-Type": resolved_content_type},
            )

        if response.status_code >= 400:
            logger.error(
                "Template upload to storage failed file_id=%s status=%s",
                upload_target["file_id"],
                response.status_code,
            )
            raise FileServiceError("Failed to upload template file to storage")

        logger.info("Template uploaded file_id=%s", upload_target["file_id"])
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
