import uvicorn
from fastapi import FastAPI

from app.api.api_v1.api import public_v1_router
from app.core.app_factory import create_app

app: FastAPI = create_app()

app = FastAPI()

app.include_router(public_v1_router)

if __name__ == "__main__":
    uvicorn.run(app, port=8000)