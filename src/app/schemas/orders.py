import enum
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
)

from src import core
from src.app import models

from . import instruments as instrument_schemas

settings = core.config.get_settings()

LimitOrderPrice = Annotated[int, Field(gt=0)]
OrderQuantity = Annotated[int, Field(ge=1)]


class Base(BaseModel):
    direction: models.order.Direction
    qty: OrderQuantity


class Create(Base):
    ticker: instrument_schemas.Ticker
    status: models.order.OrderStatus = models.order.OrderStatus.NEW
    price: LimitOrderPrice | None = None


class LimitOrderBody(Base):
    ticker: instrument_schemas.Ticker
    price: LimitOrderPrice


class MarketOrderBody(Base):
    ticker: instrument_schemas.Ticker


class Read(Base):
    id: UUID
    status: models.order.OrderStatus
    order_type: models.order.OrderType
    user_id: UUID
    created_at: Annotated[datetime, Field(serialization_alias="timestamp")]
    instrument_id: UUID

    locked_money: int

    instrument: Annotated[instrument_schemas.Read, Field(exclude=True)]
    direction: Annotated[models.order.Direction, Field(exclude=True)]
    qty: Annotated[OrderQuantity, Field(exclude=True)]
    price: Annotated[LimitOrderPrice | None, Field(exclude=True)]

    filled: int

    model_config = ConfigDict(from_attributes=True, serialize_by_alias=True)


class ReadResponse(Base):
    id: UUID
    status: models.order.OrderStatus
    user_id: UUID
    created_at: Annotated[datetime, Field(serialization_alias="timestamp")]
    instrument_id: UUID

    instrument: Annotated[instrument_schemas.Read, Field(exclude=True)]
    direction: Annotated[models.order.Direction, Field(exclude=True)]
    qty: Annotated[OrderQuantity, Field(exclude=True)]
    price: Annotated[LimitOrderPrice | None, Field(exclude=True)]

    filled: int

    @computed_field
    @property
    def body(self) -> LimitOrderBody | MarketOrderBody:
        return (
            LimitOrderBody(
                direction=self.direction,
                ticker=self.instrument.ticker,
                qty=self.qty,
                price=self.price,
            )
            if self.price
            else MarketOrderBody(
                direction=self.direction, ticker=self.instrument.ticker, qty=self.qty
            )
        )

    model_config = ConfigDict(from_attributes=True, serialize_by_alias=True)


class Update(BaseModel):
    status: models.order.OrderStatus | None = None
    filled: int | None = None
    locked_money: int | None = None


class SuccessResponse(BaseModel):
    success: bool = True


class CreateSuccess(SuccessResponse):
    order_id: UUID


class Filters(core.schemas.BaseFilters):
    direction: list[models.order.Direction] | models.order.Direction | None = None
    instrument_id: list[UUID] | UUID | None = None
    status: list[models.order.OrderStatus] | models.order.OrderStatus | None = None
    user_id: list[UUID] | UUID | None = None
    price_from: LimitOrderPrice | None = None
    price_to: LimitOrderPrice | None = None


class SortFields(enum.StrEnum):
    DIRECTION = "direction"
    QUANTITY = "qty"
    PRICE = "price"
    STATUS = "status"
    TICKER = "ticker"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class SortParams(core.schemas.SortParams):
    sort_by: SortFields | None = None


class ReadManyParams(Filters, SortParams, core.schemas.PaginationParams):
    pass
