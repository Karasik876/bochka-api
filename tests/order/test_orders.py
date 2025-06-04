from collections.abc import Callable

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app import models, schemas

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.parametrize(
    ("limit_direction", "market_direction", "expected_status", "qty_diff"),
    [
        (
            models.order.Direction.SELL,
            models.order.Direction.BUY,
            models.order.OrderStatus.EXECUTED,
            0,
        ),
        (
            models.order.Direction.SELL,
            models.order.Direction.BUY,
            models.order.OrderStatus.PARTIALLY_EXECUTED,
            4,
        ),
        (
            models.order.Direction.BUY,
            models.order.Direction.SELL,
            models.order.OrderStatus.EXECUTED,
            0,
        ),
        (
            models.order.Direction.BUY,
            models.order.Direction.SELL,
            models.order.OrderStatus.PARTIALLY_EXECUTED,
            4,
        ),
    ],
    ids=[
        "execute_one_limit_sell_order",
        "partially_execute_one_limit_sell_order",
        "execute_one_limit_buy_order",
        "partially_execute_one_limit_buy_order",
    ],
)
async def test_execute_limit_order_by_market_order(
    db_session: AsyncSession,
    user_client: AsyncClient,
    instrument: models.Instrument,
    admin_user: models.User,
    user_rub_balance: models.Balance,
    user_balance: models.Balance,
    admin_rub_balance: models.Balance,
    admin_balance: models.Balance,
    create_order: Callable,
    limit_direction,
    market_direction,
    expected_status,
    qty_diff,
):
    start_user_balance, start_user_rub_balance, start_admin_balance, start_admin_rub_balance = [
        b.amount for b in [user_balance, user_rub_balance, admin_balance, admin_rub_balance]
    ]

    limit_order_qty = 10
    trade_qty = limit_order_qty - qty_diff

    limit_order: models.Order = await create_order(
        direction=limit_direction,
        instrument_id=instrument.id,
        user_id=admin_user.id,
        qty=limit_order_qty,
        price=100,
        status=models.order.OrderStatus.NEW,
    )

    user_market_order_create = schemas.orders.CreateRequest(
        direction=market_direction,
        ticker=instrument.ticker,
        qty=trade_qty,
    )
    response = await user_client.post("/order", json=user_market_order_create.model_dump())
    assert "detail" not in response.json()

    market_orders = (
        await db_session.scalars(
            select(models.Order).filter_by(
                order_type=models.order.OrderType.MARKET,
                direction=market_direction,
            )
        )
    ).all()
    limit_orders = (
        await db_session.scalars(
            select(models.Order).filter_by(
                order_type=models.order.OrderType.LIMIT,
                direction=limit_direction,
            )
        )
    ).all()

    assert len(market_orders) == len(limit_orders) == 1

    market_order_db, limit_order_db = market_orders[0], limit_orders[0]

    assert limit_order_db.status == expected_status
    assert limit_order_db.filled == trade_qty

    if limit_direction == models.order.Direction.BUY:
        assert limit_order_db.locked_money_amount == (
            limit_order_qty * (limit_order.price or 0)
        ) - (trade_qty * (limit_order.price or 0))
        assert limit_order_db.locked_instrument_amount is None

    if limit_direction == models.order.Direction.SELL:
        assert limit_order_db.locked_instrument_amount == limit_order_qty - trade_qty
        assert limit_order_db.locked_money_amount is None

    assert market_order_db.status == models.order.OrderStatus.EXECUTED
    assert (
        market_order_db.locked_instrument_amount
        is market_order_db.locked_money_amount
        is market_order_db.filled
        is market_order_db.price
        is None
    )

    price = limit_order.price
    if market_direction == models.order.Direction.BUY:
        # Market BUY: user spends RUB, receives instrument; admin receives RUB, loses instrument
        assert user_rub_balance.amount == start_user_rub_balance - trade_qty * price
        assert admin_rub_balance.amount == start_admin_rub_balance + trade_qty * price
        assert user_balance.amount == start_user_balance + trade_qty
        assert admin_balance.amount == start_admin_balance - trade_qty
    else:
        # Market SELL: user receives RUB, loses instrument; admin spends RUB, receives instrument
        assert user_rub_balance.amount == start_user_rub_balance + trade_qty * price
        assert admin_rub_balance.amount == start_admin_rub_balance - trade_qty * price
        assert user_balance.amount == start_user_balance - trade_qty
        assert admin_balance.amount == start_admin_balance + trade_qty
