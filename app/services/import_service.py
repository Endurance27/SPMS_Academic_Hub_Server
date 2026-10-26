import csv
import io
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import SecurityService
from app.models.registration import (
    CourseRegistration,
    RegistrationStatus,
    RegistrationType,
    StudentImport,
    StudentImportRow,
)
from app.models.user import User, UserRole, UserStatus


class ImportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_student_import(
        self,
        file_content: bytes,
        filename: str,
        department_id: uuid.UUID,
        student_category: str,
        academic_year: str,
        programme_id: Optional[uuid.UUID],
        level: Optional[int],
        created_by_id: uuid.UUID,
    ) -> StudentImport:
        decoded = file_content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))
        rows_raw = list(reader)

        if not rows_raw:
            raise ValueError("The CSV file must include a header and at least one row.")

        headers_lower = [h.lower().strip() for h in (reader.fieldnames or [])]
        required = ["student id", "name", "email"]
        missing = [r for r in required if r not in headers_lower]
        if missing:
            raise ValueError(f"Missing CSV columns: {', '.join(missing)}")

        header_map = {h.lower().strip(): h for h in (reader.fieldnames or [])}

        import_obj = StudentImport(
            kind="student-onboarding",
            department_id=department_id,
            programme_id=programme_id,
            student_category=student_category,
            academic_year=academic_year,
            filename=filename,
            row_count=len(rows_raw),
            status="Processing",
            created_by_id=created_by_id,
        )
        self.db.add(import_obj)
        await self.db.flush()

        created_count = 0
        updated_count = 0
        warning_count = 0
        error_count = 0

        for i, row in enumerate(rows_raw, start=1):
            student_number = row.get(header_map.get("student id", ""), "").strip()
            name = row.get(header_map.get("name", ""), "").strip()
            email = row.get(header_map.get("email", ""), "").strip().lower()

            raw_data = dict(row)
            outcome = None
            message = None

            if not email or not name:
                outcome = "skipped"
                message = "Missing required field (name or email)"
                error_count += 1
            else:
                existing = await self.db.execute(
                    select(User).where(
                        (User.email == email) | (User.student_number == student_number)
                    )
                )
                existing_user = existing.scalar_one_or_none()

                if existing_user:
                    if student_number and not existing_user.student_number:
                        existing_user.student_number = student_number
                    if programme_id and not existing_user.programme_id:
                        existing_user.programme_id = programme_id
                    if level and not existing_user.level:
                        existing_user.level = level
                    outcome = "updated"
                    updated_count += 1
                else:
                    hashed_pw = SecurityService.get_password_hash(
                        SecurityService.generate_temp_password()
                    )
                    new_user = User(
                        email=email,
                        hashed_password=hashed_pw,
                        name=name,
                        role=UserRole.STUDENT,
                        status=UserStatus.INVITED,
                        student_number=student_number or None,
                        programme_id=programme_id,
                        level=level,
                        student_category=student_category,
                        title=f"Level {level} Student" if level else "Student",
                    )
                    self.db.add(new_user)
                    outcome = "created"
                    created_count += 1

            import_row = StudentImportRow(
                import_id=import_obj.id,
                row_number=i,
                raw=raw_data,
                outcome=outcome,
                message=message,
            )
            self.db.add(import_row)

        import_obj.created_count = created_count
        import_obj.updated_count = updated_count
        import_obj.warning_count = warning_count
        import_obj.error_count = error_count
        import_obj.status = "Completed"

        await self.db.commit()
        await self.db.refresh(import_obj)
        return import_obj

    async def create_course_roster_import(
        self,
        file_content: bytes,
        filename: str,
        course_id: uuid.UUID,
        department_id: uuid.UUID,
        student_category: str,
        academic_year: str,
        semester_id: uuid.UUID,
        created_by_id: uuid.UUID,
    ) -> StudentImport:
        decoded = file_content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))
        rows_raw = list(reader)

        if not rows_raw:
            raise ValueError("The CSV file must include a header and at least one row.")

        headers_lower = [h.lower().strip() for h in (reader.fieldnames or [])]
        required = ["student id", "name", "email"]
        missing = [r for r in required if r not in headers_lower]
        if missing:
            raise ValueError(f"Missing CSV columns: {', '.join(missing)}")

        header_map = {h.lower().strip(): h for h in (reader.fieldnames or [])}

        import_obj = StudentImport(
            kind="course-roster",
            department_id=department_id,
            course_id=course_id,
            student_category=student_category,
            academic_year=academic_year,
            semester_id=semester_id,
            filename=filename,
            row_count=len(rows_raw),
            status="Processing",
            created_by_id=created_by_id,
        )
        self.db.add(import_obj)
        await self.db.flush()

        created_count = 0
        updated_count = 0
        error_count = 0

        for i, row in enumerate(rows_raw, start=1):
            student_number = row.get(header_map.get("student id", ""), "").strip()
            name = row.get(header_map.get("name", ""), "").strip()
            email = row.get(header_map.get("email", ""), "").strip().lower()

            raw_data = dict(row)
            outcome = None
            message = None

            if not email or not name:
                outcome = "skipped"
                message = "Missing required field (name or email)"
                error_count += 1
            else:
                existing = await self.db.execute(
                    select(User).where(
                        (User.email == email) | (User.student_number == student_number)
                    )
                )
                student = existing.scalar_one_or_none()

                if not student:
                    hashed_pw = SecurityService.get_password_hash(
                        SecurityService.generate_temp_password()
                    )
                    student = User(
                        email=email,
                        hashed_password=hashed_pw,
                        name=name,
                        role=UserRole.STUDENT,
                        status=UserStatus.INVITED,
                        student_number=student_number or None,
                        student_category=student_category,
                        title="Student",
                    )
                    self.db.add(student)
                    await self.db.flush()
                    outcome = "created"
                    created_count += 1
                else:
                    outcome = "updated"
                    updated_count += 1

                # Create course registration
                existing_reg = await self.db.execute(
                    select(CourseRegistration).where(
                        CourseRegistration.student_id == student.id,
                        CourseRegistration.course_id == course_id,
                        CourseRegistration.semester_id == semester_id,
                    )
                )
                if not existing_reg.scalar_one_or_none():
                    reg = CourseRegistration(
                        student_id=student.id,
                        course_id=course_id,
                        semester_id=semester_id,
                        level=student.level or 100,
                        registration_type=RegistrationType.CORE,
                        credits=3,
                        status=RegistrationStatus.REGISTERED,
                        source="roster-import",
                    )
                    self.db.add(reg)

            import_row = StudentImportRow(
                import_id=import_obj.id,
                row_number=i,
                raw=raw_data,
                outcome=outcome,
                message=message,
            )
            self.db.add(import_row)

        import_obj.created_count = created_count
        import_obj.updated_count = updated_count
        import_obj.error_count = error_count
        import_obj.status = "Completed"

        await self.db.commit()
        await self.db.refresh(import_obj)
        return import_obj

    async def list_imports(
        self,
        kind: Optional[str] = None,
        department_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 25,
    ) -> List[StudentImport]:
        query = select(StudentImport)

        if kind:
            query = query.where(StudentImport.kind == kind)
        if department_id:
            query = query.where(StudentImport.department_id == department_id)

        query = query.offset(skip).limit(limit).order_by(
            StudentImport.created_at.desc()
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_import(self, import_id: uuid.UUID) -> Optional[StudentImport]:
        result = await self.db.execute(
            select(StudentImport).where(StudentImport.id == import_id)
        )
        return result.scalar_one_or_none()

    async def get_import_rows(
        self,
        import_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[StudentImportRow]:
        result = await self.db.execute(
            select(StudentImportRow)
            .where(StudentImportRow.import_id == import_id)
            .order_by(StudentImportRow.row_number)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
