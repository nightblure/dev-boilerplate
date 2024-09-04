from enum import Enum

from sqlalchemy import and_, func


class FilterModifier(str, Enum):
    fuzzy_searching = 'fuzzy_searching'
    simple_filtering = 'simple_filtering'
    lower_case_filtering = 'lower_case_filtering'


def _get_simple_filters(sqla_field, filter_value) -> list:
    is_primitive = not isinstance(filter_value, list)

    if is_primitive:
        filters = [sqla_field == filter_value]
    else:
        filters = [sqla_field.in_(filter_value)]

    return filters


def _get_lower_case_filters(sqla_field, filter_value) -> list:
    if isinstance(filter_value, str):
        filter_value = filter_value.lower()
    elif (
        isinstance(filter_value, (list, tuple, set))
        and len(filter_value) > 0
        and isinstance(filter_value[0], str)
    ):
        filter_value = [item.lower() for item in filter_value]

    return _get_simple_filters(sqla_field, filter_value)


def _get_fuzzy_search_filters(sqla_field, filter_value: str) -> list:
    q = filter_value.strip().lower()
    q_parts = q.split()
    q_parts = [f'%{part}%' for part in q_parts]
    filters = []

    word_filters = [func.lower(sqla_field).like(part) for part in q_parts]
    filters_ = [and_(*word_filters), sqla_field.is_not(None)]
    filters.append(and_(*filters_))

    return filters


def _apply_filter_modifier(
    *,
    sqla_fields: list,
    filter_value,
    modifier: FilterModifier,
) -> list:
    filter_modifier_to_modifier_func = {
        FilterModifier.simple_filtering: _get_simple_filters,
        FilterModifier.fuzzy_searching: _get_fuzzy_search_filters,
        FilterModifier.lower_case_filtering: _get_lower_case_filters,
    }
    modifier_func = filter_modifier_to_modifier_func[modifier]

    filters = []

    for sqla_field in sqla_fields:
        filters.extend(modifier_func(sqla_field, filter_value))

    return filters
