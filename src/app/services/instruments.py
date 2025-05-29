from src import core
from src.app import models, repositories, schemas


class Instruments(
    core.services.BaseCRUD[
        schemas.instruments.Create,
        schemas.instruments.Read,
        schemas.instruments.Update,
        schemas.instruments.Filters,
        schemas.instruments.SortParams,
        models.Instrument,
    ],
):
    def __init__(self):
        self.repo = repositories.Instruments()
        super().__init__(
            repo=self.repo,
            create_schema=schemas.instruments.Create,
            read_schema=schemas.instruments.Read,
            update_schema=schemas.instruments.Update,
            filters_schema=schemas.instruments.Filters,
        )

    async def get_all_tickers(self, uow: core.UnitOfWork) -> list[str]:
        return list(await self.repo.get_all_tickers(uow))
