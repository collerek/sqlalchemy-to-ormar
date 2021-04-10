# sqlalchemy-to-ormar

A simple auto-translator from `sqlalchemy` ORM models to `ormar` models.

The `ormar` package is an async mini ORM for Python, with support for **Postgres,
MySQL**, and **SQLite**.

To learn more about ormar:

* ormar [github][github]
* ormar [documentation][documentation]

## Quickstart

```python
from databases import Database
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    create_engine,
    DECIMAL,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker

Base = declarative_base()
Database_URL = "sqlite:///test.db"
engine = create_engine(Database_URL, echo=True)


# given sqlalchemy models you already have
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    fullname = Column(String)
    nickname = Column(String)
    salary = Column(DECIMAL)

    addresses = relationship(
        "Address", back_populates="user", cascade="all, delete, delete-orphan"
    )


class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True)
    email_address = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="addresses")


# instantiate new Databases instance
database = Database(Database_URL)
# note that you need new metadata instance as table names in ormar
# will remain the same and you cannot have two tables with same name in
# one metadata, note that we bind it to the same engine! 
# (or you can create new one with same url) 
metadata = MetaData(engine)

# use sqlalchemy-to-ormar (not normally imports should be at the top)
from sqlalchemy_to_ormar import ormar_model_str_repr, sqlalchemy_to_ormar

# convert sqlalchemy models to ormar
OrmarAddress = sqlalchemy_to_ormar(Address, database=database, metadata=metadata)
OrmarUser = sqlalchemy_to_ormar(User, database=database, metadata=metadata)

# you can print the ormar model
# or save it to file and you have proper model definition created for you

address_str = ormar_model_str_repr(OrmarAddress)

# now you can print it or save to file
print(address_str)
# will print:

# class OrmarAddress(ormar.Model):
# 
#     class Meta(ormar.ModelMeta):
#         metadata=metadata
#         database=database
#         tablename="addresses"
# 
#     id = ormar.Integer(autoincrement=True, primary_key=True)
#     email_address = ormar.String(max_length=255, nullable=False)
#     user = ormar.ForeignKey(to=OrmarUser, related_name="addresses", name=user_id, nullable=True)

# if you want to skip column aliases if they match field names use skip_names_if_match flag
user_model_str = ormar_model_str_repr(OrmarUser, skip_names_if_match=True)

# let's insert some sample data with sync sqlalchemy

Base.metadata.create_all(engine)
LocalSession = sessionmaker(bind=engine)
db: Session = LocalSession()

ed_user = User(name="ed", fullname="Ed Jones", nickname="edsnickname")
address = Address(email_address="ed@example.com")
address2 = Address(email_address="eddy@example.com")
ed_user.addresses = [address, address2]

db.add(ed_user)
db.commit()

# and now we can query it asynchronously with ormar
async def test_ormar_queries(): 
    user = await OrmarUser.objects.select_related("addresses").get(name='ed')
    assert len(user.addresses) == 2
    assert user.nickname == 'edsnickname'
    assert user.fullname == 'Ed Jones'
    
    addresses = await OrmarAddress.objects.select_related('user').all(user__name='ed')
    assert len(addresses) == 2
    assert addresses[0].user.nickname == 'edsnickname'
    assert addresses[1].user.nickname == 'edsnickname'

# run async
import asyncio
asyncio.run(test_ormar_queries())

# drop db
Base.metadata.drop_all(engine)
```

## Automap support

TBD -> translated from models auto-mapped by sqlalchemy

## Supported fields

`sqlalchemy-to-ormar` supports following sqlalchemy field types:

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
although like `ormar` itself it will create relation field on one side of the relation only
and other side will be auto-populated with reversed side.

## Known limitations

sqlalchemy to ormar right now does not support:

* composite (multi-column) primary keys and foreign keys (as ormar does not support them
  yet)
* `cascade` options from `relationship` are ignored, only the ones declared in sqlalchemy ForeignKey (ondelete, onupdate) are extracted
* ManyToMany fields names customization (as ormar does not support them yet)
* ManyToMany association table has to have primary key
* Model inheritance

[documentation]: https://collerek.github.io/ormar/
[github]: https://github.com/collerek/ormar