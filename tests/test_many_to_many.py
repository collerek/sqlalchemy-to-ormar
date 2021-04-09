from databases import Database
from sqlalchemy import Column, ForeignKey, Integer, Table, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from sqlalchemy_to_ormar import sqlalchemy_to_ormar

Base = declarative_base()
Database_URL = "sqlite://"
engine = create_engine(Database_URL, echo=True)
database = Database(Database_URL)

association_table = Table(
    "association",
    Base.metadata,
    Column("left_id", Integer, ForeignKey("left.id", ondelete="CASCADE")),
    Column("right_id", Integer, ForeignKey("right.id", ondelete="CASCADE")),
)


class Parent(Base):
    __tablename__ = "left"
    id = Column(Integer, primary_key=True)
    children = relationship(
        "Child",
        secondary=association_table,
        back_populates="parents",
        cascade="all, delete",
    )


class Child(Base):
    __tablename__ = "right"
    id = Column(Integer, primary_key=True)
    parents = relationship(
        "Parent",
        secondary=association_table,
        back_populates="children",
        passive_deletes=True,
    )


def test_many_to_many():
    ParentOrmar = sqlalchemy_to_ormar(Parent, database=database)
