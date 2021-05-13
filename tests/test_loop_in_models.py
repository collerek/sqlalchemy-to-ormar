from databases import Database
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from sqlalchemy_to_ormar import sqlalchemy_to_ormar

Base = declarative_base()
Database_URL = "sqlite:///test.db"
engine = create_engine(Database_URL)

database = Database(Database_URL)
metadata = MetaData(engine)


class User(Base):
    __tablename__ = "user"
    USER_ID = Column(Integer(), primary_key=True)
    FIRST_NAME = Column(String(255))
    LAST_NAME = Column(String(255))
    USERNAME = Column(String(255), index=True)
    PASSWORD = Column(String(40))
    EMAIL = Column(String(255))
    CUSTOMER_ID = Column(ForeignKey("customer.CUSTOMER_ID"), index=True)
    user_customer = relationship(
        "Customer", primaryjoin="User.CUSTOMER_ID == Customer.CUSTOMER_ID"
    )


class Customer(Base):
    __tablename__ = "customer"

    CUSTOMER_ID = Column(Integer(), primary_key=True)
    NAME = Column(String(60), index=True)
    ORGNO = Column(String(20))
    TYPE = Column(Integer())
    STATUS = Column(Integer())
    SELLER_ID = Column(ForeignKey("user.USER_ID"), index=True)
    PHONE = Column(String(20))
    FAX = Column(String(20))
    seller = relationship("User", primaryjoin="Customer.SELLER_ID == User.USER_ID")


def test_loops_in_relations():
    OrmarCustomer = sqlalchemy_to_ormar(Customer, database=database, metadata=metadata)
    OrmarUser = sqlalchemy_to_ormar(User, database=database, metadata=metadata)

    assert OrmarCustomer.extract_related_names() == {"seller", "users"}
    assert OrmarUser.extract_related_names() == {"user_customer", "customers"}
