import datetime
from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


if TYPE_CHECKING:
    from .seller import Seller


class User(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(unique=True)
    first_name: Mapped[str | None]
    last_name: Mapped[str | None]
    added_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP)

    sellers: Mapped[list["Seller"]] = relationship(back_populates="user")
