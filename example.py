import sqlalchemy as sa

from db.deps import get_db_session_context, get_db_session, DbSession
from db.typings import SQLADbSession
from db.sqla_mixin import SQLAMixin


class SomeRepository(SQLAMixin):
    def __init__(self, db_session: SQLADbSession):
        self.db_session = db_session

    def get_all(self):
        return self.all()
        

def create_some_repository(db_session=None):
    return SomeRepository(db_session=db_session)


def example1():
    # Session with context manager with auto-closing session and catching errors
    with get_db_session_context() as db_session:
        repo = create_some_repository(db_session)
        repo.get_all()

    # Or get session directly (not recommended)
    db_session = get_db_session()
    repo = create_some_repository(db_session)
    repo.get_all()
    db_session.close()


def example2(db_session: DbSession):
    # Using example with FastAPI depends that call context manager with auto-closing session and catching errors
    repo = create_some_repository(db_session)
    repo.get_all()
    db_session.close()


if __name__ == '__main__':
    example1()
    example2()
