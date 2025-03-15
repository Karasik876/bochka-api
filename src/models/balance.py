from datetime import datetime

from sqlalchemy import UUID, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_extensions import uuid7

from src.models.base import Base
from src.models.instrument import Instrument
from src.models.user import User


class Balance(Base):
    __tablename__ = "balances"

    repr_cols = ("user_id", "ticker", "amount")

    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), primary_key=True
    )
    ticker: Mapped[str] = mapped_column(
        String(10), ForeignKey("instruments.ticker"), primary_key=True
    )
    amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="balances")
    instrument: Mapped["Instrument"] = relationship(
        "Instrument", back_populates="operations"
    )


class BalanceOperation(Base):
    __tablename__ = "balance_operations"
    repr_cols = ("id", "user_id", "ticker")

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )
    ticker: Mapped[str] = mapped_column(
        String(10), ForeignKey("instruments.ticker"), nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_type: Mapped[str] = mapped_column(
        Enum("DEPOSIT", "WITHDRAW"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="operations")
    instrument: Mapped["Instrument"] = relationship(
        "Instrument", back_populates="operations"
    )
