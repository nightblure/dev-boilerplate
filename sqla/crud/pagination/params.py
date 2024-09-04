from typing import Annotated

from fastapi import Depends, Request
from pydantic import BaseModel


class PaginationParams(BaseModel):
    page: int
    page_size: int
    limit: int
    offset: int


def get_pagination_params(request: Request) -> PaginationParams:
    query_params = request.query_params
    return PaginationParams(
        page=query_params.get('page', 1),
        limit=query_params.get('limit', 100),
        offset=query_params.get('offset', 0),
        page_size=query_params.get('page_size', 10),
    )


PaginationParams = Annotated[PaginationParams, Depends(get_pagination_params)]
