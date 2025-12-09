from fastapi import APIRouter, Depends, Query
from fastapi_cache import default_key_builder
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.fee_type import FeeTypeService
from app.database.db.session import get_async_db
from app.database.schemas.fee_type import FeeTypeRead
from app.enums.auction import AuctionEnum

fee_type_api_router = APIRouter(prefix="/fee-types")


@fee_type_api_router.get(
    "",
    response_model=list[FeeTypeRead],
    tags=["fee_types"],
    description="Get all fee types (optionally filtered by auction)",
)
@cache(expire=60 * 5, key_builder=default_key_builder)
async def get_fee_types(
    auction: AuctionEnum | None = Query(None, description="Filter fee types by auction"),
    db: AsyncSession = Depends(get_async_db),
):
    fee_type_service = FeeTypeService(db)
    fee_types = await fee_type_service.list_fee_types(auction=auction)
    return [FeeTypeRead.model_validate(ft, from_attributes=True) for ft in fee_types]
