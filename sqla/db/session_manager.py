from collections.abc import Iterator
from contextlib import contextmanager

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker


class DbSessionManager:
    _instance = None
    _engine = None
    _session_maker = None

    @classmethod
    def create(cls, **kw) -> 'DbSessionManager':
        if cls._instance is None:
            cls._instance = cls(**kw)
        return cls._instance

    def __init__(
        self,
        *,
        db_url: str,
        echo: bool = False,
        scoped: bool = False,
        pool_size: int = 20,
        max_overflow: int = 0,
        pool_pre_ping: bool = False,
    ):
        self.db_url = db_url
        self.echo = echo
        self.scoped = scoped
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_pre_ping = pool_pre_ping

        self.engine = create_engine(
            self.db_url,
            echo=self.echo,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_pre_ping=self.pool_pre_ping,
        )
        maker_args = {'autocommit': False, 'autoflush': False, 'bind': self.engine}

        self.session_factory: sessionmaker | Session = sessionmaker(**maker_args)

        if self.scoped:
            self.session_factory = scoped_session(self.session_factory)

    def get_db_session(self) -> Session:
        db_session = self.session_factory()
        return db_session

    @contextmanager
    def get_db_session_context(self) -> Iterator[Session]:
        db_session = self.get_db_session()
        try:
            # logger.warning('open session')
            yield db_session
        except Exception as e:
            db_session.rollback()
            logger.warning('rollback db session')
            raise
        finally:
            # logger.warning('close session')
            db_session.close()
