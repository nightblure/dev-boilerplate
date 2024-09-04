from typing import Generic, TypeVar

from .mapper_utils import (
    convert_entity_to_persistence_object,
    convert_persistence_object_to_entity,
)

P = TypeVar('P')
E = TypeVar('E')


class BaseMapper(Generic[P, E]):
    @classmethod
    def to_persistence(cls, *, entity, sqla_class, **kwargs) -> P:
        return convert_entity_to_persistence_object(
            entity=entity, sqla_class=sqla_class, **kwargs
        )

    @classmethod
    def to_entity(cls, *, persistence_object, entity_class, **kwargs) -> E:
        return convert_persistence_object_to_entity(
            persistence_object=persistence_object, entity_class=entity_class, **kwargs
        )
