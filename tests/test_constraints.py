import pytest
from databases import Database
from sqlalchemy import (
    Column,
    DECIMAL,
    ForeignKey,
    Integer,
    MetaData,
    String,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from sqlalchemy_to_ormar import ormar_model_str_repr, sqlalchemy_to_ormar

Base = declarative_base()
Database_URL = "sqlite:///test.db"
engine = create_engine(Database_URL)

database = Database(Database_URL)
metadata = MetaData(engine)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("name", "fullname", name="_uc_name_fullname"),)

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
    user_id = Column(
        Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE")
    )

    user = relationship("User", back_populates="addresses")


def test_constraints():
    OrmarAddress = sqlalchemy_to_ormar(Address, database=database, metadata=metadata)
    OrmarUser = sqlalchemy_to_ormar(User, database=database, metadata=metadata)

    assert OrmarAddress.Meta.model_fields["user"].ondelete == "CASCADE"
    assert OrmarAddress.Meta.model_fields["user"].onupdate == "CASCADE"
    assert OrmarAddress.Meta.model_fields["user"].db_alias == "user_id"

    assert len(OrmarUser.Meta.constraints) == 1
    assert "fullname" in OrmarUser.Meta.constraints[0]._pending_colargs
    assert "name" in OrmarUser.Meta.constraints[0]._pending_colargs


def test_str_repr():
    OrmarAddress = sqlalchemy_to_ormar(Address, database=database, metadata=metadata)
    OrmarUser = sqlalchemy_to_ormar(User, database=database, metadata=metadata)

    address_str = ormar_model_str_repr(OrmarAddress)
    user_str = ormar_model_str_repr(OrmarUser, skip_names_if_match=True)

    assert (
        'user = ormar.ForeignKey(to=User, related_name="addresses", '
        'onupdate="CASCADE", ondelete="CASCADE", '
        "name=user_id, nullable=True)" in address_str
    )

    assert 'constraints=[ormar.UniqueColumns("name", "fullname")]' in user_str
