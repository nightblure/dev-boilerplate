import sqlalchemy as sa
from db.deps import get_db_session_context, get_db_session
from db.typings import SQLADbSession


class SomeRepository:
    def __init__(self, db_session: SQLADbSession):
        self.db_session = db_session

    def get_all(self):
        return self.db_session.query(...).all()
        

def create_some_repository(db_session=None):
    return SomeRepository(db_session=db_session)


def main():
    # Session with context manager with auto-closing session and catching errors
    with get_db_session_context() as db_session:
        repo = create_some_repository(db_session)
        repo.get_all()

    # Or get session directly (not recommended)
    db_session = get_db_session()
    repo = create_some_repository(db_session)
    repo.get_all()
    db_session.close()
    

if __name__ == '__main__':
    main()
