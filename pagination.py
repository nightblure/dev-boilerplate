import math
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel
from pydantic.version import VERSION
from sqlalchemy import Column
from sqlalchemy.orm import Query

T = TypeVar('T')


class Page(BaseModel, Generic[T]):
    page: int
    page_size: int
    pages_count: int
    total_count: int
    items: list[T]


def paginate(
    q: Query,
    *,
    order_field: Column,
    page: int,
    page_size: int,
    item_schema: type(BaseModel),
    order: Literal['asc', 'desc'] = 'desc',
) -> Page:
    """
    q - SQLA base query. For example: db_session.query(User)..join(...).filter(...)...
    """
    total_count = q.count()

    if order == 'asc':
        order_field = order_field.asc()

    if order == 'desc':
        order_field = order_field.desc()

    q = q.order_by(order_field)

    items = []
    pages_count = 0

    if page_size > 0:
        pages_count = math.ceil(total_count / page_size)
        offset = (page_size * page) - page_size

        db_items = q.limit(page_size).offset(offset).all()

        if VERSION.startswith('1.'):
            items = [item_schema.from_orm(item) for item in db_items]
        else:
            items = [item_schema.model_validate(item) for item in db_items]

    return Page(
        total_count=total_count,
        pages_count=pages_count,
        page=page,
        page_size=page_size,
        items=items,
    )
