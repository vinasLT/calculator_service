from datetime import datetime, UTC

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base

class ExchangeRate(Base):
    __tablename__ = "exchange_rate"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    rate: Mapped[float] = mapped_column(nullable=False)
    # Use a callable so each row gets its own timestamp instead of sharing one value from import time
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )





