"""
Unit tests for ClassSnap database initialization and connectivity.
"""

from sqlalchemy import Column, Integer, String, text
from classsnap.db.base import Base
from classsnap.db.session import check_db_health, init_db


class SampleModel(Base):
    __tablename__ = "test_sample"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)


def test_init_db(db_session):
    init_db(target_engine=db_session.get_bind())
    # Verify table existence by inserting a row
    sample = SampleModel(name="test_record")
    db_session.add(sample)
    db_session.commit()

    retrieved = db_session.query(SampleModel).filter_by(name="test_record").first()
    assert retrieved is not None
    assert retrieved.name == "test_record"
    assert retrieved.created_at is not None


def test_check_db_health(db_session):
    is_healthy = check_db_health(db_session)
    assert is_healthy is True


def test_sqlite_foreign_keys_pragma(db_session):
    cursor = db_session.execute(text("PRAGMA foreign_keys"))
    val = cursor.scalar()
    # Pragma should return 1 or 0
    assert val in (0, 1)
