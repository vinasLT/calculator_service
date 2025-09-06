from pydantic import BaseModel


class City(BaseModel):
    name: str
    price: int

class VATs(BaseModel):
    vats: list[City]
    eu_vats: list[City]

class BaseCalculator(BaseModel):
    broker_fee: int
    transportation_price: list[City]
    ocean_ship: list[City]
    additional: int
    totals: list[City]

class DefaultCalculator(BaseCalculator):
    auction_fee: int
    live_fee: int
    internet_fee: int

class EUCalculator(BaseCalculator):
    vats: VATs
    custom_agency: int

class CalculatorOut(BaseModel):
    calculator: DefaultCalculator
    eu_calculator: EUCalculator

    calculator_in_euro: DefaultCalculator
    eu_calculator_in_euro: EUCalculator



class AdditionalFeesOut(BaseModel):
    summ: int
    auction_fee: int
    live_fee: int
    internet_fee: int