import pytest
from databases import Database
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
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

association_table = Table(
    "association",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("parent", Integer, ForeignKey("left.id", ondelete="CASCADE")),
    Column("child", Integer, ForeignKey("right.id", ondelete="CASCADE")),
)


class Parent(Base):
    __tablename__ = "left"
    id = Column(Integer, primary_key=True)
    name = Column(String(length=50), nullable=False)
    children = relationship(
        "Child",
        secondary=association_table,
        back_populates="parents",
        cascade="all, delete",
    )


class Child(Base):
    __tablename__ = "right"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    parents = relationship(
        "Parent",
        secondary=association_table,
        back_populates="children",
        passive_deletes=True,
    )


@pytest.fixture(autouse=True, scope="module")
def create_test_database():
    # use sqlalchemy as ormar one is empty as of now
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def test_string_repr():
    OrmarParent = sqlalchemy_to_ormar(Parent, database=database, metadata=metadata)
    OrmarChild = sqlalchemy_to_ormar(Child, database=database, metadata=metadata)
    child_str = ormar_model_str_repr(OrmarChild)
    parent_str = ormar_model_str_repr(OrmarParent, skip_names_if_match=True)
    assert "class Child(ormar.Model):" in child_str
    assert "    class Meta(ormar.ModelMeta):" in child_str
    assert "        metadata=metadata" in child_str
    assert "        database=database" in child_str
    assert '        tablename="right"' in child_str
    assert (
        "    id = ormar.Integer(autoincrement=True, " "primary_key=True)" in child_str
    )
    assert "    name = ormar.String(max_length=50, " "nullable=False)" in child_str

    assert "class Parent(ormar.Model):" in parent_str
    assert "    class Meta(ormar.ModelMeta):" in parent_str
    assert "        metadata=metadata" in parent_str
    assert "        database=database" in parent_str
    assert '        tablename="left"' in parent_str
    assert "    id = ormar.Integer(autoincrement=True, primary_key=True)" in parent_str
    assert "    name = ormar.String(max_length=50, nullable=False)" in parent_str
    assert (
        "    children = ormar.ManyToMany(to=Child, through=Association, "
        'related_name="parents", nullable=True)' in parent_str
    )


@pytest.mark.asyncio
async def test_many_to_many():
    ParentOrmar = sqlalchemy_to_ormar(Parent, database=database, metadata=metadata)
    ChildOrmar = sqlalchemy_to_ormar(Child, database=database, metadata=metadata)

    child = await ChildOrmar(name="child1").save()
    child2 = await ChildOrmar(name="child2").save()

    parent = await ParentOrmar(name="parent1").save()
    await parent.children.add(child)
    await parent.children.add(child2)

    parent_check = (
        await ParentOrmar.objects.select_related("children")
        .order_by("-children__name")
        .get()
    )
    assert parent_check.name == "parent1"
    assert len(parent_check.children) == 2
    assert parent_check.children[0].name == "child2"
    assert parent_check.children[1].name == "child1"
