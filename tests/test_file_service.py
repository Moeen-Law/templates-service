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
        files_service_download_path_template="/files/api/v1/files/{file_id}",
        files_service_upload_url_path="/files/api/v1/files/upload-url",
        files_service_upload_bucket="AI_DOCUMENTS",
        files_service_uploader_id="uploader-1",
        files_service_auth_token="test-token",
        files_service_timeout_seconds=20,
        files_service_verify_tls=True,
    )
    return client


@pytest.mark.asyncio
async def test_download_template_supports_direct_docx_response(monkeypatch):
    direct_docx_bytes = b"PK\x03\x04fake-docx-content"
    calls: list[tuple[str, str, dict[str, str] | None]] = []

    responses = [
        _FakeResponse(
            status_code=200,
            content=direct_docx_bytes,
            headers={
                "content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            },
        )
    ]

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url: str, headers: dict[str, str] | None = None):
            calls.append(("GET", url, headers))
            return responses.pop(0)

    monkeypatch.setattr(
        "app.integrations.file_service.httpx.AsyncClient", _FakeAsyncClient
    )

    client = _build_client()
    result = await client.download_template("file-123")

    assert result == direct_docx_bytes
    assert calls == [
        (
            "GET",
            "https://gateway.moeenlaw.com/files/api/v1/files/file-123",
            {"Authorization": "Bearer test-token"},
        )
    ]


@pytest.mark.asyncio
async def test_download_template_resolves_metadata_download_url(monkeypatch):
    metadata_json = {
        "fileId": "file-123",
        "downloadUrl": "https://blob.moeenlaw.com/template-documents/file-123/1.docx?sig=abc",
    }
    docx_bytes = b"PK\x03\x04binary-docx"
    calls: list[tuple[str, str, dict[str, str] | None]] = []

    responses = [
        _FakeResponse(
            status_code=200,
            content=b'{"downloadUrl":"https://blob.moeenlaw.com/template-documents/file-123/1.docx?sig=abc"}',
            headers={"content-type": "application/json"},
            json_data=metadata_json,
            has_json=True,
        ),
        _FakeResponse(
            status_code=200,
            content=docx_bytes,
            headers={
                "content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            },
        ),
    ]

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url: str, headers: dict[str, str] | None = None):
            calls.append(("GET", url, headers))
            return responses.pop(0)

    monkeypatch.setattr(
        "app.integrations.file_service.httpx.AsyncClient", _FakeAsyncClient
    )

    client = _build_client()
    result = await client.download_template("file-123")

    assert result == docx_bytes
    assert calls == [
        (
            "GET",
            "https://gateway.moeenlaw.com/files/api/v1/files/file-123",
            {"Authorization": "Bearer test-token"},
        ),
        (
            "GET",
            "https://blob.moeenlaw.com/template-documents/file-123/1.docx?sig=abc",
            {},
        ),
    ]


@pytest.mark.asyncio
async def test_download_template_raises_for_metadata_without_download_url(monkeypatch):
    responses = [
        _FakeResponse(
            status_code=200,
            content=b'{"fileId":"file-123"}',
            headers={"content-type": "application/json"},
            json_data={"fileId": "file-123"},
            has_json=True,
        )
    ]

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url: str, headers: dict[str, str] | None = None):
            return responses.pop(0)

    monkeypatch.setattr(
        "app.integrations.file_service.httpx.AsyncClient", _FakeAsyncClient
    )

    client = _build_client()

    with pytest.raises(
        FileServiceError, match="Failed to resolve template download URL"
    ):
        await client.download_template("file-123")


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
