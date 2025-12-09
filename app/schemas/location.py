from pydantic import BaseModel, Field

from app.core.utils import create_pagination_page
from app.database.schemas.location import LocationRead
from app.enums.auction import AuctionEnum


class GetLocationsIn(BaseModel):
    search: str | None = Field(None, description="Search by location name")
    auction: AuctionEnum | None = Field(None, description="Auction")


LocationPage = create_pagination_page(LocationRead)
