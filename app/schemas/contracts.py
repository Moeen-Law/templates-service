from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ValidationErrorType


class ContractGenerateRequest(BaseModel):
    template_id: str = Field(min_length=1)
    data: dict[str, Any]


class ValidationErrorDetail(BaseModel):
    type: ValidationErrorType
    field: str
    message: str


class ContractGenerateResponse(BaseModel):
    file_id: str


class ContractValidationErrorResponse(BaseModel):
    errors: list[ValidationErrorDetail]
