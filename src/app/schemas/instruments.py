import enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from src import core

Ticker = Annotated[str, Field(pattern="^[A-Z]{2,10}$")]


class Base(BaseModel):
    ticker: Ticker
    name: Annotated[str, Field(max_length=255)]


class Create(Base):
    pass


class Update(BaseModel):
    name: Annotated[str, Field(max_length=255)]


class Read(Base):
    model_config = ConfigDict(from_attributes=True)


class Delete(BaseModel):
    success: bool = True


class CreateResponse(BaseModel):
    success: bool = True


class Filters(core.schemas.BaseFilters):
    pass


class SortFields(enum.StrEnum):
    TICKER = "ticker"
    NAME = "name"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class SortParams(core.schemas.SortParams):
    sort_by: SortFields | None = None


class ReadManyParams(Filters, SortParams, core.schemas.PaginationParams):
    pass
