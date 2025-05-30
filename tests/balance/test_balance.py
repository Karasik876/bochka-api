import pytest
from httpx import AsyncClient

from src.app import models

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_one_balance(
    admin_client: AsyncClient, instrument: models.Instrument, balance: models.Balance
):
    response = await admin_client.get("/balance")

    json_response = response.json()
    assert "detail" not in json_response
    assert len(json_response) == 1
    assert json_response.get(instrument.ticker) == balance.amount


async def test_no_balances(user_client: AsyncClient):
    response = await user_client.get("/balance")

    assert response.json() == {}
