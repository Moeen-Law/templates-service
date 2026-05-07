from fastapi.testclient import TestClient

from app.integrations.file_service import FileServiceClient
from app.main import app


def _build_template_markdown() -> str:
    return "\n".join(
        [
            "# Contract",
            "",
            "**Client:** {{ client_name }}",
            "**Company:** {{ company_name }}",
            "**Start date:** {{ start_date }}",
        ]
    )


def test_generate_contract_end_to_end_with_mocked_file_service(monkeypatch):
    async def fake_upload(self, filename: str, content: bytes) -> str:
        assert filename == "Employment Contract.docx"
        assert isinstance(content, bytes)
        assert len(content) > 0
        return "generated-file-123"

    monkeypatch.setattr(FileServiceClient, "upload_document", fake_upload)

    with TestClient(app) as client:
        create_response = client.post(
            "/templates",
            json={
                "name": "Employment Contract",
                "description": "Basic employment agreement",
                "markdown_content": _build_template_markdown(),
                "fields": [
                    {"name": "client_name", "type": "string", "required": True},
                    {"name": "company_name", "type": "string", "required": True},
                    {"name": "start_date", "type": "date", "required": True},
                ],
            },
        )
        assert create_response.status_code == 201

        template_id = create_response.json()["id"]

        generate_response = client.post(
            "/contracts/generate",
            json={
                "template_id": template_id,
                "data": {
                    "client_name": "Ahmed",
                    "company_name": "Moeen",
                    "start_date": "2026-04-11",
                },
            },
        )

        assert generate_response.status_code == 200
        assert generate_response.json() == {"file_id": "generated-file-123"}


def test_generate_contract_returns_validation_errors(monkeypatch):
    async def fake_upload(self, filename: str, content: bytes) -> str:
        return "generated-file-123"

    monkeypatch.setattr(FileServiceClient, "upload_document", fake_upload)

    with TestClient(app) as client:
        create_response = client.post(
            "/templates",
            json={
                "name": "Employment Contract",
                "description": "Basic employment agreement",
                "markdown_content": _build_template_markdown(),
                "fields": [
                    {"name": "client_name", "type": "string", "required": True},
                    {"name": "company_name", "type": "string", "required": True},
                    {"name": "start_date", "type": "date", "required": True},
                ],
            },
        )
        template_id = create_response.json()["id"]

        generate_response = client.post(
            "/contracts/generate",
            json={
                "template_id": template_id,
                "data": {
                    "client_name": "Ahmed",
                    "start_date": "not-a-date",
                },
            },
        )

        assert generate_response.status_code == 422
        errors = generate_response.json()["errors"]
        assert {item["type"] for item in errors} == {"missing_field", "invalid_type"}
