from typing import Container, Dict, Type, cast

import ormar
import sqlalchemy
from databases import Database
from ormar import ForeignKeyField, Model
from pydantic.typing import ForwardRef
from sqlalchemy import MetaData, Table
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Mapper

from sqlalchemy_to_ormar.maps import (
    COMMON_PARAMETERS,
    CURRENTLY_PROCESSED,
    FIELD_MAP,
    PARSED_MODELS,
    TYPE_SPECIFIC_PARAMETERS,
)


def sqlalchemy_to_ormar(
    db_model: Type,
    *,
    metadata: MetaData,
    database: Database,
    exclude: Container[str] = None,
    reverse: bool = False,
) -> Type[Model]:
    if db_model in PARSED_MODELS:
        return PARSED_MODELS[db_model]

    CURRENTLY_PROCESSED.add(db_model)

    exclude = exclude or []
    mapper = inspect(db_model)
    table = mapper.tables[0]
    fields: Dict[str, Dict] = {}
    fields = _extract_db_columns(table=table, exclude=exclude, fields=fields)
    fields = _extract_relations(
        mapper=mapper,
        fields=fields,
        reverse=reverse,
        metadata=metadata,
        database=database,
        db_model=db_model,
    )
    Meta = _build_model_meta(table=table, metadata=metadata, database=database)

    ready_fields = {
        k: v.get("type")(**{z: x for z, x in v.items() if z != "type"})  # type: ignore
        for k, v in fields.items()
    }
    model = type(f"{db_model.__name__}", (ormar.Model,), {"Meta": Meta, **ready_fields})
    model = cast(Type[Model], model)
    print(f"adding model {model}")
    PARSED_MODELS[db_model] = model
    CURRENTLY_PROCESSED.remove(db_model)
    _update_refs_in_related(model)
    return model


def _update_refs_in_related(model: Type[Model]):
    fields_dict = list(model.Meta.model_fields.items())
    for name, field in fields_dict:
        if field.is_relation:
            target = model.Meta.model_fields[name].to
            if target.__class__ != ForwardRef:
                target.update_forward_refs(
                    **{k.__name__: v for k, v in PARSED_MODELS.items()}
                )
            else:
                if target.__forward_arg__ == model.__name__:  # type: ignore
                    model.update_forward_refs(**{model.__name__: model})


def _extract_db_columns(table: Table, exclude: Container[str], fields: Dict) -> Dict:
    for column in table.columns:
        if column.key in exclude or column.foreign_keys:
            continue
        field_definition = dict()
        field_type = column.type.__visit_name__.lower()  # type: ignore
        for param, field_def in COMMON_PARAMETERS.items():
            field_definition[param] = getattr(
                column, field_def.get("key", ""), None
            ) or field_def.get("default")
            field_definition["type"] = FIELD_MAP.get(field_type)
        if field_definition.get("primary_key") and field_type in [
            "integer",
            "small_integer",
            "big_integer",
        ]:
            field_definition["autoincrement"] = True
        else:
            field_definition["autoincrement"] = False
        type_params = TYPE_SPECIFIC_PARAMETERS.get(field_type, None)
        if type_params:
            for param, field_def in type_params.items():
                param_val = getattr(
                    column.type, field_def.get("key", ""), None
                ) or field_def.get("default")
                field_definition[param] = param_val
        fields[column.key] = field_definition
    return fields


def _extract_relations(
    mapper: Mapper,
    fields: Dict,
    reverse: bool,
    metadata: MetaData,
    database: Database,
    db_model: Type,
) -> Dict:
    for attr in mapper.attrs:  # type: ignore
        if isinstance(attr, sqlalchemy.orm.RelationshipProperty):
            # skip one to many, it will be populated later by ormar
            # if attr.direction.name == "ONETOMANY":
            #     continue
            if attr.direction.name == "MANYTOONE":
                # we use forward ref as target might not be populated
                target_sqlalchemy = attr.entity.class_
                if (
                    target_sqlalchemy not in PARSED_MODELS
                    and target_sqlalchemy not in CURRENTLY_PROCESSED
                    and not target_sqlalchemy == db_model
                ):
                    PARSED_MODELS[target_sqlalchemy] = sqlalchemy_to_ormar(
                        target_sqlalchemy, metadata=metadata, database=database
                    )
                    target = PARSED_MODELS[target_sqlalchemy]
                else:
                    target = ForwardRef(target_sqlalchemy.__name__)  # type: ignore

                column = next(iter(attr.local_columns))
                sql_fk = next(iter(column.foreign_keys))
                fields[attr.key] = dict(
                    type=ormar.ForeignKey,
                    to=target,
                    name=column.key,
                    related_name=attr.back_populates,
                    onupdate=getattr(sql_fk, "onupdate", None),
                    ondelete=getattr(sql_fk, "ondelete", None),
                )
            elif attr.direction.name == "MANYTOMANY":
                target_sqlalchemy = attr.entity.class_
                if target_sqlalchemy not in PARSED_MODELS and not reverse:
                    PARSED_MODELS[target_sqlalchemy] = sqlalchemy_to_ormar(
                        target_sqlalchemy,
                        metadata=metadata,
                        database=database,
                        reverse=True,
                    )
                else:  # pragma: no cover
                    # target model already should have m2m relation
                    continue
                target = PARSED_MODELS[target_sqlalchemy]
                through_table_name = attr.secondary.key
                fields[attr.key] = dict(
                    type=ormar.ManyToMany,
                    to=target,
                    through=create_through_model(
                        class_name=through_table_name.title(),
                        table_name=through_table_name,
                        metadata=metadata,
                        database=database,
                    ),
                    related_name=attr.back_populates,
                )
    return fields


def _build_model_meta(
    table: Table, metadata: MetaData, database: Database
) -> Type[ormar.ModelMeta]:
    # constraints
    constraints = []
    for const in table.constraints:
        if isinstance(const, sqlalchemy.UniqueConstraint):
            constraints.append(
                ormar.UniqueColumns(*const._pending_colargs)  # type: ignore
            )

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
    return cast(Type[ormar.ModelMeta], Meta)


def create_through_model(
    class_name: str,
    table_name: str,
    metadata: MetaData,
    database: Database,
) -> Type[Model]:
    """
    Creates default empty through model if no additional fields are required.
    """
    new_meta_namespace = {
        "tablename": table_name,
        "database": database,
        "metadata": metadata,
    }
    new_meta = type("Meta", (), new_meta_namespace)
    through_model = type(class_name, (ormar.Model,), {"Meta": new_meta})
    return cast(Type["Model"], through_model)


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
        constraints = []
        for const in model.Meta.constraints:
            if isinstance(const, ormar.UniqueColumns):
                args = ", ".join(
                    [f'"{x}"' for x in const._pending_colargs]  # type: ignore
                )
                constraints.append(f"ormar.UniqueColumns({args})")

        definition += f"{pad}{pad}constraints=[{', '.join(constraints)}]\n"
    definition += "\n"
    for field in model.Meta.model_fields.values():
        if field.is_relation and field.virtual:
            continue
        field_definition = dict()
        field_type = field.__class__.__name__
        field_name = field.name
        remap_params = {"default": "ormar_default", "name": "db_alias"}
        for param, field_def in COMMON_PARAMETERS.items():
            param_name = remap_params.get(param, param)
            if getattr(field, param_name, None) != field_def.get("default"):
                field_definition[param] = getattr(field, param_name, None)
        if skip_names_if_match and field_definition.get("name") == field_name:
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
            field = cast(ForeignKeyField, field)
            rel_params = (
                f"to={field.to.get_name(lower=False)}, "
                f'related_name="{field.related_name}", '
            )
            if field.onupdate:
                rel_params += f'onupdate="{field.onupdate}", '
            if field.ondelete:
                rel_params += f'ondelete="{field.ondelete}", '
            params_str = rel_params + params_str
        if field_type == "ManyToMany":
            field = cast(ForeignKeyField, field)
            rel_params = (
                f"to={field.to.get_name(lower=False)}, "
                f"through={field.through.get_name(lower=False)}, "
                f'related_name="{field.related_name}", '
            )
            params_str = rel_params + params_str
        definition += f"{pad}{field_name} = ormar.{field_type}({params_str})\n"
    return definition
