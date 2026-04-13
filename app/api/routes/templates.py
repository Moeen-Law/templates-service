import json

from fastapi import APIRouter, Depends, Response, status
from fastapi import HTTPException, Request
from pydantic import TypeAdapter, ValidationError as PydanticValidationError

from app.schemas.template import (
    TemplateCreate,
    TemplateFieldCreate,
    TemplateListResponse,
    TemplateRead,
    TemplateUpdate,
)
from app.services.dependencies import get_template_service
from app.services.template_service import TemplateService

router = APIRouter()


@router.post("", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
async def create_template(
    request: Request,
    service: TemplateService = Depends(get_template_service),
) -> TemplateRead:
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("application/json"):
        payload = TemplateCreate.model_validate(await request.json())
        return await service.create_template(payload)

    if content_type.startswith("multipart/form-data"):
        form = await request.form()

        name = form.get("name")
        description = form.get("description")
        fields_raw = form.get("fields")
        file_value = form.get("file")

        if not isinstance(name, str) or not name.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Form field 'name' is required",
            )
        if fields_raw is None or not isinstance(fields_raw, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Form field 'fields' must be a JSON array",
            )
        if (
            file_value is None
            or not hasattr(file_value, "filename")
            or not hasattr(file_value, "read")
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Form field 'file' is required",
            )

        try:
            fields_data = json.loads(fields_raw)
            fields = TypeAdapter(list[TemplateFieldCreate]).validate_python(fields_data)
        except (json.JSONDecodeError, PydanticValidationError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid 'fields' payload: {exc}",
            ) from exc

        content = await file_value.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Uploaded template file is empty",
            )

        return await service.create_template_with_file(
            name=name.strip(),
            description=description if isinstance(description, str) else None,
            fields=fields,
            filename=file_value.filename or "template.docx",
            content=content,
            content_type=file_value.content_type,
        )

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Use application/json or multipart/form-data",
    )


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
