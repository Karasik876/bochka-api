from fastapi import APIRouter

router = APIRouter(prefix="/public", tags=["public"])


@router.post("/healthcheck")
async def healthcheck():
    return 1


@router.post("/register")
async def register():
    raise NotImplementedError()


@router.get("/instrument")
async def get_instruments():
    raise NotImplementedError()


@router.get("/orderbook/{ticker}")
async def get_orderbook(ticker: str):
    raise NotImplementedError()


@router.get("/transactions/{ticker}")
async def get_transactions(ticker: str):
    raise NotImplementedError()
