from typing import Dict, Type

import ormar
from ormar import Model

FIELD_MAP = {
    "integer": ormar.Integer,
    "tinyint": ormar.Integer,
    "smallint": ormar.Integer,
    "bigint": ormar.Integer,
    "small_integer": ormar.Integer,
    "big_integer": ormar.BigInteger,
    "string": ormar.String,
    "char": ormar.String,
    "varchar": ormar.String,
    "text": ormar.Text,
    "mediumtext": ormar.Text,
    "longtext": ormar.Text,
    "float": ormar.Float,
    "decimal": ormar.Decimal,
    "date": ormar.Date,
    "datetime": ormar.DateTime,
    "timestamp": ormar.DateTime,
    "time": ormar.Time,
    "boolean": ormar.Boolean,
    "bit": ormar.Boolean,
}
TYPE_SPECIFIC_PARAMETERS: Dict[str, Dict] = {
    "string": {"max_length": {"key": "length", "default": 255}},
    "varchar": {"max_length": {"key": "length", "default": 255}},
    "char": {"max_length": {"key": "length", "default": 255}},
    "decimal": {
        "max_digits": {"key": "precision", "default": 18},
        "decimal_places": {"key": "scale", "default": 6},
    },
}
COMMON_PARAMETERS: Dict[str, Dict] = dict(
    name={"key": "name", "default": None},
    primary_key={"key": "primary_key", "default": False},
    autoincrement={"key": "autoincrement", "default": False},
    index={"key": "index", "default": False},
    unique={"key": "unique", "default": False},
    nullable={"key": "nullable", "default": None},
    default={"key": "default", "default": None},
    server_default={"key": "server_default", "default": None},
)
PARSED_MODELS: Dict[Type, Type[Model]] = dict()
