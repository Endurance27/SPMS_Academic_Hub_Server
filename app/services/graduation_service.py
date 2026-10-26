import csv
import io
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.graduation import (
    GraduationCandidate,
    GraduationStatus,
    GraduationSubmission,
)
from app.models.settings import InstitutionSettings
from app.models.user import User, UserRole
from app.schemas.graduation import GraduationCandidateUpdate, GraduationSubmissionCreate


class GraduationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_submission(
        self,
        data: GraduationSubmissionCreate,
        file_content: bytes,
        filename: str,
        department_id: uuid.UUID,
        created_by_id: uuid.UUID,
    ) -> GraduationSubmission:
        decoded = file_content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))
        rows = list(reader)

        if not rows:
            raise ValueError("The CSV file must include a header and at least one row.")

        headers_lower = [h.lower().strip() for h in (reader.fieldnames or [])]
        required = ["student id", "name", "programme"]
        missing = [r for r in required if r not in headers_lower]
        if missing:
            raise ValueError(f"Missing CSV columns: {', '.join(missing)}")

        submission = GraduationSubmission(
            department_id=department_id,
            programme_id=data.programme_id,
            programme_text=data.programme_text or "",
            student_category=data.student_category,
            academic_year=data.academic_year,
            declared_count=data.declared_count,
            filename=filename,
            row_count=len(rows),
            status=GraduationStatus.SUBMITTED,
            created_by_id=created_by_id,
        )
        self.db.add(submission)
        await self.db.flush()

        header_map = {h.lower().strip(): h for h in (reader.fieldnames or [])}

        for row in rows:
            student_number = row.get(header_map.get("student id", ""), "").strip()
            name = row.get(header_map.get("name", ""), "").strip()
            programme = row.get(header_map.get("programme", ""), "").strip()

            issues = []
            student_id = None

            if student_number:
                student_result = await self.db.execute(
                    select(User).where(User.student_number == student_number)
                )
                student = student_result.scalar_one_or_none()
                if student:
                    student_id = student.id
                    if student.department_id and student.department_id != department_id:
                        # Check via programme's department
                        pass
                else:
                    issues.append(f"Student number {student_number} not found in system")

            candidate = GraduationCandidate(
                submission_id=submission.id,
                student_number=student_number or "UNKNOWN",
                name=name or "UNKNOWN",
                programme=programme,
                student_id=student_id,
                issues=issues,
            )
            self.db.add(candidate)

        await self.db.commit()
        await self.db.refresh(submission)
        return submission

    async def list_submissions(
        self,
        department_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 25,
    ) -> tuple[List[GraduationSubmission], dict]:
        query = select(GraduationSubmission)

        if department_id:
            query = query.where(GraduationSubmission.department_id == department_id)
        if status:
            query = query.where(GraduationSubmission.status == status)

        query = query.offset(skip).limit(limit).order_by(
            GraduationSubmission.created_at.desc()
        )
        result = await self.db.execute(query)
        submissions = list(result.scalars().all())

        # Counts
        count_base = select(
            GraduationSubmission.status, func.count(GraduationSubmission.id)
        )
        if department_id:
            count_base = count_base.where(
                GraduationSubmission.department_id == department_id
            )
        count_base = count_base.group_by(GraduationSubmission.status)
        count_result = await self.db.execute(count_base)
        count_rows = count_result.all()

        counts = {"All": 0, "Submitted": 0, "Validated": 0, "Returned": 0}
        for s, c in count_rows:
            counts[s.value] = c
            counts["All"] += c

        return submissions, counts

    async def get_submission(
        self, submission_id: uuid.UUID
    ) -> Optional[GraduationSubmission]:
        result = await self.db.execute(
            select(GraduationSubmission)
            .options(selectinload(GraduationSubmission.candidates))
            .where(GraduationSubmission.id == submission_id)
        )
        return result.scalar_one_or_none()

    async def update_candidate(
        self, candidate_id: uuid.UUID, data: GraduationCandidateUpdate
    ) -> Optional[GraduationCandidate]:
        result = await self.db.execute(
            select(GraduationCandidate).where(GraduationCandidate.id == candidate_id)
        )
        candidate = result.scalar_one_or_none()
        if not candidate:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(candidate, field, value)

        await self.db.commit()
        await self.db.refresh(candidate)
        return candidate

    async def validate_submission(
        self, submission_id: uuid.UUID, reviewer_id: uuid.UUID
    ) -> GraduationSubmission:
        submission = await self.get_submission(submission_id)
        if not submission:
            raise ValueError("Submission not found.")
        if submission.status != GraduationStatus.SUBMITTED:
            raise ValueError("Only submitted entries can be validated.")

        # Check clearance requirements
        settings_result = await self.db.execute(select(InstitutionSettings).limit(1))
        settings = settings_result.scalar_one_or_none()

        if settings:
            for candidate in submission.candidates:
                if settings.require_academic_clearance and not candidate.academic_clearance:
                    raise ValueError(
                        f"Candidate {candidate.student_number} has not received academic clearance."
                    )
                if settings.require_financial_clearance and not candidate.financial_clearance:
                    raise ValueError(
                        f"Candidate {candidate.student_number} has not received financial clearance."
                    )

        submission.status = GraduationStatus.VALIDATED
        submission.reviewed_by_id = reviewer_id
        submission.reviewed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(submission)
        return submission

    async def return_submission(
        self,
        submission_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        comment: str,
    ) -> GraduationSubmission:
        submission = await self.get_submission(submission_id)
        if not submission:
            raise ValueError("Submission not found.")
        if submission.status != GraduationStatus.SUBMITTED:
            raise ValueError("Only submitted entries can be returned.")

        submission.status = GraduationStatus.RETURNED
        submission.review_comment = comment
        submission.reviewed_by_id = reviewer_id
        submission.reviewed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(submission)
        return submission

    async def export_csv(
        self, department_id: Optional[uuid.UUID] = None
    ) -> str:
        query = (
            select(GraduationSubmission)
            .options(selectinload(GraduationSubmission.candidates))
        )
        if department_id:
            query = query.where(GraduationSubmission.department_id == department_id)

        result = await self.db.execute(query)
        submissions = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Programme", "Category", "Academic Year", "Student Number",
            "Name", "Academic Clearance", "Financial Clearance", "Status", "Issues",
        ])

        for sub in submissions:
            for candidate in sub.candidates:
                writer.writerow([
                    sub.programme_text or "",
                    sub.student_category,
                    sub.academic_year,
                    candidate.student_number,
                    candidate.name,
                    "Yes" if candidate.academic_clearance else "No" if candidate.academic_clearance is False else "Pending",
                    "Yes" if candidate.financial_clearance else "No" if candidate.financial_clearance is False else "Pending",
                    sub.status.value,
                    "; ".join(candidate.issues) if candidate.issues else "",
                ])

        return output.getvalue()
