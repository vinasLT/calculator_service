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
        search_conditions = [Location.name.ilike(location_name)]

        if city and state:
            search_conditions.extend([
                Location.name.ilike(f"{city} {state}"),
                and_(Location.city.ilike(city), Location.state.ilike(state))
            ])

        result = await self.session.execute(
            select(Location)
            .join(DeliveryPrice)  # Join с таблицей delivery_price
            .where(
                and_(
                    or_(*search_conditions),
                    DeliveryPrice.vehicle_type_id == vehicle_type.id  # Фильтр по vehicle_type
                )
            )
            .distinct()  # Избегаем дублирования, если есть несколько DeliveryPrice для одной локации
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Location | None:
        result = await self.session.execute(
            select(Location).where(Location.name == name)
        )
        return result.scalar_one_or_none()










