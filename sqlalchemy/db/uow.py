from dataclasses import dataclass

from sqlalchemy.orm import sessionmaker, Session

from db.types import SQLADbSession
from db.some_dao import SomeDAO
from db.session_manager import DbSessionManager


@dataclass(slots=True, kw_only=True)
class UnitOfWork:
    db_session_manager: DbSessionManager
    some_dao: SomeDAO = None
  
    _db_session: SQLADbSession | None = None
    _instance = None

    def __enter(self):
        session = self.db_session_manager.session_factory()
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
        self.__enter()
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

        if self.db_session_manager.scoped:
            self.db_session_manager.session_factory.remove()

    def close(self):
        self._db_session.close()
