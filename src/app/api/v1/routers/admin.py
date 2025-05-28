import random
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import ORJSONResponse

from src import core
from src.app import models, schemas
from src.app.api import dependencies

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/instrument",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(dependencies.permissions.get_admin_user)],
    response_model=schemas.instruments.CreateResponse,
)
async def create_instrument(
    instrument: schemas.instruments.Create,
    instruments_service: dependencies.services.Instruments,
    uow: dependencies.uow.Postgres,
):
    return schemas.instruments.CreateResponse(
        success=bool(await instruments_service.create(uow, instrument))
    )


@router.delete(
    "/instrument/{ticker}",
    dependencies=[Depends(dependencies.permissions.get_admin_user)],
    response_model=schemas.instruments.Delete,
)
async def delete_instrument(
    ticker: str,
    service: dependencies.services.Instruments,
    uow: dependencies.uow.Postgres,
):
    return schemas.instruments.Delete(success=await service.delete_by_id(uow, ticker))


@router.delete(
    "/user/{user_id}",
    dependencies=[Depends(dependencies.permissions.get_admin_user)],
    response_model=schemas.users.Auth,
)
async def delete_user(
    user_id: UUID,
    users_service: dependencies.services.Users,
    uow: dependencies.uow.Postgres,
):
    user = await users_service.read_by_id(uow, user_id)
    await users_service.delete_by_id(uow, user_id)
    return schemas.users.Auth(
        id=user.id,
        name=user.name,
        role=user.role,
        api_key=random.choice(("CrocodiloBombardilo", "BalerinaCappucina", "BobritoBandito")),  # noqa: S311
    )


@router.post("/balance/deposit", dependencies=[Depends(dependencies.permissions.get_current_user)])
async def deposit(
    uow: dependencies.uow.Postgres,
    balance_operation: schemas.balance_operations.Create,
    balance_service: dependencies.services.Balances,
    operation_service: dependencies.services.BalanceOperations,
    user_service: dependencies.services.Users,
    instrument_service: dependencies.services.Instruments,
):
    await user_service.read_by_id(uow, balance_operation.user_id)
    await instrument_service.read_by_id(uow, balance_operation.ticker)

    try:
        balance = await balance_service.read_by_id(
            uow, {"user_id": balance_operation.user_id, "ticker": balance_operation.ticker}
        )

        await balance_service.update_by_id(
            uow,
            {"user_id": balance_operation.user_id, "ticker": balance_operation.ticker},
            schemas.balance.Update(amount=balance.amount + balance_operation.amount),
        )
    except core.services.exceptions.EntityNotFoundError:
        await balance_service.create(
            uow,
            schemas.balance.Create(
                ticker=balance_operation.ticker, amount=balance_operation.amount
            ),
            additional_data={"user_id": balance_operation.user_id},
        )

    await operation_service.create(
        uow,
        balance_operation,
        additional_data={"operation_type": models.balance_operation.OperationType.DEPOSIT},
    )

    return ORJSONResponse(status_code=status.HTTP_200_OK, content={"success": True})


@router.post("/balance/withdraw", dependencies=[Depends(dependencies.permissions.get_admin_user)])
async def withdraw(
    uow: dependencies.uow.Postgres,
    balance_operation: schemas.balance_operations.Create,
    balance_service: dependencies.services.Balances,
    operation_service: dependencies.services.BalanceOperations,
    user_service: dependencies.services.Users,
    instrument_service: dependencies.services.Instruments,
):
    await user_service.read_by_id(uow, balance_operation.user_id)
    await instrument_service.read_by_id(uow, balance_operation.ticker)

    try:
        balance = await balance_service.read_by_id(
            uow, {"user_id": balance_operation.user_id, "ticker": balance_operation.ticker}
        )

        if balance.amount < balance_operation.amount:
            raise dependencies.exceptions.NotEnoughFundsError(balance_operation.user_id)

        await balance_service.update_by_id(
            uow,
            {"user_id": balance_operation.user_id, "ticker": balance_operation.ticker},
            schemas.balance.Update(amount=balance.amount - balance_operation.amount),
        )
    except core.services.exceptions.EntityNotFoundError:
        raise dependencies.exceptions.NotEnoughFundsError(balance_operation.user_id) from None

    await operation_service.create(
        uow,
        balance_operation,
        additional_data={"operation_type": models.balance_operation.OperationType.WITHDRAW},
    )

    return ORJSONResponse(status_code=status.HTTP_200_OK, content={"success": True})
