from fastapi import APIRouter, Depends, Response, status

from app.schemas.template import (
    TemplateCreate,
    TemplateListResponse,
    TemplateRead,
    TemplateUpdate,
)
from app.services.dependencies import get_template_service
from app.services.template_service import TemplateService

router = APIRouter()


@router.post("", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: TemplateCreate,
    service: TemplateService = Depends(get_template_service),
) -> TemplateRead:
    return await service.create_template(payload)


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    service: TemplateService = Depends(get_template_service),
) -> TemplateListResponse:
    items = await service.list_templates()
    return TemplateListResponse(items=items)


@router.get("/{template_id}", response_model=TemplateRead)
async def get_template(
    template_id: str,
    service: TemplateService = Depends(get_template_service),
) -> TemplateRead:
    return await service.get_template(template_id)


@router.put("/{template_id}", response_model=TemplateRead)
async def update_template(
    template_id: str,
    payload: TemplateUpdate,
    service: TemplateService = Depends(get_template_service),
) -> TemplateRead:
    return await service.update_template(template_id, payload)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    service: TemplateService = Depends(get_template_service),
) -> Response:
    await service.delete_template(template_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
