from asyncio import iscoroutinefunction
from typing import ContextManager

from db.settings import DbSettings
from db.session_manager import DbSessionManager
from db.typings import SQLADbSession

from fastapi import Depends, Request


settings = DbSettings()


def create_db_session_manager() -> DbSessionManager:
    if DbSessionManager.instance is None:
        db_session_manager_kwargs = dict(
            pool_size=20,
            max_overflow=0,
            pool_pre_ping=True,
            echo=settings.is_need_log_sql,
            scoped=False,
            db_url=settings.db_url
        )

        DbSessionManager.instance = DbSessionManager(**db_session_manager_kwargs)

    return DbSessionManager.instance


def get_db_session(*, from_cache: bool = True) -> SQLADbSession:
    return create_db_session_manager().get_db_session(from_cache=from_cache)


def get_db_session_context(*, from_cache: bool = True) -> ContextManager[SQLADbSession]:
    return create_db_session_manager().get_db_session_context(from_cache=from_cache)


def inject_db_session():
    """Inject session into decorated function. Name for the session arg must be 'db_session'"""

    def wrapper(f):

        if iscoroutinefunction(f):
            async def inner(*a, **kw):
                with get_db_session_context() as db_session:
                    kw['db_session'] = db_session
                    result = await f(*a, **kw)

                return result

            return inner
        else:
            def inner(*a, **kw):
                with get_db_session_context() as db_session:
                    kw['db_session'] = db_session
                    result = f(*a, **kw)

                return result

            return inner

    return wrapper


def get_db(request: Request):
    return request.state.db


DbSession = Annotated[SQLADbSession, Depends(get_db)]
