from dataclasses import dataclass
from typing import Any, Generic, Literal, TypeAlias, TypeVar

from loguru import logger
from sqlalchemy import UnaryExpression, or_
from sqlalchemy.orm import InstrumentedAttribute, Query, Session

from ..db.base import SQLABase

from .filter_modifiers import FilterModifier, _apply_filter_modifier
from .pagination.pagination import (
    LimitOffsetPage,
    Page,
    PaginationMethod,
    paginate_by_method,
)
from .pagination.params import PaginationParams

T = TypeVar('T')

OrderType: TypeAlias = Literal['asc', 'desc']
SQLAField: TypeAlias = InstrumentedAttribute | UnaryExpression


def _resolve_order_field_name(field_name_or_alias: str) -> tuple[str, OrderType]:
    order: OrderType = 'asc'
    field_name = field_name_or_alias

    if field_name_or_alias.startswith('-'):
        order = 'desc'
        field_name = field_name_or_alias[1:]

    return field_name, order


@dataclass(slots=True)
class OrderField:
    name: str
    sqla_field: InstrumentedAttribute | UnaryExpression
    order: OrderType = 'asc'

    def __post_init__(self):
        self.name, self.order = _resolve_order_field_name(self.name)


@dataclass(slots=True)
class FieldMeta:
    name: str
    sqla_field: Any
    filter_modifiers: list[FilterModifier]


@dataclass(slots=True)
class PaginationMeta:
    default_order_fields: list[InstrumentedAttribute | UnaryExpression]
    method: PaginationMethod


@dataclass(slots=True)
class CRUDMeta:
    field_name_to_field_meta: dict[str, FieldMeta]
    pagination_meta: PaginationMeta


def _get_search_value(filters: dict, allow_field_names: list[str]) -> str | None:
    search_value = None

    for frontend_field in allow_field_names:
        search_value = filters.get(frontend_field)

        if search_value is not None:
            break

    return search_value


class CRUDService(Generic[T]):
    model: type[SQLABase]
    pydantic_read_model: T

    pagination = {
        'default_order_fields': [],
        'method': PaginationMethod.Default,
    }

    filter_modifiers: dict[InstrumentedAttribute, list[FilterModifier]] = {}

    search_fields = []
    search_param_frontend_names = ['search', 'query']

    def _build_meta(self) -> dict[str, FieldMeta]:
        field_name_to_field_meta = {}

        for sqla_field in self.filter_modifiers:
            field_name = sqla_field.name

            field_meta = FieldMeta(
                name=field_name,
                sqla_field=sqla_field,
                filter_modifiers=self.filter_modifiers[sqla_field],
            )

            field_name_to_field_meta[field_name] = field_meta

        return field_name_to_field_meta

    def __initialize(self):
        if self.pydantic_read_model is None:
            msg = "Please specify class attribute 'pydantic_read_model'"
            raise Exception(msg)

        meta = CRUDMeta(
            pagination_meta=PaginationMeta(
                default_order_fields=self.pagination['default_order_fields'],
                method=self.pagination['method'],
            ),
            field_name_to_field_meta=self._build_meta(),
        )

        return meta

    def __init__(self, db_session: Session) -> None:
        self.field_name_to_sqla_field = self.model.build_fields_mapping()
        self.meta = self.__initialize()
        self.db_session = db_session

    @property
    def _base_sqla_query(self) -> Query:
        return self.db_session.query(self.model)

    @staticmethod
    def get_clean_field_name(field_name: str) -> str:
        return _resolve_order_field_name(field_name)[0]

    def is_field_exists(self, field_name: str) -> bool:
        return self.model.is_field_exists(self.get_clean_field_name(field_name))

    def get_sqla_field_by_name(self, field_name: str):
        return self.field_name_to_sqla_field[self.get_clean_field_name(field_name)]

    def _get_sqla_filters(self, **filters: Any) -> list:
        sqla_filters = []
        default_modifiers = [FilterModifier.simple_filtering]

        for field_name, filter_value in filters.items():
            search_value = _get_search_value(filters, self.search_param_frontend_names)

            if search_value is not None and len(self.search_fields) > 0:
                filters_ = _apply_filter_modifier(
                    filter_value=search_value,
                    sqla_fields=self.search_fields,
                    modifier=FilterModifier.fuzzy_searching,
                )
                sqla_filters.append(or_(*filters_))
                continue

            if not self.is_field_exists(field_name):
                continue

            filter_modifiers = default_modifiers
            field_meta = self.meta.field_name_to_field_meta.get(field_name)

            if field_meta is not None:
                filter_modifiers = field_meta.filter_modifiers

            if (
                FilterModifier.lower_case_filtering in filter_modifiers
                and FilterModifier.fuzzy_searching in filter_modifiers
            ):
                filter_modifiers.remove(FilterModifier.lower_case_filtering)

            for modifier in filter_modifiers:
                filters_ = _apply_filter_modifier(
                    modifier=modifier,
                    sqla_fields=[self.get_sqla_field_by_name(field_name)],
                    filter_value=filter_value,
                )

                if modifier == FilterModifier.fuzzy_searching:
                    sqla_filters.append(or_(*filters_))
                else:
                    sqla_filters.extend(filters_)

        return sqla_filters

    def modify_query_before_filters_applying(
        self,
        query: Query,
        _: dict[str, Any],
    ) -> Query:
        return query

    def _extract_filters_and_order_fields(self, **filters_and_params):
        # ORDER FIELD START =========================================================================================
        frontend_order_fields: str | list[str] | None = filters_and_params.pop(
            'sort_by',
            None,
        )

        if frontend_order_fields is None:
            frontend_order_fields = filters_and_params.pop('order_by', None)

        default_order_fields = self.pagination['default_order_fields']

        if frontend_order_fields is None:
            order_fields = default_order_fields
        else:
            order_fields = []

        if not isinstance(frontend_order_fields, list):
            frontend_order_fields = [frontend_order_fields]

        if order_fields is not default_order_fields:
            for frontend_field in frontend_order_fields:
                if not self.is_field_exists(frontend_field):
                    logger.warning(
                        f'Field {frontend_field!r} not found for DB entity {self.model.__name__}',
                    )
                    continue

                order_field = OrderField(
                    name=frontend_field,
                    sqla_field=self.get_sqla_field_by_name(frontend_field),
                )
                order_fields.append(order_field.sqla_field)

        # ORDER FIELD END =========================================================================================

        filters = {}

        for field_name, filter_value in filters_and_params.items():
            if not self.is_field_exists(field_name):
                logger.warning(
                    f'Field {field_name!r} not found for DB entity {self.model.__name__}',
                )

            filters[field_name] = filter_value

        return filters, order_fields

    def _build_sqla_query(self, filters: dict[str, Any]) -> Query:
        sqla_filters = self._get_sqla_filters(**filters)
        query = self.modify_query_before_filters_applying(
            self._base_sqla_query,
            filters,
        )
        query = query.filter(*sqla_filters)
        return query

    def get_page(
        self,
        *,
        pagination_params: PaginationParams,
        **filters_and_params,
    ) -> Page[T] | LimitOffsetPage[T]:
        filters, order_fields = self._extract_filters_and_order_fields(
            **filters_and_params,
        )
        query = self._build_sqla_query(filters)
        page = paginate_by_method(
            query,
            order_fields=order_fields,
            method=self.pagination['method'],
            pagination_params=pagination_params,
            pydantic_model_class=self.pydantic_read_model,
        )
        return page
