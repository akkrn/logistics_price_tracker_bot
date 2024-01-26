import datetime
from typing import TYPE_CHECKING
from pydantic import json
from sqlalchemy import (
    BigInteger,
    ForeignKey,
    String,
    UniqueConstraint,
    Text,
    JSON,
    TIMESTAMP,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .seller import Seller
    from .stock import Stock


class Product(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"))
    nm_id: Mapped[int | None]
    imt_id: Mapped[int | None]
    nm_uuid: Mapped[str | None]
    subject_id: Mapped[int | None]
    subject_name: Mapped[str | None]
    vendor_code: Mapped[str | None]
    brand: Mapped[str | None]
    title: Mapped[str | None]
    description: Mapped[str | None] = mapped_column(Text)
    video: Mapped[str | None]
    photos: Mapped[dict | None] = mapped_column(JSON)
    length: Mapped[float | None]
    width: Mapped[float | None]
    height: Mapped[float | None]
    characteristics: Mapped[dict | None] = mapped_column(JSON)
    sizes: Mapped[dict | None] = mapped_column(JSON)
    tags: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP)
    updated_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP)

    __table_args__ = (
        UniqueConstraint("seller_id", "nm_id", name="seller_nm_id_key"),
    )

    seller: Mapped["Seller"] = relationship(back_populates="products")
    stocks: Mapped[list["Stock"]] = relationship(back_populates="product")
