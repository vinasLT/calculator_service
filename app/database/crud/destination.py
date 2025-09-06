from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.base import BaseService

from app.database.models.destination import Destination
from app.database.schemas.destination import DestinationCreate, DestinationUpdate


class DestinationService(BaseService[Destination, DestinationCreate, DestinationUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(Destination, session)

    async def get_by_name(self, name: str) -> Destination | None:
        result = await self.session.execute(
            select(Destination)
            .where(
                Destination.name.ilike(name),
            )
        )
        return result.scalar_one_or_none()



    async def get_default(self)-> Destination | None:
        result = await self.session.execute(
            select(Destination)
            .where(
                Destination.is_default.is_(True),
            )
        )
        return result.scalar_one_or_none()





