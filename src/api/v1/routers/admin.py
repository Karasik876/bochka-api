from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/instrument")
async def create_instrument():
    raise NotImplementedError()


@router.post("/instrument/{ticker}")
async def delete_instrument(ticker: str):
    raise NotImplementedError()
