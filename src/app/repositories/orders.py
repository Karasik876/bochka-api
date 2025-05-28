from src import core
from src.app import models


class Orders(core.repositories.sqlalchemy.BaseCRUD[models.Order]):
    def __init__(self):
        super().__init__(models.Order)
