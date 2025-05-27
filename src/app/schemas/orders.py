from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src import core
from src.app import models

from . import instruments as instruments_schemas

settings = core.config.get_settings()


class OrderBase(BaseModel):
    direction: models.order.Direction
    ticker: instruments_schemas.Ticker
    qty: Annotated[int, Field(ge=1)]


class OrderRead(OrderBase):
    id: UUID
    status: models.order.OrderStatus
    user_id: UUID
    created_at: Annotated[datetime, Field(serialization_alias="timestamp")]

    model_config = ConfigDict(from_attributes=True, serialize_by_alias=True)


class LimitOrderBody(OrderBase):
    price: Annotated[int, Field(gt=0)]


class LimitOrderUpdate(BaseModel):
    pass


class LimitOrderRead(OrderRead):
    filled: int = 0
    body: LimitOrderBody


class MarketOrderBody(OrderBase):
    pass


class MarketOrderUpdate(BaseModel):
    pass


class MarketOrderRead(OrderRead):
    body: MarketOrderBody
