import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid_v7.base import uuid7

from src.app import models
from src.app.models import BalanceOperation, Instrument, User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_withdraw_success(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
    instrument: Instrument,
):
    initial_amount = 1000
    balance = models.Balance(
        user_id=admin_user.id, ticker=instrument.ticker, amount=initial_amount
    )
    db_session.add(balance)
    await db_session.flush()

    withdraw_amount = 500
    withdraw_data = {
        "user_id": str(admin_user.id),
        "ticker": instrument.ticker,
        "amount": withdraw_amount,
    }

    response = await admin_client.post("/admin/balance/withdraw", json=withdraw_data)

    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["success"]

    await db_session.refresh(balance)
    assert balance.amount == initial_amount - withdraw_amount

    operation = await db_session.scalar(
        select(BalanceOperation).where(
            BalanceOperation.user_id == admin_user.id,
            BalanceOperation.ticker == instrument.ticker,
            BalanceOperation.amount == withdraw_amount,
        )
    )
    assert operation is not None
    assert operation.operation_type == "WITHDRAW"


async def test_withdraw_failed_not_enough_funds(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
    instrument: Instrument,
):
    initial_amount = 100
    balance = models.Balance(
        user_id=admin_user.id, ticker=instrument.ticker, amount=initial_amount
    )
    db_session.add(balance)
    await db_session.flush()

    withdraw_amount = 500
    withdraw_data = {
        "user_id": str(admin_user.id),
        "ticker": instrument.ticker,
        "amount": withdraw_amount,
    }

    response = await admin_client.post("/admin/balance/withdraw", json=withdraw_data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json().get("error_code") == "not_enough_funds"


async def test_withdraw_failed_no_balance(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
    instrument: Instrument,
):
    withdraw_data = {
        "user_id": str(admin_user.id),
        "ticker": instrument.ticker,
        "amount": 100,
    }

    response = await admin_client.post("/admin/balance/withdraw", json=withdraw_data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json().get("error_code") == "not_enough_funds"


async def test_withdraw_failed_user_not_found(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    instrument: Instrument,
):
    withdraw_data = {
        "user_id": str(uuid7()),
        "ticker": instrument.ticker,
        "amount": 100,
    }

    response = await admin_client.post("/admin/balance/withdraw", json=withdraw_data)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("error_code") == "resource_not_found"


async def test_withdraw_failed_instrument_not_found(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
):
    withdraw_data = {
        "user_id": str(admin_user.id),
        "ticker": "NONEXIST",
        "amount": 100,
    }

    response = await admin_client.post("/admin/balance/withdraw", json=withdraw_data)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("error_code") == "resource_not_found"


async def test_withdraw_failed_negative_amount(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
    instrument: Instrument,
):
    withdraw_data = {
        "user_id": str(admin_user.id),
        "ticker": instrument.ticker,
        "amount": -100,  # Отрицательная сумма
    }

    response = await admin_client.post("/admin/balance/withdraw", json=withdraw_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_withdraw_failed_zero_amount(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
    instrument: Instrument,
):
    withdraw_data = {
        "user_id": str(admin_user.id),
        "ticker": instrument.ticker,
        "amount": 0,
    }

    response = await admin_client.post("/admin/balance/withdraw", json=withdraw_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_withdraw_failed_invalid_user_id_type(
    admin_client: AsyncClient,
    instrument: Instrument,
):
    withdraw_data = {
        "user_id": 12345,
        "ticker": instrument.ticker,
        "amount": 100,
    }

    response = await admin_client.post("/admin/balance/withdraw", json=withdraw_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_withdraw_failed_invalid_user_id_format(
    admin_client: AsyncClient,
    instrument: Instrument,
):
    withdraw_data = {
        "user_id": "not-a-uuid",
        "ticker": instrument.ticker,
        "amount": 100,
    }

    response = await admin_client.post("/admin/balance/withdraw", json=withdraw_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_withdraw_failed_invalid_amount_type_string(
    admin_client: AsyncClient,
    admin_user: User,
    instrument: Instrument,
):
    withdraw_data = {
        "user_id": str(admin_user.id),
        "ticker": instrument.ticker,
        "amount": "ABC",
    }

    response = await admin_client.post("/admin/balance/withdraw", json=withdraw_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_withdraw_failed_invalid_amount_type_float(
    admin_client: AsyncClient,
    admin_user: User,
    instrument: Instrument,
):
    withdraw_data = {
        "user_id": str(admin_user.id),
        "ticker": instrument.ticker,
        "amount": 100.50,
    }

    response = await admin_client.post("/admin/balance/withdraw", json=withdraw_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_withdraw_failed_missing_user_id(
    admin_client: AsyncClient,
    instrument: Instrument,
):
    withdraw_data = {
        "ticker": instrument.ticker,
        "amount": 100,
    }

    response = await admin_client.post("/admin/balance/withdraw", json=withdraw_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_withdraw_failed_missing_ticker(
    admin_client: AsyncClient,
    admin_user: User,
):
    withdraw_data = {
        "user_id": str(admin_user.id),
        "amount": 100,
    }

    response = await admin_client.post("/admin/balance/withdraw", json=withdraw_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_withdraw_failed_missing_amount(
    admin_client: AsyncClient,
    admin_user: User,
    instrument: Instrument,
):
    withdraw_data = {
        "user_id": str(admin_user.id),
        "ticker": instrument.ticker,
    }

    response = await admin_client.post("/admin/balance/withdraw", json=withdraw_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
