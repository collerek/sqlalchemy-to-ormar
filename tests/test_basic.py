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
from sqlalchemy.orm import relationship

from sqlalchemy_to_ormar import ormar_model_str_repr, sqlalchemy_to_ormar

Base = declarative_base()
Database_URL = "sqlite://"
engine = create_engine(Database_URL, echo=True)

database = Database(Database_URL)
metadata = MetaData()


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


OrmarAddress = sqlalchemy_to_ormar(Address, database=database, metadata=metadata)
OrmarUser = sqlalchemy_to_ormar(User, database=database, metadata=metadata)


def test_run():
    print(ormar_model_str_repr(OrmarAddress))
    print(ormar_model_str_repr(OrmarUser, skip_names_if_match=True))
