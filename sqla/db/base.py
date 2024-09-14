from sqlalchemy.orm import declarative_base, InstrumentedAttribute
from sqlalchemy.orm.collections import InstrumentedList

from .ids import get_uuid4_str

Base = declarative_base()


class SQLABase(Base):
    __abstract__ = True
    _default_id_factory = get_uuid4_str

    def set_id(self, value=None, *, id_field: str = 'id') -> None:
        if getattr(self, id_field) is not None:
            return None

        if value is None:
            value = self.__class__._default_id_factory()

        setattr(self, id_field, value)
        return None

    @classmethod
    def get_fields(cls) -> list:
        return cls.__table__.columns

    @classmethod
    def field_name_to_orm_field(cls) -> dict[str, InstrumentedAttribute]:
        """Returns map field_name -> sqlalchemy orm field"""
        return {field.name: field for field in cls.get_fields()}

    @classmethod
    def get_field_names(cls) -> list[str]:
        return [f.name for f in cls.get_fields()]

    @classmethod
    def get_field(cls, name: str):
        return cls.field_name_to_orm_field()[name]

    def to_dict(self, *, exclude_none: bool = False):
        exclude_keys = ['_sa_instance_state']
        data: dict = {
            k: v
            for k, v in self.__dict__.items()
            if k not in exclude_keys and not isinstance(v, (InstrumentedList, SQLABase))
        }
        fields = self.get_field_names()

        for db_field in fields:
            if db_field not in data:
                data[db_field] = None

        if exclude_none:
            data = {k: v for k, v in data.items() if v is not None}

        return data
