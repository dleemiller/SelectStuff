import json
from typing import Optional
from sqlmodel import SQLModel, Session, create_engine, select
from app.applications.sql_converter import SignatureToSQLModel
import dspy


class SampleSignature(dspy.Signature):
    """
    Example DSPy-style signature class.
    """

    name: str = dspy.InputField()
    age: int = dspy.OutputField()
    preferences: Optional[dict] = dspy.OutputField()
    tags: Optional[list] = dspy.OutputField()


def test_signature_to_sqlmodel_conversion():
    """
    Test the conversion of a Pydantic class into a SQLModel class.
    """

    # Convert SampleSignature to a SQLModel class
    SQLModel.metadata.clear()
    SampleSQLModel = SignatureToSQLModel.to_sqlmodel(SampleSignature)

    # Assert table name and attributes
    assert SampleSQLModel.__tablename__ == "samplesignaturesqlmodel"
    assert hasattr(SampleSQLModel, "name")
    assert hasattr(SampleSQLModel, "age")
    assert hasattr(SampleSQLModel, "preferences")
    assert hasattr(SampleSQLModel, "tags")

    # Verify the Python types of the attributes
    assert SampleSQLModel.__annotations__["name"] == str  # Should be str
    assert SampleSQLModel.__annotations__["age"] == int  # Should be int
    assert SampleSQLModel.__annotations__["preferences"] is Optional[str]
    assert SampleSQLModel.__annotations__["tags"] == Optional[str]


def test_sqlmodel_crud_operations():
    """
    Test CRUD operations on the generated SQLModel class with an in-memory SQLite database.
    """
    SQLModel.metadata.clear()
    SampleSQLModel = SignatureToSQLModel.to_sqlmodel(SampleSignature)

    # Set up an in-memory SQLite database
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)

    # Create and insert a test record
    with Session(engine) as session:
        instance = SampleSQLModel(name="Alice", age=25, preferences={"theme": "dark"})
        session.add(instance)
        session.commit()
        session.refresh(instance)

        # Verify the record's properties
        assert instance.id is not None
        assert instance.name == "Alice"
        assert instance.age == 25
        assert json.loads(instance.preferences) == {"theme": "dark"}

        # Query the database and validate the result
        stmt = select(SampleSQLModel).where(SampleSQLModel.id == instance.id)
        record = session.exec(stmt).first()

        assert record is not None
        assert record.name == "Alice"
        assert record.age == 25
        assert json.loads(record.preferences) == {"theme": "dark"}
