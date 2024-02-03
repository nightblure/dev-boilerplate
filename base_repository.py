import logging
from typing import Any

from sqlalchemy import update, insert, or_, and_
from sqlalchemy.exc import IntegrityError, CompileError
from sqlalchemy.orm import Session, InstrumentedAttribute, Query

logger = logging.getLogger(__name__)


class BaseSqlRepository:
    """
    Fluent interface wrapper above simple SQLAlchemy queries
    Examples:
        objs = repo.select('id').where(name='test').order_by('id', 'desc').all()

        objs = repo.select(id='id_label').where_in(id=[1, 2]).limit(5).all()

        objs = repo.where(id=230423).all()

        Example with multiple joins and filters:

        joins = [
            (Class, self.model.class_id == Class.id, False),
            (Brand, Brand.id == Class.brand_id, True)
        ]

        filters = [
            Brand.name.in_(brand_names),
            self.model.size_name.in_(size_names),
            Class.name.in_(class_names)
        ]

        q = self.select_from(
            self.model, Class, Brand, ProductCategory,
            Subbrand, ProductAttributes, ClassAttributes
        ).apply_joins(*joins).apply_filters(*filters)

        objs = q.all()
    """
    model = None

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.field_name_to_orm_field = self.__build_fields_mapping()
        self.all_field_names = list(self.field_name_to_orm_field.keys())
        self.q = db_session.query(self.model)

    def __build_fields_mapping(self) -> dict[str, InstrumentedAttribute]:
        """Returns map field_name -> sqlalchemy orm field"""
        fields = self.model.__table__.columns

        field_name_to_orm_field = {
            field.name: self.model.__dict__[field.name]
            for field in fields
            # if isinstance(self.model.__dict__[field], InstrumentedAttribute)
        }

        return field_name_to_orm_field

    def _get_field(self, name: str):
        return self.field_name_to_orm_field[name]

    def reset_query(self):
        self.q = self.db_session.query(self.model)

    def order_by(self, field: str, order: str = 'asc'):
        orm_field = self._get_field(field)
        self.q = self.q.order_by(orm_field)

        if order == 'desc':
            self.q = self.q.order_by(orm_field.desc())

        return self

    def where(self, **filter_args):
        self.q = self.q.filter_by(**filter_args)
        return self

    def where_in(self, **filter_args):
        filters = [
            self._get_field(field).in_(value)
            for field, value in filter_args.items()
        ]
        self.q = self.q.filter(*filters)
        return self

    def where_like(self, **filter_args):
        filters = [
            self._get_field(field).like(value)
            for field, value in filter_args.items()
        ]
        self.q = self.q.filter(*filters)
        return self

    def select(self, *fields, **field_to_label):
        """Using examples in class comment"""
        orm_fields = []

        if fields:
            orm_fields = [self._get_field(field) for field in fields]

        if field_to_label:
            orm_fields = [
                self._get_field(field).label(label)
                for field, label in field_to_label.items()
            ]

        if orm_fields:
            self.q = self.db_session.query(*orm_fields)

        return self

    def select_from(self, *tables):
        """Using examples in class"""
        self.q = self.db_session.query(*tables)
        return self

    def apply_joins(self, *joins):
        """Using examples in class"""
        q = self.q

        for join in joins:
            model, on_condition, _ = join
            outer_join = join[2] if len(join) == 3 else False
            q = q.join(model, on_condition, isouter=outer_join)

        self.q = q
        return self

    def apply_filters(self, filters: list, *, condition=None):
        """Condition must be 'and' or 'or' on None"""
        q = self.q.filter(*filters)

        if condition is not None:
            if condition == 'and':
                q = self.q.filter(and_(*filters))

            if condition == 'or':
                q = self.q.filter(or_(*filters))

        self.q = q
        return self

    def limit(self, limit: int):
        self.q = self.q.limit(limit)
        return self

    def all(self):
        result = self.q.all()
        self.reset_query()
        return result

    def orm_object_to_dict(self, orm_obj) -> dict[str, Any]:
        data = {}
        db_obj_dict = orm_obj.__dict__

        for field in self.all_field_names:
            if field not in db_obj_dict:
                data[field] = None
            else:
                data[field] = db_obj_dict[field]

        return data

    def get_query_result_as_list_dicts(self) -> list[dict[str, Any]]:
        db_data = self.all()
        result = []

        for orm_obj in db_data:
            orm_obj_data = self.orm_object_to_dict(orm_obj)
            result.append(orm_obj_data)

        return result

    def where_null(self, field: str):
        orm_field = self._get_field(field)
        self.q = self.q.filter(orm_field.is_(None))
        return self

    def where_not_null(self, field: str):
        orm_field = self._get_field(field)
        self.q = self.q.filter(orm_field.isnot(None))
        return self

    @property
    def query(self) -> Query:
        q = self.q
        self.reset_query()
        return q

    def one_or_none(self, id: Any, id_field_name: str = 'id'):
        id_field = self._get_field(id_field_name)
        return self.q.filter(id_field == id).one_or_none()

    def insert_object_by_mapping(self, data: dict[str, Any], commit=True, flush=False) -> dict[str, Any]:
        try:
            db_obj = self.model(**data)
            self.db_session.add(db_obj)

            if commit:
                self.commit()

            if flush:
                self.flush()

            return self.orm_object_to_dict(db_obj)
        except IntegrityError as e:
            self.db_session.rollback()
            raise e

    def update(self, id: Any, data: dict[str, Any], id_field: str = 'id', commit=True):
        try:
            id_field = self._get_field(id_field)
            q = update(self.model).where(id_field == id).values(**data)
            self.db_session.execute(q)

            if commit:
                self.commit()

        except IntegrityError as e:
            self.db_session.rollback()
            raise e

    def update_by_object(self, db_obj, data: dict[str, Any], commit=True):
        try:
            for field in self.field_name_to_orm_field:
                if field in data:
                    setattr(db_obj, field, data[field])

            if commit:
                self.commit()

        except IntegrityError as e:
            self.db_session.rollback()
            raise e

    def delete(self, id: Any, id_field_name: str = 'id', commit=True, synchronize_session=False):
        db_obj = self.one_or_none(id=id, id_field_name=id_field_name)
        try:
            db_obj.delete(synchronize_session=synchronize_session)
            if commit:
                self.commit()
        except IntegrityError as e:
            self.db_session.rollback()
            raise e

    def commit(self):
        self.db_session.commit()

    def flush(self, objects=None):
        self.db_session.flush(objects)

    def refresh(self, orm_obj):
        self.db_session.refresh(orm_obj)

    def bulk_update_by_mappings(self, mappings: list[dict], commit=True):
        # https://docs.sqlalchemy.org/en/14/core/tutorial.html#inserts-updates-and-deletes
        if len(mappings) == 0:
            return

        self.db_session.bulk_update_mappings(self.model, mappings)

        # example with explicit composite update key
        # from sqlalchemy import bindparam
        #
        # update_key = ['brand_id', 'name']
        # update_key_binds = [
        #     self.field_name_to_orm_field[key] == bindparam(key)
        #     for key in update_key
        # ]
        #
        # fields: list[str] = list(values[0].keys())
        # values_bind_param_map = {field: bindparam(field) for field in fields}
        #
        # q = self.model.__table__.update().where(*update_key_binds).values(**values_bind_param_map)
        # self.db_session.execute(q, values)

        if commit:
            self.commit()

    def bulk_insert_by_mappings(
            self,
            mappings: list[dict[str, Any]],
            commit: bool = True,
            returning_fields: list[str] = None
    ) -> set | None:
        if len(mappings) == 0:
            return
        # https://docs.sqlalchemy.org/en/14/orm/persistence_techniques.html#bulk-operations
        if returning_fields is None:
            returning_fields = ['id']

        orm_returning_fields = [self._get_field(field) for field in returning_fields]
        values = None

        try:
            q = insert(self.model).values(mappings).returning(*orm_returning_fields)
            values = self.db_session.execute(q).fetchall()
        except CompileError as e:
            # some DBAPI not supported returning operator :c
            logger.error(str(e))
            q = insert(self.model).values(mappings)
            self.db_session.execute(q)

        if not commit:
            return None

        if values is not None:
            if len(returning_fields) == 1:
                values = [v[0] for v in values]

            values = set(values)

        return values

    def bulk_insert_objects_by_mappings(self, data: list[dict[str, Any]], commit=True):
        objs = [self.model(**d) for d in data]
        self.db_session.bulk_save_objects(objs)

        if commit:
            self.db_session.commit()

    def get_all_field_unique_values(self, field: str) -> set:
        q = self.db_session.query(self._get_field(field))
        values = self.db_session.scalars(q).all()
        return set(values)

    def get_all_ids(self, id_field: str = 'id') -> set:
        ids = self.get_all_field_unique_values(id_field)
        return ids

    def is_value_exists(self, field: str, value) -> bool:
        orm_field = self._get_field(field)
        return self.db_session.query(orm_field).filter(orm_field == value).exists().scalar()
