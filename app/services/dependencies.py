from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.integrations.file_service import FileServiceClient
from app.services.contract_service import ContractService
from app.services.template_service import TemplateService


def get_template_service(
    session: AsyncSession = Depends(get_db_session),
) -> TemplateService:
    return TemplateService(session=session)


def get_contract_service(
    session: AsyncSession = Depends(get_db_session),
) -> ContractService:
    return ContractService(
        template_service=TemplateService(
            session=session,
        ),
        file_service_client=FileServiceClient(),
    )
