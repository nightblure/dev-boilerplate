from typing import TypeVar

from sqlalchemy.orm import Session

SQLADbSession = TypeVar('SQLADbSession', bound=Session)
