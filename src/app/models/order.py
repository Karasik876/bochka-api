import enum
from typing import TYPE_CHECKING

from sqlalchemy import UUID, CheckConstraint, ForeignKey
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_v7.base import uuid7

from src import core

if TYPE_CHECKING:
    from src.app.models.instrument import Instrument
    from src.app.models.user import User


class OrderType(enum.StrEnum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderStatus(enum.StrEnum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"


class Direction(enum.StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class Order(core.models.sqlalchemy.Base, core.models.sqlalchemy.SoftDelete):
    __tablename__ = "orders"
    repr_cols = ("id", "user_id", "ticker")

    __table_args__ = (
        CheckConstraint("qty >= 1", name="check_qty_constraint"),
        CheckConstraint("price > 0", name="check_price_positive"),
        CheckConstraint("filled >= 0", name="check_filled_non_negative"),
    )

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        UUID,
        ForeignKey("users.id"),
    )
    status: Mapped[OrderStatus] = mapped_column(
        SQLAlchemyEnum(
            OrderStatus,
            name="orderstatus",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        default=OrderStatus.NEW,
    )
    direction: Mapped[Direction] = mapped_column(
        SQLAlchemyEnum(
            Direction,
            name="orderdirection",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        )
    )

    instrument_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("instruments.id"))

    qty: Mapped[int]
    price: Mapped[int]
    order_type: Mapped[OrderType] = mapped_column(
        SQLAlchemyEnum(
            OrderType,
            name="ordertype",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        )
    )
    filled: Mapped[int] = mapped_column(default=0)

    user: Mapped["User"] = relationship("User", back_populates="orders")
    instrument: Mapped["Instrument"] = relationship("Instrument", back_populates="orders")


class Transaction(core.models.sqlalchemy.Base):
    __tablename__ = "transactions"
    repr_cols = ("id", "ticker", "amount")
    __table_args__ = (
        CheckConstraint("amount > 0", name="check_transaction_amount_positive"),
        CheckConstraint("price >= 0", name="check_price_transaction_non_negative"),
    )

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True)
    instrument_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("instruments.id"))
    amount: Mapped[int]
    price: Mapped[int]

    instrument: Mapped["Instrument"] = relationship("Instrument", back_populates="transactions")
