import pytest

from classsnap.exceptions import ValidationError
from classsnap.models.attendance import AttendanceRecord, ReviewDecision
from classsnap.schemas.student import StudentCreate
from classsnap.services.attendance_service import AttendanceService
from classsnap.services.roster_service import RosterService


def test_session_requires_review_before_confirmation(db_session):
    session = AttendanceService.create_session(db_session, "Math 101")
    AttendanceService.begin_processing(db_session, session.id)
    AttendanceService.add_proposals(
        db_session, session.id, [("face-1", "matched_pending_review", None, 0.9, None)]
    )

    with pytest.raises(ValidationError, match="reviewed"):
        AttendanceService.confirm(db_session, session.id)


def test_review_and_confirmation_create_unique_attendance_record(db_session):
    student = RosterService.create_student(
        db_session,
        StudentCreate(student_id="ATT24AT0001", first_name="Ada", last_name="Lovelace"),
    )
    session = AttendanceService.create_session(db_session, "Math 101")
    AttendanceService.begin_processing(db_session, session.id)
    AttendanceService.add_proposals(
        db_session, session.id, [("face-1", "matched_pending_review", student.id, 0.95, None)]
    )
    AttendanceService.review_detection(
        db_session, session.id, "face-1", student.id, True, actor="teacher-1", notes="Confirmed manually"
    )
    confirmed = AttendanceService.confirm(db_session, session.id)

    assert confirmed.status == "confirmed"
    records = db_session.query(AttendanceRecord).filter_by(session_id=session.id).all()
    assert len(records) == 1
    assert records[0].student_id == student.id
    decisions = db_session.query(ReviewDecision).filter_by(session_id=session.id).all()
    assert len(decisions) == 1
    assert decisions[0].reviewer == "teacher-1"
    assert decisions[0].decision == "present"
    assert decisions[0].original_student_id == student.id
    assert decisions[0].selected_student_id == student.id
    assert decisions[0].notes == "Confirmed manually"

    with pytest.raises(ValidationError, match="expected"):
        AttendanceService.confirm(db_session, session.id)


def test_confirmed_session_supports_audited_correction_only_through_workflow(db_session):
    first = RosterService.create_student(
        db_session,
        StudentCreate(student_id="ATT24AT0002", first_name="Grace", last_name="Hopper"),
    )
    second = RosterService.create_student(
        db_session,
        StudentCreate(student_id="ATT24AT0003", first_name="Katherine", last_name="Johnson"),
    )
    session = AttendanceService.create_session(db_session, "Physics 101")
    AttendanceService.begin_processing(db_session, session.id)
    AttendanceService.add_proposals(
        db_session, session.id, [("face-1", "matched_pending_review", first.id, 0.9, None)]
    )
    AttendanceService.review_detection(db_session, session.id, "face-1", first.id, True)
    AttendanceService.confirm(db_session, session.id)

    AttendanceService.correct_confirmed_attendance(
        db_session,
        session.id,
        "face-1",
        second.id,
        True,
        actor="teacher-2",
        reason="Corrected after comparing the seating chart",
    )

    records = db_session.query(AttendanceRecord).filter_by(session_id=session.id).all()
    assert [record.student_id for record in records] == [second.id]
    decisions = db_session.query(ReviewDecision).filter_by(session_id=session.id).all()
    assert len(decisions) == 2
    assert decisions[-1].decision == "correction_present"
    assert decisions[-1].original_student_id == first.id
    assert decisions[-1].selected_student_id == second.id

    with pytest.raises(ValidationError, match="reason"):
        AttendanceService.correct_confirmed_attendance(
            db_session, session.id, "face-1", None, False, "teacher-2", ""
        )


def test_duplicate_correction_rolls_back_without_changing_attendance(db_session):
    first = RosterService.create_student(
        db_session,
        StudentCreate(student_id="ATT24AT0004", first_name="Alan", last_name="Turing"),
    )
    already_present = RosterService.create_student(
        db_session,
        StudentCreate(student_id="ATT24AT0005", first_name="Dorothy", last_name="Vaughan"),
    )
    session = AttendanceService.create_session(db_session, "Computer Science 101")
    AttendanceService.begin_processing(db_session, session.id)
    AttendanceService.add_proposals(
        db_session,
        session.id,
        [
            ("face-1", "matched_pending_review", first.id, 0.9, None),
            ("face-2", "matched_pending_review", already_present.id, 0.91, None),
        ],
    )
    AttendanceService.review_detection(db_session, session.id, "face-1", first.id, True)
    AttendanceService.review_detection(
        db_session, session.id, "face-2", already_present.id, True
    )
    AttendanceService.confirm(db_session, session.id)

    with pytest.raises(ValidationError, match="already present"):
        AttendanceService.correct_confirmed_attendance(
            db_session,
            session.id,
            "face-1",
            already_present.id,
            True,
            actor="teacher-3",
            reason="This would create a duplicate identity",
        )

    records = db_session.query(AttendanceRecord).filter_by(session_id=session.id).all()
    assert {record.student_id for record in records} == {first.id, already_present.id}


def test_processing_transition_is_single_use_across_sessions(db_session):
    session = AttendanceService.create_session(db_session, "Concurrency 101")
    second_session = db_session.__class__(bind=db_session.get_bind())
    try:
        AttendanceService.begin_processing(db_session, session.id)
        with pytest.raises(ValidationError, match="expected"):
            AttendanceService.begin_processing(second_session, session.id)
    finally:
        second_session.close()


def test_duplicate_detection_submission_is_rejected_before_commit(db_session):
    session = AttendanceService.create_session(db_session, "Duplicate Detection")
    AttendanceService.begin_processing(db_session, session.id)
    with pytest.raises(ValidationError, match="duplicate detection"):
        AttendanceService.add_proposals(
            db_session,
            session.id,
            [
                ("same-face", "unknown", None, None, "first"),
                ("same-face", "unknown", None, None, "duplicate"),
            ],
        )
    db_session.refresh(session)
    assert session.status == "processing"
