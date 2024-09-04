import inspect
from typing import Any

from loguru import logger


def _extract_property_values(obj):
    prop_names = [
        m[0] for m in inspect.getmembers(obj.__class__) if isinstance(m[1], property)
    ]

    prop_name_to_value = {
        member_name: value
        for member_name, value in inspect.getmembers(obj)
        if member_name in prop_names
    }

    return prop_name_to_value


def copy_field_values(
    *,
    copy_from_object,
    new_object_class,
    fields: list[str],
    additional_values: dict[str, Any] | None = None,
    set_null: bool = False,
):
    if additional_values is None:
        additional_values = {}

    field_values = {}

    for field in fields:
        is_field_found = hasattr(copy_from_object, field)

        if not is_field_found:
            if field not in additional_values:
                logger.warning(
                    f'Field {field!r} not found in entity of class {copy_from_object.__class__.__name__!r}'
                )
            continue

        field_value = getattr(copy_from_object, field)

        if field_value is None and not set_null:
            continue

        field_values[field] = field_value

    persistence_object = new_object_class(**field_values, **additional_values)
    return persistence_object


def convert_entity_to_persistence_object(*, entity, sqla_class, **kwargs):
    fields = sqla_class.get_field_names()

    return copy_field_values(
        copy_from_object=entity,
        fields=fields,
        new_object_class=sqla_class,
        **kwargs,
    )


def convert_persistence_object_to_entity(*, persistence_object, entity_class, **kwargs):
    fields = ...

    return copy_field_values(
        copy_from_object=persistence_object,
        fields=fields,
        new_object_class=entity_class,
        **kwargs,
    )
