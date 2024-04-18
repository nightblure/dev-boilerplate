from pydantic.version import VERSION
from pydantic import BaseModel
from sqlalchemy.orm import Query


class PaginatedItems(BaseModel):
    page: int
    page_size: int
    pages_count: int
    total_count: int
    items: list[BaseModel]


def make_pagination(
        q: Query, *, page: int, page_size: int, item_schema: type(BaseModel)
) -> PaginatedItems:
    """
    q - SQLA base query. For example: db_session.query(User)..join(...).filter(...).order_by(User.id.desc())
    """
    total_count = q.count()

    items = []
    pages_count = 0

    if page_size > 0:
        # pages_count = total_count // page_size
        #
        # if total_count % page_size != 0:
        #     pages_count += 1

        pages_count = ((total_count - 1) // page_size) + 1
        offset = (page_size * page) - page_size

        db_items = q.limit(page_size).offset(offset).all()

        if VERSION.startswith('1.'):
            items = [item_schema.from_orm(item) for item in db_items]
        else:
            items = [item_schema.model_validate(item) for item in db_items]

    return PaginatedItems(
        total_count=total_count,
        pages_count=pages_count,
        page=page,
        page_size=page_size,
        items=items
    )
