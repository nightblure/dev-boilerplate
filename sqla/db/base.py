from sqlalchemy.orm import declarative_base, InstrumentedAttribute

Base = declarative_base()


class SQLABase(Base):
    __abstract__ = True

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

    def to_dict(self, *, exclude_none: bool = False, with_relations: bool = False):
        data: dict = self.__dict__

        if '_sa_instance_state' in data:
            data.pop('_sa_instance_state')

        for field in self.get_field_names():
            if field not in data:
                data[field] = None

        if exclude_none:
            data = {k: v for k, v in data.items() if v is not None}

        if not with_relations:
            return data

        for field, value in data.items():
            if isinstance(value, SQLABase):
                data[field] = value.to_dict(
                    exclude_none=exclude_none, with_relations=with_relations
                )

            if isinstance(value, list) and isinstance(value[0], SQLABase):
                data[field] = [
                    v.to_dict(exclude_none=exclude_none, with_relations=with_relations)
                    for v in value
                ]

        return data
