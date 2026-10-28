"""
Unit and integration tests for Roster Management and CSV Roster Import.
"""

import pytest
from sqlalchemy import select
from classsnap.exceptions import ResourceNotFoundError, ValidationError
from classsnap.models.audit import AuditEvent
from classsnap.models.student import Student
from classsnap.schemas.student import StudentCreate, StudentUpdate
from classsnap.services.roster_service import RosterService


def test_create_student_success(db_session):
    student_in = StudentCreate(
        student_id="CSE24CS0101",
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@university.edu",
        has_consent=True,
        consent_notes="Signed consent waiver",
    )
    student = RosterService.create_student(db_session, student_in)

    assert student.id is not None
    assert student.student_id == "CSE24CS0101"
    assert student.full_name == "Jane Doe"
    assert student.has_consent is True
    assert student.consent_recorded_at is not None
    assert student.is_active is True

    # Verify audit event
    audit = db_session.execute(
        select(AuditEvent).where(AuditEvent.entity_id == student.id)
    ).scalar_one_or_none()
    assert audit is not None
    assert audit.action == "STUDENT_CREATED"


def test_create_duplicate_student_fails(db_session):
    s1 = StudentCreate(student_id="DUP24DP0001", first_name="First", last_name="Student")
    RosterService.create_student(db_session, s1)

    s2 = StudentCreate(student_id="DUP24DP0001", first_name="Second", last_name="Student")
    with pytest.raises(ValidationError) as exc:
        RosterService.create_student(db_session, s2)
    assert "already registered" in str(exc.value).lower()


def test_update_and_deactivate_student(db_session):
    student = RosterService.create_student(
        db_session,
        StudentCreate(student_id="ACT24AC0001", first_name="Active", last_name="One", has_consent=False),
    )
    assert student.has_consent is False

    # Grant consent
    updated = RosterService.update_student(
        db_session,
        student.id,
        StudentUpdate(has_consent=True, consent_notes="Form signed"),
    )
    assert updated.has_consent is True
    assert updated.consent_recorded_at is not None

    # Deactivate
    deactivated = RosterService.deactivate_student(db_session, student.id)
    assert deactivated.is_active is False


def test_delete_student(db_session):
    student = RosterService.create_student(
        db_session,
        StudentCreate(student_id="DEL24DL0001", first_name="To", last_name="Delete"),
    )
    deleted = RosterService.delete_student(db_session, student.id)
    assert deleted is True

    with pytest.raises(ResourceNotFoundError):
        RosterService.get_student_by_id(db_session, student.id)


def test_import_roster_from_csv(db_session):
    csv_text = """student_id,first_name,last_name,email,has_consent
ENG24AM0001,Alice,Smith,alice@uni.edu,true
ENG24AM0002,Bob,Jones,bob@uni.edu,false
ENG24AM0003,Charlie,Brown,charlie@uni.edu,1
"""
    summary = RosterService.import_roster_from_csv(db_session, csv_text)

    assert summary.imported_count == 3
    assert summary.skipped_count == 0
    assert len(summary.errors) == 0

    s1 = RosterService.get_student_by_id(db_session, "ENG24AM0001")
    assert s1.has_consent is True
    s2 = RosterService.get_student_by_id(db_session, "ENG24AM0002")
    assert s2.has_consent is False


def test_import_roster_handles_duplicates_and_validation(db_session):
    # Pre-existing student in DB
    RosterService.create_student(
        db_session,
        StudentCreate(student_id="ENG24EX0001", first_name="Old", last_name="Record"),
    )

    csv_text = """student_id,first_name,last_name,email,has_consent
ENG24EX0001,Clash,User,clash@uni.edu,true
ENG24CD0001,Dave,Miller,,true
ENG24CD0001,DaveDuplicate,Miller,,true
,Missing,ID,,false
ENG24VW0001,Evan,Wright,evan@uni.edu,yes
"""
    summary = RosterService.import_roster_from_csv(db_session, csv_text)

    # 1 valid (VALID1), 1 existing skipped, 1 duplicate in csv skipped, 1 missing id skipped, 1 CSV_DUP first imported
    assert summary.imported_count == 2  # CSV_DUP and VALID1
    assert summary.skipped_count == 3
    assert len(summary.errors) == 3


def test_import_roster_missing_mandatory_headers(db_session):
    bad_csv = """roll_no,name,email
101,John Doe,john@uni.edu
"""
    with pytest.raises(ValidationError) as exc:
        RosterService.import_roster_from_csv(db_session, bad_csv)
    assert "missing mandatory columns" in str(exc.value).lower()
