"""Confirmed attendance report generation."""

import csv
import io
from typing import Literal

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from classsnap.exceptions import ValidationError
from classsnap.models.attendance import AttendanceRecord, AttendanceSession
from classsnap.models.student import Student


class ReportService:
    @staticmethod
    def attendance_rows(db: Session, session_id: str) -> list[dict[str, object]]:
        session = db.get(AttendanceSession, session_id)
        if session is None:
            raise ValidationError(f"Attendance session '{session_id}' was not found")
        if session.status != "confirmed":
            raise ValidationError("Attendance reports are available only for confirmed sessions")

        present_ids = set(
            db.execute(
                select(AttendanceRecord.student_id).where(
                    AttendanceRecord.session_id == session_id,
                    AttendanceRecord.present.is_(True),
                )
            ).scalars()
        )
        students = db.execute(
            select(Student).where(Student.is_active.is_(True)).order_by(Student.student_id)
        ).scalars()
        return [
            {
                "session_id": session.id,
                "session_name": session.name,
                "student_id": student.student_id,
                "student_name": student.full_name,
                "status": "present" if student.id in present_ids else "absent",
            }
            for student in students
        ]

    @staticmethod
    def export_attendance(
        db: Session, session_id: str, file_format: Literal["csv", "xlsx"]
    ) -> tuple[bytes, str, str]:
        rows = ReportService.attendance_rows(db, session_id)
        headers = ["session_id", "session_name", "student_id", "student_name", "status"]
        if file_format == "csv":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
            return output.getvalue().encode("utf-8"), "text/csv", f"attendance-{session_id}.csv"

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Attendance"
        worksheet.append(headers)
        for row in rows:
            worksheet.append([row[header] for header in headers])
        output = io.BytesIO()
        workbook.save(output)
        return (
            output.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            f"attendance-{session_id}.xlsx",
        )
