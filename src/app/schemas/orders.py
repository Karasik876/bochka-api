import enum
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src import core
from src.app import models

from . import instruments as instrument_schemas

settings = core.config.get_settings()

LimitOrderPrice = Annotated[int, Field(gt=0)]


class Base(BaseModel):
    direction: models.order.Direction
    ticker: instrument_schemas.Ticker
    qty: Annotated[int, Field(ge=1)]


class Read(Base):
    id: UUID
    order_type: models.order.OrderType
    status: models.order.OrderStatus
    user_id: UUID
    created_at: Annotated[datetime, Field(serialization_alias="timestamp")]

    model_config = ConfigDict(from_attributes=True, serialize_by_alias=True)


class Create(Base):
    price: Annotated[int, Field(gt=0)]


class CreateSuccess(BaseModel):
    success: bool = True
    order_id: UUID


class Update(BaseModel):
    price: Annotated[int, Field(gt=0)]
    qty: Annotated[int, Field(ge=1)]


class LimitRead(Base):
    price: LimitOrderPrice


class MarketRead(Base):
    price: LimitOrderPrice


class Filters(core.schemas.BaseFilters):
    direction: list[models.order.Direction] | models.order.Direction | None = None
    ticker: list[instrument_schemas.Ticker] | instrument_schemas.Ticker | None = None
    status: list[models.order.OrderStatus] | models.order.OrderStatus | None = None
    user_id: list[UUID] | UUID | None = None
    price_from: LimitOrderPrice
    price_to: LimitOrderPrice


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
