import re

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.base import BaseService, CreateSchemaType, ModelType
from app.database.models import Location, VehicleType, ShippingPrice, DeliveryPrice

from app.database.schemas.location import LocationCreate, LocationUpdate


class LocationService(BaseService[Location, LocationCreate, LocationUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(Location, session)

    async def get_location(self, location_name: str,
                                  vehicle_type: VehicleType,
                                  city: str | None = None,
                                  state: str | None = None) -> Location | None:

        # Очищаем название от скобок
        clean_name = re.sub(r'\s*\([^)]*\)', '', location_name).strip()

        # Пытаемся найти по разным критериям с приоритетом
        search_patterns = [
            location_name,  # Точное совпадение
            clean_name,  # Без скобок
            f"%{clean_name}%",  # Частичное совпадение
            f"{clean_name}%",  # Начинается с
        ]

        for pattern in search_patterns:
            result = await self.session.execute(
                select(Location)
                .join(DeliveryPrice)
                .where(
                    and_(
                        Location.name.ilike(pattern),
                        DeliveryPrice.vehicle_type_id == vehicle_type.id
                    )
                )
                .distinct()
                .limit(1)
            )

            location = result.scalar_one_or_none()
            if location:
                return location

        # Если не найдено и указаны город/штат, пробуем их
        if city and state:
            result = await self.session.execute(
                select(Location)
                .join(DeliveryPrice)
                .where(
                    and_(
                        or_(
                            Location.name.ilike(f"{city} {state}"),
                            and_(Location.city.ilike(city), Location.state.ilike(state))
                        ),
                        DeliveryPrice.vehicle_type_id == vehicle_type.id
                    )
                )
                .distinct()
                .limit(1)
            )
            return result.scalar_one_or_none()

        return None

    async def get_by_name(self, name: str) -> Location | None:
        result = await self.session.execute(
            select(Location).where(Location.name == name)
        )
        return result.scalar_one_or_none()










