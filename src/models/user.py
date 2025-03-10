import enum
from src.models.base import Base
from sqlalchemy import String, Enum, UUID
from sqlalchemy.orm import mapped_column, relationship, Mapped

from uuid_extensions import uuid7

from src.models.balance import Balance, BalanceOperation
from src.models.order import Order


class UserRole(enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"
    repr_cols = ("id", "name", "role")

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), nullable=False, default=UserRole.USER
    )
    api_key: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )

    balances: Mapped[list["Balance"]] = relationship(
        "Balance", back_populates="user"
    )
    orders: Mapped[list["Order"]] = relationship(
        "Order", back_populates="user"
    )
    operations: Mapped[list["BalanceOperation"]] = relationship(
        "BalanceOperation", back_populates="user"
    )
