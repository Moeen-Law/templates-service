from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class FieldType(str, Enum):
    string = "string"
    number = "number"
    boolean = "boolean"
    date = "date"
    array = "array"


class ValidationErrorType(str, Enum):
    missing_field = "missing_field"
    extra_field = "extra_field"
    invalid_type = "invalid_type"
    empty_required = "empty_required"
    template_mismatch = "template_mismatch"


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(ORMBaseModel):
    created_at: datetime
    updated_at: datetime
