import pytest
from databases import Database
from sqlalchemy import (
    Column,
    DECIMAL,
    ForeignKey,
    Integer,
    MetaData,
    String,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker

from sqlalchemy_to_ormar import ormar_model_str_repr, sqlalchemy_to_ormar

Base = declarative_base()
Database_URL = "sqlite:///test.db"
engine = create_engine(Database_URL)

database = Database(Database_URL)
metadata = MetaData(engine)


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


@pytest.fixture(autouse=True, scope="module")
def db_and_sample_data_from_sqlalchemy():
    Base.metadata.create_all(engine)
    LocalSession = sessionmaker(bind=engine)
    db: Session = LocalSession()

    ed_user = User(name="ed", fullname="Ed Jones", nickname="edsnickname")
    address = Address(email_address="ed@example.com")
    address2 = Address(email_address="eddy@example.com")
    ed_user.addresses = [address, address2]
    db.add(ed_user)
    db.commit()
    yield
    Base.metadata.drop_all(engine)


def test_string_repr():
    OrmarAddress = sqlalchemy_to_ormar(Address, database=database, metadata=metadata)
    OrmarUser = sqlalchemy_to_ormar(User, database=database, metadata=metadata)
    address_str = ormar_model_str_repr(OrmarAddress)
    assert "class Address(ormar.Model):" in address_str
    assert "    class Meta(ormar.ModelMeta):" in address_str
    assert "        metadata=metadata" in address_str
    assert "        database=database" in address_str
    assert '        tablename="addresses"' in address_str
    assert (
        "    id = ormar.Integer(autoincrement=True, " "primary_key=True)" in address_str
    )
    assert (
        "    email_address = ormar.String(max_length=255, "
        "nullable=False)" in address_str
    )
    assert (
        '    user = ormar.ForeignKey(to=User, related_name="addresses", '
        "name=user_id, nullable=True)" in address_str
    )

    user_str = ormar_model_str_repr(OrmarUser, skip_names_if_match=True)
    assert "class User(ormar.Model):" in user_str
    assert "    class Meta(ormar.ModelMeta):" in user_str
    assert "        metadata=metadata" in user_str
    assert "        database=database" in user_str
    assert '        tablename="users"' in user_str
    assert "    id = ormar.Integer(autoincrement=True, primary_key=True)" in user_str
    assert "    name = ormar.String(max_length=255, nullable=True)" in user_str
    assert "    fullname = ormar.String(max_length=255, nullable=True)" in user_str
    assert "    nickname = ormar.String(max_length=255, nullable=True)" in user_str
    assert (
        "    salary = ormar.Decimal(decimal_places=6, "
        "max_digits=18, nullable=True)" in user_str
    )


def test_schema() -> None:
    OrmarAddress = sqlalchemy_to_ormar(Address, database=database, metadata=metadata)
    OrmarUser = sqlalchemy_to_ormar(User, database=database, metadata=metadata)
    assert OrmarUser.schema().get("properties") == {
        "fullname": {
            "allow_blank": True,
            "curtail_length": None,
            "maxLength": 255,
            "strip_whitespace": False,
            "title": "Fullname",
            "type": "string",
        },
        "id": {"maximum": None, "minimum": None, "title": "Id", "type": "integer"},
        "name": {
            "allow_blank": True,
            "curtail_length": None,
            "maxLength": 255,
            "strip_whitespace": False,
            "title": "Name",
            "type": "string",
        },
        "nickname": {
            "allow_blank": True,
            "curtail_length": None,
            "maxLength": 255,
            "strip_whitespace": False,
            "title": "Nickname",
            "type": "string",
        },
        "salary": {
            "decimal_places": 6,
            "max_digits": 18,
            "maximum": None,
            "minimum": None,
            "precision": 18,
            "scale": 6,
            "title": "Salary",
            "type": "number",
        },
    }

    assert OrmarAddress.schema().get("properties", {}).get("email_address") == {
        "allow_blank": None,
        "curtail_length": None,
        "maxLength": 255,
        "strip_whitespace": False,
        "title": "Email Address",
        "type": "string",
    }

    assert OrmarAddress.schema().get("properties", {}).get("id") == {
        "maximum": None,
        "minimum": None,
        "title": "Id",
        "type": "integer",
    }

    assert (
        OrmarAddress.schema().get("properties", {}).get("user", {}).get("title")
        == "User"
    )
    types = OrmarAddress.schema().get("properties", {}).get("user", {}).get("anyOf")
    assert types[0] == {"type": "integer"}
    assert types[1] == {"$ref": "#/definitions/User"}
    assert "#/definitions/PkOnlyUser" in types[2].get("$ref")


@pytest.mark.asyncio
async def test_db_query():
    OrmarAddress = sqlalchemy_to_ormar(Address, database=database, metadata=metadata)
    OrmarUser = sqlalchemy_to_ormar(User, database=database, metadata=metadata)

    user = await OrmarUser.objects.select_related("addresses").get(name="ed")
    assert len(user.addresses) == 2
    assert user.nickname == "edsnickname"
    assert user.fullname == "Ed Jones"

    addresses = await OrmarAddress.objects.select_related("user").all(user__name="ed")
    assert len(addresses) == 2
    assert addresses[0].user.nickname == "edsnickname"
    assert addresses[1].user.nickname == "edsnickname"
