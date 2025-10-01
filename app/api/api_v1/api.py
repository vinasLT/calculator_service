from fastapi import APIRouter

from app.api.api_v1.endpoints.private.api import private_v1_router
from app.api.api_v1.endpoints.public.api import public_v1_router

api_v1_router = APIRouter(prefix="/v1")

api_v1_router.include_router(public_v1_router)

api_v1_router.include_router(private_v1_router)


