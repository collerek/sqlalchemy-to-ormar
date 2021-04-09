# sqlalchemy-to-ormar

# **WORK IN PROGRESS**

Simple translator from `sqlalchemy` ORM models to `ormar` models.

The `ormar` package is an async mini ORM for Python, with support for **Postgres,
MySQL**, and **SQLite**. 

To learn more about ormar:

*  ormar [github][github]
*  ormar [documentation][documentation]

## Supported fields

`sqlalchemy-to-ormar` supports following sqlachemy field types:

* "integer": `ormar.Integer`,
* "small_integer": `ormar.Integer`,
* "big_integer": `ormar.BigInteger`,
* "string": `ormar.String,`
* "text": `ormar.Text,`
* "float": `ormar.Float,`
* "decimal": `ormar.Decimal,`
* "date": `ormar.Date,`
* "datetime": `ormar.DateTime,`
* "time": `ormar.Time,`
* "boolean": `ormar.Boolean`

## Supported relations

sqlalchemy-to-ormar supports both `ForeignKey` as well as `ManyToMany` relations

## Known limitations

sqlalchemy to ormar right now does not support:

* composite (multi-column) primary keys and foreign keys (as ormar does not support
  them yet)
* ManyToMany fields names customization (as ormar does not support them yet)
* Model inheritance


[documentation]: https://collerek.github.io/ormar/
[github]: https://github.com/collerek/ormar