from datetime import date
import logging
from typing import Any

from app.models.template import TemplateField
from app.schemas.common import FieldType

logger = logging.getLogger(__name__)


class ValidationService:
    def validate_data(
        self,
        fields: list[TemplateField],
        data: dict[str, Any],
    ) -> list[dict[str, str]]:
        logger.debug(
            "Validating contract data fields=%s provided_keys=%s",
            len(fields),
            sorted(data.keys()),
        )
        errors: list[dict[str, str]] = []
        field_map = {field.name: field for field in fields}

        for field in fields:
            value = data.get(field.name)
            if field.required and field.name not in data:
                errors.append(
                    {
                        "type": "missing_field",
                        "field": field.name,
                        "message": "Field is required",
                    }
                )
                continue

            if field.required and self._is_empty(value):
                errors.append(
                    {
                        "type": "empty_required",
                        "field": field.name,
                        "message": "Required field cannot be empty",
                    }
                )
                continue

            if field.name in data and not self._is_valid_type(field.type, value):
                errors.append(
                    {
                        "type": "invalid_type",
                        "field": field.name,
                        "message": self._expected_message(field.type),
                    }
                )

        for key in data:
            if key not in field_map:
                errors.append(
                    {
                        "type": "extra_field",
                        "field": key,
                        "message": "Field is not defined in template schema",
                    }
                )

        if errors:
            logger.debug("Validation produced errors count=%s", len(errors))
        else:
            logger.debug("Validation completed successfully")
        return errors

    @staticmethod
    def _is_empty(value: Any) -> bool:
        return value in (None, "", [], {})

    @staticmethod
    def _is_valid_type(expected_type: str, value: Any) -> bool:
        if value is None:
            return True

        field_type = FieldType(expected_type)

        if field_type is FieldType.string:
            return isinstance(value, str)
        if field_type is FieldType.number:
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if field_type is FieldType.boolean:
            return isinstance(value, bool)
        if field_type is FieldType.array:
            return isinstance(value, list)
        if field_type is FieldType.date:
            if not isinstance(value, str):
                return False
            try:
                date.fromisoformat(value)
                return True
            except ValueError:
                return False
        return False

    @staticmethod
    def _expected_message(field_type: str) -> str:
        if field_type == FieldType.date.value:
            return "Expected YYYY-MM-DD"
        return f"Expected type '{field_type}'"
