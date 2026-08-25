from fastapi import APIRouter, Depends

from apps.store.adapter.inbound.api.schemas.store_schema import StoreResponse
from apps.store.adapter.inbound.mappers.store_mapper import to_response
from apps.store.app.ports.input.store_use_case import StoreUseCase
from apps.store.dependencies.store_dependencies import get_store_use_case

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("/myself", response_model=StoreResponse)
def myself(
    use_case: StoreUseCase = Depends(get_store_use_case),
) -> StoreResponse:
    return to_response(use_case.myself())
