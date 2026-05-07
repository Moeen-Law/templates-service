from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DocumentTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "document_templates"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)

    fields: Mapped[list["TemplateField"]] = relationship(
        "TemplateField",
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class TemplateField(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "template_fields"

    template_id: Mapped[str] = mapped_column(
        ForeignKey("document_templates.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    example: Mapped[str | None] = mapped_column(Text, nullable=True)

    template: Mapped[DocumentTemplate] = relationship(
        "DocumentTemplate", back_populates="fields"
    )
