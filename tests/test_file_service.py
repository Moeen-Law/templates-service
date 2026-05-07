from types import SimpleNamespace

import pytest

from app.core.exceptions import FileServiceError
from app.integrations.file_service import FileServiceClient


class _FakeResponse:
    def __init__(
        self,
        *,
        status_code: int,
        content: bytes,
        headers: dict[str, str] | None = None,
        json_data: object | None = None,
        has_json: bool = False,
    ):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}
        self._json_data = json_data
        self._has_json = has_json
        self.text = content.decode("utf-8", errors="ignore")

    def json(self) -> object:
        if not self._has_json:
            raise ValueError("response does not contain JSON")
        return self._json_data


def _build_client() -> FileServiceClient:
    client = FileServiceClient()
    client._settings = SimpleNamespace(
        files_service_base_url="https://gateway.moeenlaw.com",
        files_service_upload_url_path="/files/api/v1/files/upload-url",
        files_service_upload_bucket="AI_DOCUMENTS",
        files_service_uploader_id="uploader-1",
        files_service_auth_token="test-token",
        files_service_timeout_seconds=20,
        files_service_verify_tls=True,
    )
    return client


@pytest.mark.asyncio
async def test_upload_document_uses_upload_url_and_storage_put(monkeypatch):
    calls: list[tuple] = []
    responses = [
        _FakeResponse(
            status_code=200,
            content=b'{"fileId":"generated-123","uploadUrl":"https://blob.moeenlaw.com/generated/generated-123/contract.docx","httpMethod":"PUT"}',
            json_data={
                "fileId": "generated-123",
                "uploadUrl": "https://blob.moeenlaw.com/generated/generated-123/contract.docx",
                "httpMethod": "PUT",
            },
            has_json=True,
        ),
        _FakeResponse(status_code=200, content=b""),
    ]

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url: str, json: dict | None = None, headers=None):
            calls.append(("POST", url, json, headers))
            return responses.pop(0)

        async def request(
            self,
            method: str,
            url: str,
            content: bytes | None = None,
            headers: dict[str, str] | None = None,
        ):
            calls.append(("REQUEST", method, url, content, headers))
            return responses.pop(0)

    monkeypatch.setattr(
        "app.integrations.file_service.httpx.AsyncClient", _FakeAsyncClient
    )

    client = _build_client()
    content = b"PK\x03\x04generated-docx"

    file_id = await client.upload_document("contract.docx", content)

    assert file_id == "generated-123"
    assert calls == [
        (
            "POST",
            "https://gateway.moeenlaw.com/files/api/v1/files/upload-url",
            {
                "fileName": "contract.docx",
                "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "bucket": "AI_DOCUMENTS",
                "uploaderId": "uploader-1",
                "uploader_id": "uploader-1",
            },
            {"Authorization": "Bearer test-token"},
        ),
        (
            "REQUEST",
            "PUT",
            "https://blob.moeenlaw.com/generated/generated-123/contract.docx",
            content,
            {
                "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            },
        ),
    ]


@pytest.mark.asyncio
async def test_upload_document_raises_when_storage_upload_fails(monkeypatch):
    responses = [
        _FakeResponse(
            status_code=200,
            content=b'{"fileId":"generated-123","uploadUrl":"https://blob.moeenlaw.com/generated/generated-123/contract.docx","httpMethod":"PUT"}',
            json_data={
                "fileId": "generated-123",
                "uploadUrl": "https://blob.moeenlaw.com/generated/generated-123/contract.docx",
                "httpMethod": "PUT",
            },
            has_json=True,
        ),
        _FakeResponse(status_code=415, content=b"unsupported media"),
    ]

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url: str, json: dict | None = None, headers=None):
            return responses.pop(0)

        async def request(
            self,
            method: str,
            url: str,
            content: bytes | None = None,
            headers: dict[str, str] | None = None,
        ):
            return responses.pop(0)

    monkeypatch.setattr(
        "app.integrations.file_service.httpx.AsyncClient", _FakeAsyncClient
    )

    client = _build_client()

    with pytest.raises(
        FileServiceError, match="Failed to upload generated contract to File Service"
    ):
        await client.upload_document("contract.docx", b"PK\x03\x04generated-docx")
