from app.services.validation_service import ValidationService


class Field:
    def __init__(self, name: str, type_: str, required: bool):
        self.name = name
        self.type = type_
        self.required = required


def test_validation_catches_missing_extra_and_invalid_type():
    service = ValidationService()
    fields = [
        Field("client_name", "string", True),
        Field("has_partner", "boolean", True),
        Field("start_date", "date", True),
    ]
    data = {
        "client_name": "ACME",
        "has_partner": "yes",
        "unexpected": 123,
    }

    errors = service.validate_data(fields=fields, data=data)
    assert {item["type"] for item in errors} == {
        "invalid_type",
        "missing_field",
        "extra_field",
    }


def test_validation_catches_empty_required():
    service = ValidationService()
    fields = [Field("client_name", "string", True)]

    errors = service.validate_data(fields=fields, data={"client_name": ""})
    assert errors[0]["type"] == "empty_required"
