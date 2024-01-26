import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .product import Product
    from .seller import Seller


class Stock(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    last_change_date: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP
    )
    warehouse_name: Mapped[str | None]
    supplier_article: Mapped[str | None]
    barcode: Mapped[str | None]
    quantity: Mapped[int | None]
    in_way_to_client: Mapped[int | None]
    in_way_from_client: Mapped[int | None]
    quantity_full: Mapped[int | None]
    category: Mapped[str | None]
    subject: Mapped[str | None]
    brand: Mapped[str | None]
    tech_size: Mapped[str | None]
    price: Mapped[float | None]
    discount: Mapped[float | None]
    is_supply: Mapped[bool | None]
    is_realization: Mapped[bool | None]
    sc_code: Mapped[str | None]

    __table_args__ = (
        UniqueConstraint(
            "seller_id",
            "last_change_date",
            "warehouse_name",
            "product_id",
            name="seller_product_warehouse_change_date_key",
        ),
    )

    seller: Mapped["Seller"] = relationship(back_populates="stocks")
    product: Mapped["Product"] = relationship(back_populates="stocks")
