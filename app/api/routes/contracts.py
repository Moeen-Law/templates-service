from fastapi import APIRouter, Depends

from app.schemas.contracts import ContractGenerateRequest, ContractGenerateResponse
from app.services.contract_service import ContractService
from app.services.dependencies import get_contract_service

router = APIRouter()


@router.post("/generate", response_model=ContractGenerateResponse)
async def generate_contract(
    payload: ContractGenerateRequest,
    service: ContractService = Depends(get_contract_service),
) -> ContractGenerateResponse:
    file_id = await service.generate_contract(
        template_id=payload.template_id,
        data=payload.data,
    )
    return ContractGenerateResponse(file_id=file_id)
