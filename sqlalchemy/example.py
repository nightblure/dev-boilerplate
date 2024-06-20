from db.some_dao import SomeDAO
from db.uow import UnitOfWork

from sqlalchemy.orm import sessionmaker


def create_uow():
    db_url = 'sqlite:///sqlite.db'
    
    engine = create_engine(
        db_url,
        echo=True
    )
    maker_args = dict(
        autocommit=False,
        autoflush=False,
        bind=engine
    )
    
    session_factory = sessionmaker(**maker_args)
    uow = UnitOfWork.create(
        session_factory=session_factory
    )
    return uow


def main(uow=None):
    if uow is None:
        uow = create_uow()
        
    with uow:
        objects = uow.some_dao.get_all()
    
    print(objects)


if __name__ == '__main__':
    main()
