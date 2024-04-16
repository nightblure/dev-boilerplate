import time
from functools import wraps
from inspect import iscoroutinefunction

from loguru import logger


def log_exec_time():
    def wrapper(f):
        if iscoroutinefunction(f):
            @wraps(f)
            async def inner(*a, **kw):
                start = time.monotonic()
                result = await f(*a, **kw)
                finish = time.monotonic()
                exec_time = round(finish - start, 2)
                logger.info(f'Execution time of "{f.__name__}": {exec_time} seconds')
                return result
        else:
            @wraps(f)
            def inner(*a, **kw):
                start = time.monotonic()
                result = f(*a, **kw)
                finish = time.monotonic()
                exec_time = round(finish - start, 2)
                logger.info(f'Execution time of "{f.__name__}": {exec_time} seconds')
                return result

        return inner

    return wrapper


def log_if_errors(*, reraise=True):
    def wrapper(f):
        @wraps(f)
        async def inner(*a, **kw):
            try:
                if iscoroutinefunction(f):
                    return await f(*a, **kw)
                else:
                    return f(*a, **kw)
            except Exception as e:
                f_name = f.__qualname__

                if reraise:
                    logger.error(f'Error at "{f_name}": {str(e)}')
                    raise e
                else:
                    logger.exception(f'Error at "{f_name}": {str(e)}')

        return inner

    return wrapper
