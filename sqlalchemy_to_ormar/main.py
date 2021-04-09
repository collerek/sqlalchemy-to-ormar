from typing import Container, Type, cast

import ormar
import sqlalchemy
from databases import Database
from pydantic.typing import ForwardRef
from sqlalchemy import MetaData
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.properties import ColumnProperty

FIELD_MAP = {
    "integer": ormar.Integer,
    "small_integer": ormar.Integer,
    "big_integer": ormar.BigInteger,
    "string": ormar.String,
    "text": ormar.Text,
    "float": ormar.Float,
    "decimal": ormar.Decimal,
    "date": ormar.Date,
    "datetime": ormar.DateTime,
    "time": ormar.Time,
    "boolean": ormar.Boolean,
}

TYPE_SPECIFIC_PARAMETERS = {
    "string": {"max_length": {"key": "length", "default": 255}},
    "decimal": {
        "max_digits": {"key": "precision", "default": 18},
        "decimal_places": {"key": "scale", "default": 6},
    },
}

COMMON_PARAMETERS = dict(
    name={"key": "name", "default": None},
    primary_key={"key": "primary_key", "default": False},
    autoincrement={"key": "autoincrement", "default": False},
    index={"key": "index", "default": False},
    unique={"key": "unique", "default": False},
    nullable={"key": "nullable", "default": None},
    default={"key": "default", "default": None},
    server_default={"key": "server_default", "default": None},
)


def sqlalchemy_to_ormar(
    db_model: Type,
    *,
    metadata: MetaData,
    database: Database,
    exclude: Container[str] = None,
) -> Type[ormar.Model]:
    exclude = exclude or []
    mapper = inspect(db_model)
    table = mapper.tables[0]
    fields = {}
    # columns
    for c in table.columns:
        if c.key in exclude or c.foreign_keys:
            continue
        field_definition = dict()
        field_type = c.type.__visit_name__.lower()
        for param, field_def in COMMON_PARAMETERS.items():
            field_definition[param] = getattr(
                c, field_def.get("key"), None
            ) or field_def.get("default")
            if param == "autoincrement" and field_definition[param] == "auto":
                field_definition[param] = True
            field_definition["type"] = FIELD_MAP.get(field_type)
        if field_definition.get("primary_key") and field_type in [
            "integer",
            "small_integer",
            "big_integer",
        ]:
            field_definition["autoincrement"] = True
        type_params = TYPE_SPECIFIC_PARAMETERS.get(field_type, None)
        if type_params:
            for param, field_def in type_params.items():
                param_val = getattr(c, field_def.get("key"), None) or field_def.get(
                    "default"
                )
                field_definition[param] = param_val
        fields[c.key] = field_definition

    # fks
    for attr in mapper.attrs:
        if isinstance(attr, sqlalchemy.orm.RelationshipProperty):
            # skip one to many, it will be populated later by ormar
            if attr.direction.name == "ONETOMANY":
                continue
            elif attr.direction.name == "MANYTOONE":
                # we use forward ref as target might not be populated
                target = ForwardRef(f"Ormar{attr.entity.class_.__name__}")
                column = next(iter(attr.local_columns))
                fields[attr.key] = dict(
                    type=ormar.ForeignKey,
                    to=target,
                    name=column.key,
                    related_name=attr.back_populates,
                    onupdate=getattr(column, "onupdate", None),
                    ondelete=getattr(column, "ondelete", None),
                )
    # constraints
    constraints = []
    for const in table.constraints:
        if isinstance(const, sqlalchemy.UniqueConstraint):
            constraints.append(ormar.UniqueColumns(*const._pending_colargs))

    Meta = type(
        "Meta",
        (ormar.ModelMeta,),
        {
            "metadata": metadata,
            "database": database,
            "tablename": table.key,
            "constraints": constraints,
        },
    )

    ready_fields = {
        k: v.get("type")(**{z: x for z, x in v.items() if z != "type"})
        for k, v in fields.items()
    }
    model = type(
        f"Ormar{db_model.__name__}", (ormar.Model,), {"Meta": Meta, **ready_fields}
    )
    model = cast(Type[ormar.Model], model)
    return model


def ormar_model_str_repr(
    model: Type[ormar.Model], skip_names_if_match: bool = True
) -> str:
    pad = "    "
    definition = (
        f"\n"
        f"class {model.__name__}(ormar.Model):\n"
        f"\n{pad}class Meta(ormar.ModelMeta):\n"
        f"{pad * 2}metadata=metadata\n"
        f"{pad * 2}database=database\n"
        f'{pad * 2}tablename="{model.Meta.tablename}"\n'
    )
    if model.Meta.constraints:
        definition += f"{pad}{pad}constraints={model.Meta.constraints}\n"
    definition += "\n"
    for field in model.Meta.model_fields.values():
        field_definition = dict()
        field_type = field.__class__.__name__
        field_name = field.name
        remap_params = {"default": "ormar_default", "name": "db_alias"}
        for param, field_def in COMMON_PARAMETERS.items():
            param_name = remap_params.get(param, param)
            if getattr(field, param_name, None) != field_def.get("default"):
                field_definition[param] = getattr(field, param_name, None)
        if skip_names_if_match and field_definition["name"] == field_name:
            field_definition.pop("name", None)
        if field_definition.get("primary_key"):
            field_definition.pop("nullable", None)
        type_params = TYPE_SPECIFIC_PARAMETERS.get(field_type.lower(), None)
        if type_params:
            for param in type_params.keys():
                param_val = getattr(field, param, None)
                field_definition[param] = param_val
        params = ["=".join([str(k), str(v)]) for k, v in field_definition.items()]
        params_str = ", ".join(sorted(params))
        if field_type == "ForeignKey":
            rel_params = f'to={field.to}, related_name="{field.related_name}", '
            if field.onupdate:
                rel_params += f'onupdate="{field.onupdate}"'
            if field.ondelete:
                rel_params += f'ondelete="{field.ondelete}"'
            params_str = rel_params + params_str
        definition += f"{pad}{field_name} = ormar.{field_type}({params_str})\n"
    return definition
