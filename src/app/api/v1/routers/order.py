from fastapi import APIRouter, Depends, status
from pydantic import UUID4

from src.app import schemas
from src.app.api import dependencies

router = APIRouter(prefix="/order", tags=["order"])


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(dependencies.permissions.get_current_user)],
    response_model=schemas.orders.CreateSuccess,
)
async def create_order(
    order_data: schemas.orders.Create,
    orders_service: dependencies.services.Orders,
    uow: dependencies.uow.Postgres,
):
    order = await orders_service.create(uow, order_data)
    return schemas.orders.CreateSuccess(order_id=order.id)


@router.get("", dependencies=[Depends(dependencies.permissions.get_current_user)])
async def get_orders():
    raise NotImplementedError


@router.get("/{order_id}", dependencies=[Depends(dependencies.permissions.get_current_user)])
async def get_order(order_id: UUID4):
    raise NotImplementedError


@router.delete("/{order_id}", dependencies=[Depends(dependencies.permissions.get_current_user)])
async def delete_order(order_id: UUID4):
    raise NotImplementedError
