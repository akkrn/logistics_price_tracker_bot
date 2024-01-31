import datetime

from typing import TYPE_CHECKING
from sqlalchemy import (
    BigInteger,
    ForeignKey,
    String,
    UniqueConstraint,
    TIMESTAMP,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .product import Product
    from .stock import Stock


class Seller(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    api_token: Mapped[str] = mapped_column(String(450))
    added_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP)
    updated_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP)

    __table_args__ = (
        UniqueConstraint("api_token", "user_id", name="user_token_key"),
    )

    user: Mapped["User"] = relationship(back_populates="sellers")
    products: Mapped[list["Product"]] = relationship(back_populates="seller")
    stocks: Mapped[list["Stock"]] = relationship(back_populates="seller")
