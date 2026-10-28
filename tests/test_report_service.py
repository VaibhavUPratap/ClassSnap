from classsnap.schemas.student import StudentCreate
from classsnap.services.attendance_service import AttendanceService
from classsnap.services.report_service import ReportService
from classsnap.services.roster_service import RosterService


def _confirmed_session(db_session):
    present = RosterService.create_student(
        db_session, StudentCreate(student_id="REP24OR0001", first_name="Present", last_name="Student")
    )
    RosterService.create_student(
        db_session, StudentCreate(student_id="REP24OR0002", first_name="Absent", last_name="Student")
    )
    session = AttendanceService.create_session(db_session, "Report Session")
    AttendanceService.begin_processing(db_session, session.id)
    AttendanceService.add_proposals(
        db_session, session.id, [("face-report", "matched_pending_review", present.id, 0.9, None)]
    )
    AttendanceService.review_detection(db_session, session.id, "face-report", present.id, True)
    AttendanceService.confirm(db_session, session.id)
    return session


def test_confirmed_attendance_exports_csv_and_xlsx(db_session):
    session = _confirmed_session(db_session)

    csv_content, csv_type, csv_name = ReportService.export_attendance(db_session, session.id, "csv")
    assert b"REP24OR0001" in csv_content
    assert b",absent" in csv_content
    assert csv_type == "text/csv"
    assert csv_name.endswith(".csv")

    xlsx_content, xlsx_type, xlsx_name = ReportService.export_attendance(
        db_session, session.id, "xlsx"
    )
    assert xlsx_content[:2] == b"PK"
    assert "spreadsheet" in xlsx_type
    assert xlsx_name.endswith(".xlsx")
