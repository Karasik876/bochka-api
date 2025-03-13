from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.balance import BalanceOperation
from src.models.base import Base
from src.models.order import Order, Transaction


class Instrument(Base):
    __tablename__ = "instruments"
    repr_cols = ("ticker", "name")

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    orders: Mapped[list["Order"]] = relationship(
        "Order", back_populates="instrument"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="instrument"
    )
    operations: Mapped[list["BalanceOperation"]] = relationship(
        "BalanceOperation", back_populates="instrument"
    )
