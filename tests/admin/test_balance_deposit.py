import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid_v7.base import uuid7

from src.app import models
from src.app.models import Balance, BalanceOperation, Instrument, User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_deposit_success_new_balance(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
    instrument: Instrument,
):
    amount_test = 1000
    deposit_data = {
        "user_id": str(admin_user.id),
        "ticker": instrument.ticker,
        "amount": amount_test,
    }

    response = await admin_client.post("/admin/balance/deposit", json=deposit_data)

    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["success"]

    # Check balance was created
    balance = await db_session.scalar(
        select(Balance).where(
            Balance.user_id == admin_user.id, Balance.ticker == instrument.ticker
        )
    )
    assert balance is not None
    assert balance.amount == amount_test

    # Check operation was created
    operation = await db_session.scalar(
        select(BalanceOperation).where(
            BalanceOperation.user_id == admin_user.id,
            BalanceOperation.ticker == instrument.ticker,
        )
    )
    assert operation is not None
    assert operation.amount == amount_test
    assert operation.operation_type == "DEPOSIT"


async def test_deposit_success_existing_balance(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
    instrument: Instrument,
):
    balance = models.Balance(user_id=admin_user.id, ticker=instrument.ticker, amount=1)
    db_session.add(balance)
    await db_session.flush()

    initial_amount = balance.amount
    deposit_amount = 500

    deposit_data = {
        "user_id": str(admin_user.id),
        "ticker": instrument.ticker,
        "amount": deposit_amount,
    }

    response = await admin_client.post("/admin/balance/deposit", json=deposit_data)

    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["success"]

    # Check balance was updated
    await db_session.refresh(balance)
    assert balance.amount == initial_amount + deposit_amount

    # Check operation was created
    operation = await db_session.scalar(
        select(BalanceOperation).where(
            BalanceOperation.user_id == admin_user.id,
            BalanceOperation.ticker == instrument.ticker,
            BalanceOperation.amount == deposit_amount,
        )
    )
    assert operation is not None


async def test_deposit_failed_user_not_found(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    instrument: Instrument,
):
    deposit_data = {
        "user_id": str(uuid7()),
        "ticker": instrument.ticker,
        "amount": 1000,
    }

    response = await admin_client.post("/admin/balance/deposit", json=deposit_data)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("error_code") == "resource_not_found"


async def test_deposit_failed_instrument_not_found(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
):
    deposit_data = {"user_id": str(admin_user.id), "ticker": "NONEXIST", "amount": 1000}

    response = await admin_client.post("/admin/balance/deposit", json=deposit_data)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("error_code") == "resource_not_found"


async def test_deposit_failed_negative_amount(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
    instrument: Instrument,
):
    deposit_data = {
        "user_id": str(admin_user.id),
        "ticker": instrument.ticker,
        "amount": -100,  # Negative amount
    }

    response = await admin_client.post("/admin/balance/deposit", json=deposit_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_deposit_failed_zero_amount(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    admin_user: User,
    instrument: Instrument,
):
    deposit_data = {"user_id": str(admin_user.id), "ticker": instrument.ticker, "amount": 0}

    response = await admin_client.post("/admin/balance/deposit", json=deposit_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_deposit_failed_invalid_user_id_type(
    admin_client: AsyncClient,
    instrument: Instrument,
):
    deposit_data = {"user_id": 12345, "ticker": instrument.ticker, "amount": 1000}

    response = await admin_client.post("/admin/balance/deposit", json=deposit_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_deposit_failed_invalid_user_id_format(
    admin_client: AsyncClient,
    instrument: Instrument,
):
    deposit_data = {
        "user_id": "not-a-uuid",  # Невалидный UUID
        "ticker": instrument.ticker,
        "amount": 1000,
    }

    response = await admin_client.post("/admin/balance/deposit", json=deposit_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_deposit_failed_invalid_amount_type_string(
    admin_client: AsyncClient,
    admin_user: User,
    instrument: Instrument,
):
    deposit_data = {
        "user_id": str(admin_user.id),
        "ticker": instrument.ticker,
        "amount": "ABC",  # Строка вместо числа
    }

    response = await admin_client.post("/admin/balance/deposit", json=deposit_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_deposit_failed_invalid_amount_type_float(
    admin_client: AsyncClient,
    admin_user: User,
    instrument: Instrument,
):
    deposit_data = {
        "user_id": str(admin_user.id),
        "ticker": instrument.ticker,
        "amount": 1000.50,  # Float вместо int
    }

    response = await admin_client.post("/admin/balance/deposit", json=deposit_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_deposit_failed_missing_user_id(
    admin_client: AsyncClient,
    instrument: Instrument,
):
    deposit_data = {"ticker": instrument.ticker, "amount": 1000}

    response = await admin_client.post("/admin/balance/deposit", json=deposit_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_deposit_failed_missing_ticker(
    admin_client: AsyncClient,
    admin_user: User,
):
    deposit_data = {"user_id": str(admin_user.id), "amount": 1000}

    response = await admin_client.post("/admin/balance/deposit", json=deposit_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_deposit_failed_missing_amount(
    admin_client: AsyncClient,
    admin_user: User,
    instrument: Instrument,
):
    deposit_data = {"user_id": str(admin_user.id), "ticker": instrument.ticker}

    response = await admin_client.post("/admin/balance/deposit", json=deposit_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
