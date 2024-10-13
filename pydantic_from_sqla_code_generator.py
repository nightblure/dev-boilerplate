from dataclasses import dataclass
from datetime import datetime

# you need to import here your sqla classes!
# import ... as sqla_classes
from sqlalchemy import Column

class PydanticFieldTemplates:
    default_list_part = 'Field(default_factory=list)'


@dataclass
class PydanticField:
    name: str
    type_: type
    nullable: bool
    default: str | None = None

    def get_string_representation(self, *, old_typing: bool) -> str:
        template: str = '{field_name}: {field_type_hint}'
        field_type_hint = str(self.type_.__name__)

        if self.nullable:
            field_type_hint = f'{field_type_hint} | None'

            if old_typing:
                field_type_hint = f'Optional[{field_type_hint}]'

        representation = template.format(
            field_name=self.name,
            field_type_hint=field_type_hint
        )

        if self.default is not None:
            default_value = self.default

            if self.type_ is str:
                default_value = f"'{default_value}'"

            representation = f'{representation} = {default_value}'

        if self.default is None and self.nullable:
            representation = f'{representation} = None'

        return representation


class CodeGenerator:
    def __init__(
            self, *,
            old_typing: bool | int = False,
            pydantic_version: str = 'v2',
    ):
        self.old_typing = old_typing
        self.pydantic_version = pydantic_version

    def _create_file_lines(self, *, sqla_class: type) -> list[str]:
        additional_import_types = {
            datetime: 'from datetime import datetime'
        }

        lines = []
        pyd_fields = []
        import_lines = []
        ordered_lines = []

        class_name = sqla_class.__name__
        sqla_fields: list[Column] = sqla_class.__table__.columns

        lines.append(f'class {class_name}(BaseModel):\n')

        at_least_one_nullable = False
        types_for_import = set()

        for sqla_field in sqla_fields:
            pydantic_field_name = sqla_field.name
            type_ = sqla_field.type.python_type
            nullable = sqla_field.nullable

            if type_ in additional_import_types:
                types_for_import.add(type_)

            default: str | None = sqla_field.default

            if nullable:
                at_least_one_nullable = True

            if sqla_field.server_default is not None:
                default = sqla_field.server_default.arg.text

            pyd_field = PydanticField(
                default=default,
                nullable=nullable,
                name=pydantic_field_name,
                type_=type_,
            )

            pyd_fields.append(pyd_field)

        for t in types_for_import:
            import_lines.append(additional_import_types[t] + '\n')

        if self.old_typing and at_least_one_nullable:
            import_lines.append('from typing import Optional\n')

        # space between python imports and other
        import_lines.append('\n')

        if self.pydantic_version == 'v2':
            import_lines.append('from pydantic import BaseModel, ConfigDict\n')
        else:
            import_lines.append('from pydantic import BaseModel\n')

        import_lines.append('\n\n')

        if self.pydantic_version == 'v2':
            lines.append('    model_config = ConfigDict(from_attributes=True)\n\n')

        for pyd_field in pyd_fields:
            field_repr = pyd_field.get_string_representation(old_typing=self.old_typing)
            lines.append(f'    {field_repr}')
            lines.append('\n')

        if self.pydantic_version == 'v1':
            lines.append('\n')
            lines.append('    class Config:\n')
            lines.append('        orm_mode = True\n')

        ordered_lines.extend(import_lines)
        ordered_lines.extend(lines)
        return ordered_lines

    def run(
            self,
            *,
            filename: str = 'codegen_result.py',
            # exclude_uselist_false_relations: bool = False,
            sqla_class
    ) -> None:
        lines = self._create_file_lines(sqla_class=sqla_class)
        with open(filename, 'w') as f:
            f.writelines(lines)


def main():
    codegen = CodeGenerator(pydantic_version='v2', old_typing=0)
    codegen.run(sqla_class=sqla_classes.Class)


if __name__ == '__main__':
    main()
