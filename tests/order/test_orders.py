from collections.abc import Callable

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app import models, schemas

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_full_execute_one_limit_orders(
    db_session: AsyncSession,
    user_client: AsyncClient,
    instrument: models.Instrument,
    user_rub_balance: models.Balance,
    create_order: Callable,
    admin_user: models.User,
    admin_balance: models.Balance,
):
    start_admin_balance = admin_balance.amount

    sell_order: models.Order = await create_order(
        direction=models.order.Direction.SELL,
        instrument_id=instrument.id,
        user_id=admin_user.id,
        qty=10,
        price=100,
        status=models.order.OrderStatus.NEW,
    )
    user_market_order_create = schemas.orders.CreateRequest(
        direction=models.order.Direction.BUY, ticker=instrument.ticker, qty=sell_order.qty
    )
    response = await user_client.post("/order", json=user_market_order_create.model_dump())

    assert "detail" not in response.json()

    market_buy_orders = (
        await db_session.scalars(
            select(models.Order).filter_by(
                order_type=models.order.OrderType.MARKET, direction=models.order.Direction.BUY
            )
        )
    ).all()
    limit_sell_orders = (
        await db_session.scalars(
            select(models.Order).filter_by(
                order_type=models.order.OrderType.LIMIT, direction=models.order.Direction.SELL
            )
        )
    ).all()

    assert len(market_buy_orders) + len(limit_sell_orders) == 2  # noqa: PLR2004

    market_buy_order, limit_sell_order = market_buy_orders[0], limit_sell_orders[0]

    assert limit_sell_order.status == models.order.OrderStatus.EXECUTED
    assert limit_sell_order.filled == sell_order.qty == limit_sell_order.qty
    assert limit_sell_order.locked_instrument_amount == 0
    assert limit_sell_order.locked_money_amount is None

    assert market_buy_order.status == models.order.OrderStatus.EXECUTED
    assert (
        market_buy_order.locked_instrument_amount
        is market_buy_order.filled
        is market_buy_order.price
        is None
    )

    assert user_rub_balance.amount == 0
    assert admin_balance.amount == start_admin_balance - sell_order.qty
