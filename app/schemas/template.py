from pydantic import BaseModel, Field

from app.schemas.common import FieldType, ORMBaseModel, TimestampSchema


class TemplateFieldBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    type: FieldType
    required: bool = True
    description: str | None = None
    example: str | None = None


class TemplateFieldCreate(TemplateFieldBase):
    pass


class TemplateFieldRead(TemplateFieldBase, ORMBaseModel):
    id: str
    template_id: str


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    markdown_content: str = Field(min_length=1)
    fields: list[TemplateFieldCreate]


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    markdown_content: str | None = Field(default=None, min_length=1)
    fields: list[TemplateFieldCreate] | None = None


class TemplateRead(TimestampSchema):
    id: str
    name: str
    description: str | None
    markdown_content: str
    fields: list[TemplateFieldRead]


class TemplateListResponse(BaseModel):
    items: list[TemplateRead]
