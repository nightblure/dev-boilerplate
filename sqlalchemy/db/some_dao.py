from db.typings import SQLADbSession
from db.sqla_mixin import SQLAMixin


class SomeDAO(SQLAMixin):
    model = SomeModel
  
    def __init__(self, db_session: SQLADbSession):
        self.db_session = db_session

    def get_all(self):
        return self.all()
