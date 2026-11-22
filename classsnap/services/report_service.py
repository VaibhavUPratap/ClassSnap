"""Confirmed attendance reports, history, and exports.

Every figure here is read from the final ``attendance_records`` rows written at
confirmation, so exports always match what is stored in the database.
"""

import csv
import io
from datetime import datetime
from typing import Literal

from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from classsnap.exceptions import ResourceNotFoundError, ValidationError
from classsnap.models.attendance import (
    FINAL_ABSENT,
    FINAL_PRESENT,
    FINAL_UNVERIFIED,
    AttendanceRecord,
    AttendanceSession,
)
from classsnap.models.student import Student
from classsnap.schemas.attendance import (
    SessionHistoryItem,
    StudentAttendanceHistory,
    StudentSessionAttendance,
)
from classsnap.schemas.report import (
    AttendanceReportSession,
    AttendanceReportStudent,
    AttendanceReportSummary,
)

EXPORT_HEADERS = [
    "session_id",
    "session_name",
    "student_id",
    "student_name",
    "status",
    "session_date",
    "subject",
    "class_section",
    "verification_method",
    "confirmed_at",
    "confirmed_by",
    "corrected_by",
    "correction_reason",
]


def _class_timestamp():
    return func.coalesce(AttendanceSession.class_at, AttendanceSession.created_at)


def _counts(records: list[AttendanceRecord]) -> dict[str, int]:
    return {
        "present": sum(1 for r in records if r.attendance_status == FINAL_PRESENT),
        "absent": sum(1 for r in records if r.attendance_status == FINAL_ABSENT),
        "unverified": sum(1 for r in records if r.attendance_status == FINAL_UNVERIFIED),
    }


def _iso(value: datetime | None) -> str:
    return value.isoformat() if isinstance(value, datetime) else ""


class ReportService:
    @staticmethod
    def confirmed_sessions(
        db: Session,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> AttendanceReportSummary:
        statement = (
            select(AttendanceSession)
            .where(AttendanceSession.status == "confirmed")
            .order_by(_class_timestamp().desc())
        )
        if date_from is not None:
            statement = statement.where(_class_timestamp() >= date_from)
        if date_to is not None:
            statement = statement.where(_class_timestamp() < date_to)

        sessions = db.execute(statement).scalars().all()
        student_ids = {r.student_id for s in sessions for r in s.attendance}
        students = {
            s.id: s for s in db.execute(select(Student).where(Student.id.in_(student_ids))).scalars()
        } if student_ids else {}
        rows = []
        total_attendance = 0
        total_possible = 0
        for session in sessions:
            counts = _counts(session.attendance)
            attendees = sorted(
                (
                    AttendanceReportStudent(
                        student_id=students[r.student_id].student_id,
                        student_name=students[r.student_id].full_name,
                    )
                    for r in session.attendance
                    if r.attendance_status == FINAL_PRESENT and r.student_id in students
                ),
                key=lambda a: a.student_id,
            )
            total_attendance += counts["present"]
            total_possible += len(session.attendance)
            rows.append(
                AttendanceReportSession(
                    session_id=session.id,
                    session_name=session.name,
                    class_date=session.class_at or session.created_at,
                    class_section=session.class_section,
                    confirmed_at=session.confirmed_at,
                    confirmed_by=session.confirmed_by,
                    present_count=counts["present"],
                    absent_count=counts["absent"],
                    unverified_count=counts["unverified"],
                    total_registered=len(session.attendance),
                    attendees=attendees,
                )
            )
        return AttendanceReportSummary(
            total_sessions=len(rows),
            total_attendance=total_attendance,
            total_possible=total_possible,
            sessions=rows,
        )

    @staticmethod
    def session_history(db: Session, status: str | None = None) -> list[SessionHistoryItem]:
        """All sessions (newest class first), with final counts for confirmed ones."""
        statement = select(AttendanceSession).order_by(_class_timestamp().desc())
        if status:
            statement = statement.where(AttendanceSession.status == status)
        items = []
        for session in db.execute(statement).scalars():
            counts = _counts(session.attendance)
            items.append(
                SessionHistoryItem(
                    session_id=session.id,
                    session_name=session.name,
                    status=session.status,
                    class_date=session.class_at or session.created_at,
                    class_section=session.class_section,
                    confirmed_at=session.confirmed_at,
                    confirmed_by=session.confirmed_by,
                    total_registered=len(session.attendance),
                    present_count=counts["present"],
                    absent_count=counts["absent"],
                    unverified_count=counts["unverified"],
                )
            )
        return items

    @staticmethod
    def student_history(db: Session, student_ref: str) -> StudentAttendanceHistory:
        """Confirmed attendance for one student, by internal id or USN."""
        student = db.get(Student, student_ref) or db.execute(
            select(Student).where(Student.student_id == student_ref.upper())
        ).scalar_one_or_none()
        if student is None:
            raise ResourceNotFoundError("Student", student_ref)
        rows = db.execute(
            select(AttendanceRecord, AttendanceSession)
            .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
            .where(
                AttendanceRecord.student_id == student.id,
                AttendanceSession.status == "confirmed",
            )
            .order_by(_class_timestamp().desc())
        ).all()
        sessions = [
            StudentSessionAttendance(
                session_id=session.id,
                session_name=session.name,
                class_date=session.class_at or session.created_at,
                class_section=session.class_section,
                status=record.attendance_status,
                verification_method=record.verification_method,
                confirmed_at=session.confirmed_at,
            )
            for record, session in rows
        ]
        counts = _counts([record for record, _ in rows])
        decided = counts["present"] + counts["absent"]
        return StudentAttendanceHistory(
            student_id=student.id,
            student_usn=student.student_id,
            student_name=student.full_name,
            class_section=student.class_section,
            total_sessions=len(sessions),
            sessions_attended=counts["present"],
            sessions_absent=counts["absent"],
            sessions_unverified=counts["unverified"],
            attendance_rate=round(counts["present"] / decided, 4) if decided else None,
            sessions=sessions,
        )

    @staticmethod
    def attendance_rows(db: Session, session_id: str) -> list[dict[str, object]]:
        session = db.get(AttendanceSession, session_id)
        if session is None:
            raise ValidationError(f"Attendance session '{session_id}' was not found")
        if session.status != "confirmed":
            raise ValidationError("Attendance reports are available only for confirmed sessions")

        records = db.execute(
            select(AttendanceRecord, Student)
            .join(Student, Student.id == AttendanceRecord.student_id)
            .where(AttendanceRecord.session_id == session_id)
            .order_by(Student.student_id)
        ).all()
        class_date = session.class_at or session.created_at
        return [
            {
                "session_id": session.id,
                "session_name": session.name,
                "student_id": student.student_id,
                "student_name": student.full_name,
                "status": record.attendance_status,
                "session_date": class_date.date().isoformat() if class_date else "",
                "subject": session.name,
                "class_section": session.class_section or student.class_section or "",
                "verification_method": record.verification_method or "",
                "confirmed_at": _iso(record.confirmed_at or session.confirmed_at),
                "confirmed_by": record.reviewed_by or session.confirmed_by or "",
                "corrected_by": record.corrected_by or "",
                "correction_reason": record.correction_reason or "",
            }
            for record, student in records
        ]

    @staticmethod
    def export_attendance(
        db: Session, session_id: str, file_format: Literal["csv", "xlsx"]
    ) -> tuple[bytes, str, str]:
        rows = ReportService.attendance_rows(db, session_id)
        if file_format == "csv":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=EXPORT_HEADERS)
            writer.writeheader()
            writer.writerows(rows)
            return output.getvalue().encode("utf-8"), "text/csv", f"attendance-{session_id}.csv"

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Attendance"
        worksheet.append(EXPORT_HEADERS)
        for cell in worksheet[1]:
            cell.font = Font(bold=True)
        for row in rows:
            worksheet.append([row[header] for header in EXPORT_HEADERS])

        summary = workbook.create_sheet("Summary")
        statuses = [row["status"] for row in rows]
        session = db.get(AttendanceSession, session_id)
        for label, value in [
            ("Session", session.name),
            ("Class", session.class_section or "All"),
            ("Session date", rows[0]["session_date"] if rows else ""),
            ("Confirmed at", _iso(session.confirmed_at)),
            ("Confirmed by", session.confirmed_by or ""),
            ("Total registered", len(rows)),
            ("Present", statuses.count(FINAL_PRESENT)),
            ("Absent", statuses.count(FINAL_ABSENT)),
            ("Unverified", statuses.count(FINAL_UNVERIFIED)),
        ]:
            summary.append([label, value])
        output = io.BytesIO()
        workbook.save(output)
        return (
            output.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            f"attendance-{session_id}.xlsx",
        )
