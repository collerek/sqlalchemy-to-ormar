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
    PARENT_ID = Column(ForeignKey("user.USER_ID"), index=True)
    parent = relationship("User", remote_side=[USER_ID])


def test_self_relation():
    OrmarUser = sqlalchemy_to_ormar(User, database=database, metadata=metadata)
    assert OrmarUser.extract_related_names() == {"parent", "users"}
