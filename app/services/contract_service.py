from app.core.exceptions import ValidationError
from app.integrations.file_service import FileServiceClient
from app.services.render_service import RenderService
from app.services.template_service import TemplateService
from app.services.validation_service import ValidationService


class ContractService:
    def __init__(
        self,
        template_service: TemplateService,
        file_service_client: FileServiceClient,
    ):
        self._template_service = template_service
        self._file_service_client = file_service_client
        self._render_service = RenderService()
        self._validation_service = ValidationService()

    async def generate_contract(self, template_id: str, data: dict) -> str:
        template = await self._template_service.get_template_for_generation(template_id)

        validation_errors = self._validation_service.validate_data(
            template.fields, data
        )
        if validation_errors:
            raise ValidationError(validation_errors)

        template_bytes = await self._file_service_client.download_template(
            template.file_id
        )
        placeholder_errors = self._validate_placeholders(
            template_placeholders=self._render_service.extract_placeholders(
                template_bytes
            ),
            field_names={field.name for field in template.fields},
        )
        if placeholder_errors:
            raise ValidationError(placeholder_errors)

        rendered = self._render_service.render_docx(template_bytes, data)
        generated_file_id = await self._file_service_client.upload_document(
            filename=f"{template.name}.docx",
            content=rendered,
        )
        return generated_file_id

    @staticmethod
    def _validate_placeholders(
        template_placeholders: set[str],
        field_names: set[str],
    ) -> list[dict[str, str]]:
        errors: list[dict[str, str]] = []

        missing_in_db = sorted(template_placeholders - field_names)
        if missing_in_db:
            for name in missing_in_db:
                errors.append(
                    {
                        "type": "template_mismatch",
                        "field": name,
                        "message": "Placeholder is missing in DB field schema",
                    }
                )

        missing_in_template = sorted(field_names - template_placeholders)
        if missing_in_template:
            for name in missing_in_template:
                errors.append(
                    {
                        "type": "template_mismatch",
                        "field": name,
                        "message": "DB field is missing in template placeholders",
                    }
                )

        return errors
