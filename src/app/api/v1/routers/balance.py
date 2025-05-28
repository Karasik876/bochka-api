from fastapi import APIRouter

from src.app import schemas
from src.app.api import dependencies

router = APIRouter(prefix="/balance", tags=["balance"])


@router.get(
    "",
    response_model=schemas.balance.Response,
)
async def get_balance(
    uow: dependencies.uow.Postgres,
    current_user: dependencies.permissions.CurrentUser,
    service: dependencies.services.Balances,
):
    return await service.get_user_balances(uow, current_user.id)
