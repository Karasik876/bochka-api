from sqlalchemy.exc import OperationalError, SQLAlchemyError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


def is_serialization_failure(exception: BaseException) -> bool:
    return isinstance(exception, OperationalError)


def is_unexpected_error(exception: BaseException) -> bool:
    return isinstance(exception, SQLAlchemyError)


def retry_on_serialization():
    return retry(
        reraise=False,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=0.1, min=0.1, max=1),
        retry=retry_if_exception(is_unexpected_error),
    )
