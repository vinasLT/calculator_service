from fastapi import APIRouter

from app.api.api_v1.api import private_v1_router
from app.api.api_v1.endpoints.private.exchange_rate import exchange_rate_router


private_v1_router.include_router(exchange_rate_router)