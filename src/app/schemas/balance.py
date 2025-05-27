import enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, RootModel

from src import core

from . import instruments as instrument_schemas

BalanceOperationAmount = Annotated[int, Field(gt=0)]


class Base(BaseModel):
    ticker: instrument_schemas.Ticker
    amount: BalanceOperationAmount


class Create(Base):
    pass


class Update(Base):
    pass


class Read(Base):
    model_config = ConfigDict(from_attributes=True)


class Filters(core.schemas.BaseFilters):
    ticker: list[instrument_schemas.Ticker] | instrument_schemas.Ticker | None = None
    amount_from: BalanceOperationAmount
    amount_to: BalanceOperationAmount


class SortFields(enum.StrEnum):
    TICKER = "ticker"
    AMOUNT = "amount"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class SortParams(core.schemas.SortParams):
    sort_by: SortFields | None = None


class BalanceReadManyParams(Filters, SortParams, core.schemas.PaginationParams):
    pass


BalanceAmount = Annotated[int, Field(ge=0)]


class Response(RootModel[dict[instrument_schemas.Ticker, BalanceAmount]]):
    root: dict[instrument_schemas.Ticker, BalanceAmount]

    model_config = ConfigDict(
        json_schema_extra={"example": {"MEMCOIN": 0, "DODGE": 100500, "BITCOIN": 42}}
    )
