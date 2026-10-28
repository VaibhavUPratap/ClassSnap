from classsnap.schemas.student import StudentCreate
from classsnap.services.attendance_service import AttendanceService
from classsnap.services.roster_service import RosterService


def test_report_endpoint_rejects_unconfirmed_session(client):
    created = client.post(
        "/api/v1/attendance/sessions",
        json={"name": "Unconfirmed Report"},
    )
    response = client.get(f"/api/v1/attendance/sessions/{created.json()['id']}/report")
    assert response.status_code == 422
    assert "confirmed" in response.json()["error"]["message"]


def test_report_summary_returns_confirmed_class_attendees(client, db_session):
    student = RosterService.create_student(
        db_session,
        StudentCreate(student_id="REP24SU0001", first_name="Present", last_name="Student"),
    )
    session = AttendanceService.create_session(db_session, "Morning Class", "teacher")
    AttendanceService.begin_processing(db_session, session.id)
    AttendanceService.add_proposals(
        db_session,
        session.id,
        [("face-1", "matched_pending_review", student.id, 0.95, None)],
    )
    AttendanceService.review_detection(db_session, session.id, "face-1", student.id, True)
    AttendanceService.confirm(db_session, session.id)

    response = client.get("/api/v1/attendance/sessions/reports/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["total_sessions"] == 1
    assert data["total_attendance"] == 1
    assert data["sessions"][0]["session_name"] == "Morning Class"
    assert data["sessions"][0]["attendees"][0]["student_id"] == "REP24SU0001"
