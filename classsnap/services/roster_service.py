"""
Roster Management and CSV Import Service for ClassSnap.
"""

import csv
import io
import json
import re
from datetime import datetime, timezone
from typing import List, Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session

from classsnap.exceptions import DatabaseError, ResourceNotFoundError, ValidationError
from classsnap.logger import get_logger
from classsnap.models.audit import AuditEvent
from classsnap.models.student import Student
from classsnap.schemas.student import (
    RosterImportError,
    RosterImportSummary,
    StudentCreate,
    StudentUpdate,
    USN_PATTERN,
)

logger = get_logger("services.roster")


class RosterService:
    """Handles registered student roster CRUD and CSV batch import."""

    @staticmethod
    def create_student(db: Session, student_in: StudentCreate, actor: str = "system") -> Student:
        """Creates a single new student record."""
        # Check uniqueness of institutional student_id
        existing = db.execute(
            select(Student).where(Student.student_id == student_in.student_id)
        ).scalar_one_or_none()

        if existing:
            raise ValidationError(
                message=f"Student ID '{student_in.student_id}' is already registered.",
                details={"student_id": student_in.student_id},
            )

        consent_dt = datetime.now(timezone.utc) if student_in.has_consent else None

        student = Student(
            id=str(__import__("uuid").uuid4()),
            student_id=student_in.student_id.strip(),
            first_name=student_in.first_name.strip(),
            last_name=student_in.last_name.strip(),
            email=student_in.email.strip().lower() if student_in.email else None,
            has_consent=student_in.has_consent,
            consent_recorded_at=consent_dt,
            consent_notes=student_in.consent_notes,
            is_active=True,
        )

        db.add(student)
        db.flush()  # Populate student.id before referencing it in audit log

        # Audit log
        audit = AuditEvent(
            action="STUDENT_CREATED",
            entity_type="student",
            entity_id=student.id,
            actor=actor,
            details=json.dumps({"student_id": student.student_id, "name": student.full_name}),
        )
        db.add(audit)
        db.commit()
        db.refresh(student)

        logger.info(f"Created student record: {student.student_id} ({student.full_name})")
        return student

    @staticmethod
    def get_student_by_id(db: Session, id_or_student_id: str) -> Student:
        """Retrieves a student by UUID or institutional student_id."""
        stmt = select(Student).where(
            (Student.id == id_or_student_id) | (Student.student_id == id_or_student_id)
        )
        student = db.execute(stmt).scalar_one_or_none()
        if not student:
            raise ResourceNotFoundError(resource_type="Student", identifier=id_or_student_id)
        return student

    @staticmethod
    def get_students(
        db: Session,
        active_only: bool = False,
        limit: int = 500,
        offset: int = 0,
    ) -> List[Student]:
        """Lists students with optional active filter and pagination."""
        stmt = select(Student)
        if active_only:
            stmt = stmt.where(Student.is_active == True)
        stmt = stmt.order_by(Student.student_id).offset(offset).limit(limit)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def update_student(
        db: Session,
        id_or_student_id: str,
        student_in: StudentUpdate,
        actor: str = "system",
    ) -> Student:
        """Updates an existing student's demographic or consent information."""
        student = RosterService.get_student_by_id(db, id_or_student_id)

        update_dict = student_in.model_dump(exclude_unset=True)

        # Handle consent timestamp changes
        if "has_consent" in update_dict:
            if update_dict["has_consent"] and not student.has_consent:
                student.consent_recorded_at = datetime.now(timezone.utc)
            elif not update_dict["has_consent"]:
                student.consent_recorded_at = None

        for key, val in update_dict.items():
            setattr(student, key, val)

        # Audit log
        audit = AuditEvent(
            action="STUDENT_UPDATED",
            entity_type="student",
            entity_id=student.id,
            actor=actor,
            details=json.dumps(update_dict),
        )
        db.add(audit)
        db.commit()
        db.refresh(student)

        logger.info(f"Updated student record {student.student_id}")
        return student

    @staticmethod
    def deactivate_student(db: Session, id_or_student_id: str, actor: str = "system") -> Student:
        """Soft-deactivates a student record."""
        return RosterService.update_student(
            db,
            id_or_student_id,
            StudentUpdate(is_active=False),
            actor=actor,
        )

    @staticmethod
    def delete_student(db: Session, id_or_student_id: str, actor: str = "system") -> bool:
        """Permanently deletes a student record and associated biometric templates."""
        student = RosterService.get_student_by_id(db, id_or_student_id)
        student_id_str = student.student_id
        student_pk = student.id

        db.delete(student)

        audit = AuditEvent(
            action="STUDENT_DELETED",
            entity_type="student",
            entity_id=student_pk,
            actor=actor,
            details=json.dumps({"student_id": student_id_str}),
        )
        db.add(audit)
        db.commit()

        logger.info(f"Deleted student record: {student_id_str}")
        return True

    @staticmethod
    def import_roster_from_csv(
        db: Session,
        csv_data: Union[str, bytes],
        actor: str = "system",
    ) -> RosterImportSummary:
        """
        Parses and imports a student roster CSV file.
        Enforces required columns, checks duplicate student IDs, and validates fields.
        """
        if isinstance(csv_data, bytes):
            # Try utf-8-sig (handles Excel BOM) then fallback to utf-8 / latin1
            try:
                content = csv_data.decode("utf-8-sig")
            except UnicodeDecodeError:
                content = csv_data.decode("latin1")
        else:
            content = csv_data

        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames:
            raise ValidationError("CSV file is empty or missing header row.")

        # Normalize fieldnames to lowercase trimmed
        header_map = {fn.strip().lower(): fn for fn in reader.fieldnames}
        required = ["student_id", "first_name", "last_name"]
        missing = [req for req in required if req not in header_map]
        if missing:
            raise ValidationError(
                f"CSV missing mandatory columns: {', '.join(missing)}. "
                f"Found headers: {', '.join(reader.fieldnames)}"
            )

        seen_in_csv = set()
        existing_db_ids = set(db.execute(select(Student.student_id)).scalars().all())

        imported_count = 0
        skipped_count = 0
        errors: List[RosterImportError] = []

        students_to_add: List[Student] = []

        for row_idx, row in enumerate(reader, start=2):
            raw_id = row.get(header_map["student_id"], "").strip()
            first_name = row.get(header_map["first_name"], "").strip()
            last_name = row.get(header_map["last_name"], "").strip()

            email_header = header_map.get("email")
            email = row.get(email_header, "").strip() if email_header else None

            consent_header = header_map.get("has_consent")
            has_consent_raw = row.get(consent_header, "false").strip().lower() if consent_header else "false"
            has_consent = has_consent_raw in ("true", "1", "yes", "y", "t")

            # Field validation
            if not raw_id:
                errors.append(RosterImportError(row_number=row_idx, student_id=None, error_message="Missing student_id"))
                skipped_count += 1
                continue

            if not re.fullmatch(USN_PATTERN, raw_id):
                errors.append(
                    RosterImportError(
                        row_number=row_idx,
                        student_id=raw_id,
                        error_message="student_id must be a USN in the format ENG24AM0107",
                    )
                )
                skipped_count += 1
                continue

            if not first_name or not last_name:
                errors.append(
                    RosterImportError(
                        row_number=row_idx,
                        student_id=raw_id,
                        error_message="First name and last name are required",
                    )
                )
                skipped_count += 1
                continue

            # Check duplicates in CSV
            if raw_id in seen_in_csv:
                errors.append(
                    RosterImportError(
                        row_number=row_idx,
                        student_id=raw_id,
                        error_message="Duplicate student_id within CSV file",
                    )
                )
                skipped_count += 1
                continue
            seen_in_csv.add(raw_id)

            # Check duplicates in DB
            if raw_id in existing_db_ids:
                errors.append(
                    RosterImportError(
                        row_number=row_idx,
                        student_id=raw_id,
                        error_message="Student ID already exists in database",
                    )
                )
                skipped_count += 1
                continue

            consent_dt = datetime.now(timezone.utc) if has_consent else None

            student = Student(
                student_id=raw_id,
                first_name=first_name,
                last_name=last_name,
                email=email if email else None,
                has_consent=has_consent,
                consent_recorded_at=consent_dt,
                consent_notes="Imported via roster CSV" if has_consent else None,
                is_active=True,
            )
            students_to_add.append(student)
            existing_db_ids.add(raw_id)
            imported_count += 1

        if students_to_add:
            db.add_all(students_to_add)

            # Audit record
            audit = AuditEvent(
                action="ROSTER_CSV_IMPORTED",
                entity_type="roster",
                entity_id="batch",
                actor=actor,
                details=json.dumps({"imported_count": imported_count, "skipped_count": skipped_count}),
            )
            db.add(audit)
            db.commit()

        logger.info(f"Roster import completed: {imported_count} imported, {skipped_count} skipped/errors")

        return RosterImportSummary(
            total_processed=imported_count + skipped_count,
            imported_count=imported_count,
            skipped_count=skipped_count,
            errors=errors,
        )
