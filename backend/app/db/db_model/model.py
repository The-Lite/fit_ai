from datetime import  datetime
from decimal import Decimal

from sqlalchemy import String, Numeric, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class FlyerItem(Base):
    __tablename__ = "flyer_items"

    item_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    price_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    store_name: Mapped[str | None] = mapped_column(String(100), nullable=False)
    flyer_date_start: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, primary_key=True)
    flyer_date_end: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, primary_key=True)