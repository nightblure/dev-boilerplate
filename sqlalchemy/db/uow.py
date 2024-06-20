from dataclasses import dataclass

from sqlalchemy.orm import sessionmaker, Session

from db.types import SQLADbSession
from db.some_dao import SomeDAO


@dataclass(slots=True, kw_only=True)
class UnitOfWork:
    session_factory: sessionmaker
    some_dao: SomeDAO = None
  
    _db_session: SQLADbSession | None = None
    _instance = None

    def _init(self):
        session = self.session_factory()
        self.some_dao = SomeDAO(session)
        # another dao/repository...
        self._db_session = session

    @classmethod
    def create(cls, **kw) -> 'UnitOfWork':
        if cls._instance is None:
            cls._instance = cls(**kw)
        return cls._instance

    @property
    def db_session(self) -> Session:
        if self._db_session is None:
            raise Exception(f'Unit of work should be used ONLY with context manager!')
        return self._db_session

    def commit(self):
        self._db_session.commit()

    def begin_transaction(self):
        self._db_session.begin()

    def __enter__(self):
        self._init()
        # self.begin_transaction()
        return self

    def flush(self, objects: list | None = None):
        self._db_session.flush(objects)

    def rollback(self):
        self._db_session.rollback()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()

        self.close()

    def close(self):
        self._db_session.close()
