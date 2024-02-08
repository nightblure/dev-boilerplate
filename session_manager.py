from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker, scoped_session

logger = logging.getLogger(__name__)


class DbSessionManager:
    """
    Takes from https://github.com/dmontagu/fastapi-utils/blob/master/fastapi_utils/session.py
    A convenience class for managing a (cached) sqlalchemy ORM engine and sessionmaker.
    Intended for use creating ORM sessions injected into endpoint functions by FastAPI.
    """

    def __init__(self, *, database_uri: str, echo: bool, scoped: bool):
        """
        `database_uri` should be any sqlalchemy-compatible database URI.

        In particular, `sqlalchemy.create_engine(database_uri)` should work to create an engine.

        Typically, this would look like:

            "<scheme>://<user>:<password>@<host>:<port>/<database>"

        A concrete example looks like "postgresql://db_user:password@db:5432/app"
        """
        self.database_uri = database_uri
        self.echo = echo
        self.scoped = scoped

        self._cached_engine: Engine | None = None
        self._cached_sessionmaker: sessionmaker | None = None

    @property
    def cached_engine(self) -> Engine:
        """
        Returns a lazily-cached sqlalchemy engine for the instance's database_uri.
        """
        engine = self._cached_engine
        if engine is None:
            engine = self.get_new_engine(echo=self.echo)
            self._cached_engine = engine
        return engine

    @property
    def cached_sessionmaker(self) -> sessionmaker:
        """
        Returns a lazily-cached sqlalchemy sessionmaker using the instance's (lazily-cached) engine.
        """
        maker = self._cached_sessionmaker
        if maker is None:
            maker = self.get_new_sessionmaker(self.cached_engine, scoped=self.scoped)
            self._cached_sessionmaker = maker
        return maker

    def get_session(self) -> Session:
        """For direct use. Dont forget close the session!"""
        return self.cached_sessionmaker()

    def get_new_engine(self, *, echo=False) -> Engine:
        """
        Returns a new sqlalchemy engine using the instance's database_uri.
        """
        return get_engine(self.database_uri, echo=echo)

    def get_new_sessionmaker(self, engine: Engine | None, *, scoped) -> sessionmaker:
        """
        Returns a new sessionmaker for the provided sqlalchemy engine. If no engine is provided, the
        instance's (lazily-cached) engine is used.
        """
        engine = engine or self.cached_engine
        return get_sessionmaker_for_engine(engine=engine, scoped=scoped)

    def get_db(self) -> Iterator[Session]:
        """
        A generator function that yields a sqlalchemy orm session and cleans up the session once resumed after yielding.

        Can be used directly as a context-manager FastAPI dependency, or yielded from inside a separate dependency.
        """
        yield from _get_db(self.cached_sessionmaker)

    @contextmanager
    def context_session(self) -> Iterator[Session]:
        """
        A context-manager wrapped version of the `get_db` method.

        This makes it possible to get a context-managed orm session for the relevant database_uri without
        needing to rely on FastAPI's dependency injection.

        Usage looks like:

            session_maker = DbSessionManager(database_uri)
            with session_maker.context_session() as session:
                session.query(...)
                ...
        """
        yield from self.get_db()

    def reset_cache(self) -> None:
        """
        Resets the engine and sessionmaker caches.

        After calling this method, the next time you try to use the cached engine or sessionmaker,
        new ones will be created.
        """
        self._cached_engine = None
        self._cached_sessionmaker = None


def get_engine(uri: str, *, echo=True) -> Engine:
    """
    Returns a sqlalchemy engine with pool_pre_ping enabled.

    This function may be updated over time to reflect recommended engine configuration for use with FastAPI.
    """
    return create_engine(uri, pool_pre_ping=True, echo=echo)


def get_sessionmaker_for_engine(*, engine: Engine, scoped: bool) -> sessionmaker:
    """
    Returns a sqlalchemy sessionmaker for the provided engine with recommended configuration settings.

    This function may be updated over time to reflect recommended sessionmaker configuration for use with FastAPI.
    """
    maker_args = dict(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

    if scoped:
        return scoped_session(sessionmaker(**maker_args))
    else:
        return sessionmaker(**maker_args)


@contextmanager
def context_session(engine: Engine, *, scoped: bool) -> Iterator[Session]:
    """
    This contextmanager yields a managed session for the provided engine.

    Usage is similar to `DbSessionManager.context_session`, except that you have to provide the engine to use.

    A new sessionmaker is created for each call, so the DbSessionManager.context_session
    method may be preferable in performance-sensitive contexts.
    """
    maker = get_sessionmaker_for_engine(engine=engine, scoped=scoped)
    yield from _get_db(maker)


def _get_db(maker: sessionmaker) -> Iterator[Session]:
    """
    A generator function that yields an ORM session using the provided sessionmaker, and cleans it up when resumed.
    """
    session = maker()
    try:
        # print('open session')
        yield session
    except Exception as e:
        session.rollback()
        logger.error(str(e) + '; rollback db session')
        raise e
    finally:
        # print('close session')
        session.close()
