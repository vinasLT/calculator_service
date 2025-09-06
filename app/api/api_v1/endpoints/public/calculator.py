from fastapi import APIRouter
from fastapi.params import Param

from schemas.calculator import CalculatorDataIn

calculator_api_router = APIRouter(prefix="/calculator")

@calculator_api_router.get("", tags=["calculator"], name='get_calculator')
async def get_calculator(data: CalculatorDataIn = Param(...)):

