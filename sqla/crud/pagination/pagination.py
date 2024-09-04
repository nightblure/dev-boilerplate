import math
from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, model_validator
from pydantic.version import VERSION
from sqlalchemy import UnaryExpression
from sqlalchemy.orm import InstrumentedAttribute, Query

from .params import PaginationParams

T = TypeVar('T')


class PaginationMethod(str, Enum):
    LimitOffset = 'LimitOffset'
    Default = 'Default'


class Page(BaseModel, Generic[T]):
    page: int
    page_size: int
    pages_count: int
    total_count: int
    items_count: int = 0
    items: list[T]

    @model_validator(mode='after')
    def model_validator(self):
        self.items_count = len(self.items)
        return self


class LimitOffsetPage(BaseModel, Generic[T]):
    limit: int
    offset: int
    total_count: int
    items_count: int = 0
    items: list[T]

    @model_validator(mode='after')
    def model_validator(self):
        self.items_count = len(self.items)
        return self


def paginate_by_limit_offset(
    q: Query,
    *,
    limit: int,
    offset: int,
    item_schema: type(BaseModel),
    sqla_order_fields: list[InstrumentedAttribute | UnaryExpression],
) -> LimitOffsetPage:
    """
    q - SQLA base query. For example: db_session.query(User)..join(...).filter(...)...
    """
    total_count = q.count()
    q = q.order_by(*sqla_order_fields)
    db_items = q.limit(limit).offset(offset).all()

    if VERSION.startswith('1.'):
        items = [item_schema.from_orm(item) for item in db_items]
    else:
        items = [item_schema.model_validate(item) for item in db_items]

    return LimitOffsetPage(
        total_count=total_count,
        offset=offset,
        limit=limit,
        items=items,
    )


def paginate(
    q: Query,
    *,
    page: int,
    page_size: int,
    item_schema: type(BaseModel),
    sqla_order_fields: list[InstrumentedAttribute | UnaryExpression],
) -> Page:
    """
    q - SQLA base query. For example: db_session.query(User)..join(...).filter(...)...
    """
    total_count = q.count()
    q = q.order_by(*sqla_order_fields)
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


def paginate_by_method(
    query: Query,
    *,
    method: PaginationMethod,
    pydantic_model_class: type[BaseModel],
    pagination_params: PaginationParams,
    order_fields,
) -> Page[T] | LimitOffsetPage[T]:
    if method == PaginationMethod.LimitOffset:
        page = paginate_by_limit_offset(
            query,
            limit=pagination_params.limit,
            offset=pagination_params.offset,
            sqla_order_fields=order_fields,
            item_schema=pydantic_model_class,
        )
    else:
        page = paginate(
            query,
            page=pagination_params.page,
            sqla_order_fields=order_fields,
            item_schema=pydantic_model_class,
            page_size=pagination_params.page_size,
        )

    return page
