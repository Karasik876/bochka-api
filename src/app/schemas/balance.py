import enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, RootModel

from src import core


class Base(BaseModel):
    ticker: Annotated[str, Field(pattern="^[A-Z]{2,10}$")]
    amount: Annotated[int, Field(ge=0)]


class Create(Base):
    pass


class Update(Base):
    pass


class Read(Base):
    model_config = ConfigDict(from_attributes=True)


class Filters(core.schemas.BaseFilters):
    pass


class SortFields(enum.StrEnum):
    TICKER = "ticker"
    AMOUNT = "amount"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class SortParams(core.schemas.SortParams):
    sort_by: SortFields | None = None


class BalanceReadManyParams(Filters, SortParams, core.schemas.PaginationParams):
    pass


Ticker = Annotated[str, Field(pattern="^[A-Z]{2,10}$")]
Amount = Annotated[int, Field(ge=0)]


class Response(RootModel[dict[Ticker, Amount]]):
    root: dict[Ticker, Amount]

    model_config = ConfigDict(
        json_schema_extra={"example": {"MEMCOIN": 0, "DODGE": 100500, "BITCOIN": 42}}
    )
