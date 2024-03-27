from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, scoped_session

from db.typings import SQLADbSession


class DbSessionManager:
    instance = None
    _engine = None
    _session_maker = None

    def __init__(
            self,
            *,
            db_url: str,
            echo: bool = False,
            scoped: bool = False,
            pool_size: int = 20,
            max_overflow: int = 0,
            pool_pre_ping: bool = False
    ):
        self.db_url = db_url
        self.echo = echo
        self.scoped = scoped
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_pre_ping = pool_pre_ping

    def _get_or_create_engine(self, from_cache: bool = True):
        if self._engine is None or not from_cache:
            self._engine = create_engine(
                self.db_url,
                echo=self.echo,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_pre_ping=self.pool_pre_ping
            )
        return self._engine

    def get_engine(self, *, from_cache: bool = True):
        return self._get_or_create_engine(from_cache=from_cache)

    def _get_or_create_sessionmaker(self, engine: Engine):
        maker_args = dict(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
        if self.scoped:
            return scoped_session(sessionmaker(**maker_args))
        else:
            return sessionmaker(**maker_args)

    def get_db_session(self, *, from_cache: bool = True) -> SQLADbSession:
        engine = self.get_engine(from_cache=from_cache)

        if self._session_maker is None or not from_cache:
            self._session_maker = self._get_or_create_sessionmaker(engine)

        db_session = self._session_maker()
        return db_session

    @contextmanager
    def get_db_session_context(self, *, from_cache: bool = True) -> Iterator[SQLADbSession]:
        db_session = self.get_db_session(from_cache=from_cache)
        try:
            # logger.warning('open session')
            yield db_session
        except Exception as e:
            db_session.rollback()
            logger.error(str(e))
            logger.warning('rollback db session')
            raise e
        finally:
            # logger.warning('close session')
            db_session.close()
