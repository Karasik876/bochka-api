from sqlalchemy.exc import OperationalError, SQLAlchemyError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_fixed,
    wait_random,
)


def is_serialization_failure(exception: BaseException) -> bool:
    return isinstance(exception, OperationalError)


def is_unexpected_error(exception: BaseException) -> bool:
    return isinstance(exception, SQLAlchemyError)


def retry_on_serialization():
    return retry(
        reraise=False,
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.5) + wait_random(0.2, 1),
        retry=retry_if_exception(is_unexpected_error),
    )
