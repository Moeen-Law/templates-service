from dataclasses import dataclass
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cache.in_memory import InMemoryCache
from app.core.config import get_settings
from app.core.exceptions import TemplateNotFoundError
from app.models.template import DocumentTemplate, TemplateField
from app.schemas.template import TemplateCreate, TemplateRead, TemplateUpdate

settings = get_settings()
_template_cache: InMemoryCache["TemplateContractData"] = InMemoryCache(
    ttl_seconds=settings.template_cache_ttl_seconds
)
logger = logging.getLogger(__name__)


@dataclass
class TemplateContractData:
    template_id: str
    name: str
    file_id: str
    fields: list[TemplateField]


class TemplateService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_template(self, payload: TemplateCreate) -> TemplateRead:
        logger.info(
            "Creating template name=%s fields=%s", payload.name, len(payload.fields)
        )
        template = DocumentTemplate(
            name=payload.name,
            description=payload.description,
            file_id=payload.file_id,
            fields=[
                TemplateField(
                    name=field.name,
                    type=field.type.value,
                    required=field.required,
                    description=field.description,
                    example=field.example,
                )
                for field in payload.fields
            ],
        )
        self._session.add(template)
        await self._session.commit()
        await self._session.refresh(template)
        logger.info("Template created template_id=%s", template.id)
        return TemplateRead.model_validate(template)

    async def list_templates(self) -> list[TemplateRead]:
        logger.debug("Listing templates")
        stmt = select(DocumentTemplate).options(selectinload(DocumentTemplate.fields))
        result = await self._session.scalars(stmt)
        templates = result.all()
        logger.info("Listed templates count=%s", len(templates))
        return [TemplateRead.model_validate(item) for item in templates]

    async def get_template(self, template_id: str) -> TemplateRead:
        logger.debug("Fetching template template_id=%s", template_id)
        template = await self._get_template_entity(template_id)
        return TemplateRead.model_validate(template)

    async def get_template_for_generation(
        self, template_id: str
    ) -> TemplateContractData:
        cache_key = f"template:{template_id}"
        cached = _template_cache.get(cache_key)
        if cached:
            logger.debug("Template cache hit template_id=%s", template_id)
            return cached

        logger.debug("Template cache miss template_id=%s", template_id)

        template = await self._get_template_entity(template_id)
        data = TemplateContractData(
            template_id=template.id,
            name=template.name,
            file_id=template.file_id,
            fields=template.fields,
        )
        _template_cache.set(cache_key, data)
        logger.debug("Template cached template_id=%s", template_id)
        return data

    async def update_template(
        self, template_id: str, payload: TemplateUpdate
    ) -> TemplateRead:
        logger.info("Updating template template_id=%s", template_id)
        template = await self._get_template_entity(template_id)

        if payload.name is not None:
            template.name = payload.name
        if payload.description is not None:
            template.description = payload.description
        if payload.file_id is not None:
            template.file_id = payload.file_id
        if payload.fields is not None:
            template.fields = [
                TemplateField(
                    name=field.name,
                    type=field.type.value,
                    required=field.required,
                    description=field.description,
                    example=field.example,
                )
                for field in payload.fields
            ]

        await self._session.commit()
        await self._session.refresh(template)
        _template_cache.delete(f"template:{template_id}")
        logger.info("Template updated template_id=%s", template_id)
        return TemplateRead.model_validate(template)

    async def delete_template(self, template_id: str) -> None:
        logger.info("Deleting template template_id=%s", template_id)
        template = await self._get_template_entity(template_id)
        await self._session.delete(template)
        await self._session.commit()
        _template_cache.delete(f"template:{template_id}")
        logger.info("Template deleted template_id=%s", template_id)

    async def _get_template_entity(self, template_id: str) -> DocumentTemplate:
        stmt = (
            select(DocumentTemplate)
            .where(DocumentTemplate.id == template_id)
            .options(selectinload(DocumentTemplate.fields))
        )
        template = await self._session.scalar(stmt)
        if template is None:
            logger.warning("Template not found in database template_id=%s", template_id)
            raise TemplateNotFoundError(f"Template '{template_id}' not found")
        return template
