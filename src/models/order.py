import enum

from sqlalchemy import ForeignKey, Enum, String, Integer, DateTime, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from uuid_extensions import uuid7
from src.models.base import Base

from src.models.user import User
from src.models.instrument import Instrument


class OrderType(enum.Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderStatus(enum.Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"


class Direction(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class Order(Base):
    __tablename__ = "orders"
    repr_cols = ("id", "user_id", "ticker")

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.NEW, nullable=False
    )
    direction: Mapped[Direction] = mapped_column(
        Enum(Direction), nullable=False
    )
    ticker: Mapped[str] = mapped_column(
        String(10), ForeignKey("instruments.ticker"), nullable=False
    )
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer)
    order_type: Mapped[OrderType] = mapped_column(
        Enum(OrderType), nullable=False
    )
    filled: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped["User"] = relationship("User", back_populates="orders")
    instrument: Mapped["Instrument"] = relationship(
        "Instrument", back_populates="orders"
    )


class Transaction(Base):
    __tablename__ = "transactions"
    repr_cols = ("id", "ticker", "amount")

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    ticker: Mapped[str] = mapped_column(
        String(10), ForeignKey("instruments.ticker"), nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    instrument: Mapped["Instrument"] = relationship(
        "Instrument", back_populates="transactions"
    )
