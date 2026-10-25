import uuid
from typing import Optional, List, Dict
from datetime import datetime

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.user import User, UserRole
from app.repositories.assessment_repository import AssessmentRepository


class AssessmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AssessmentRepository(db)

    async def list_assessments(
        self,
        status: Optional[str],
        scope: Optional[str],
        course_id: Optional[uuid.UUID],
        search: Optional[str],
        user: User
    ) -> tuple[List[Dict], Dict]:
        """List assessments with scoping"""
        assessments = await self.repo.list_filtered(
            status=status,
            scope=scope,
            course_id=course_id,
            search=search,
            user_role=user.role,
            user_department_id=user.department_id,
            user_id=user.id
        )

        result = [self._assessment_to_dict(a) for a in assessments]

        meta = {
            "Draft": sum(1 for a in assessments if a.status == AssessmentStatus.DRAFT),
            "Submitted": sum(1 for a in assessments if a.status == AssessmentStatus.SUBMITTED),
            "Upcoming": sum(1 for a in assessments if a.status == AssessmentStatus.UPCOMING),
            "Returned": sum(1 for a in assessments if a.status == AssessmentStatus.RETURNED),
            "All": len(assessments)
        }

        return result, meta

    async def create_assessment(self, data: Dict, save_as_draft: bool, user: User) -> Dict:
        """Create assessment"""
        # Determine status based on role and save_as_draft
        if save_as_draft:
            status = AssessmentStatus.DRAFT
        elif user.role == UserRole.SUPER:
            status = AssessmentStatus.UPCOMING
        else:
            status = AssessmentStatus.SUBMITTED

        assessment = Assessment(
            course_id=data.get("course_id"),
            course_code=data["course_code"],
            course_title=data["course_title"],
            department_id=data["department_id"],
            assessment_type=data["assessment_type"],
            delivery_mode=data["delivery_mode"],
            date=data["date"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            location=data["location"],
            venue_code=data.get("venue_code"),
            cohorts=data["cohorts"],
            status=status,
            scope=data["scope"],
            is_shared=data["is_shared"],
            created_by_id=user.id,
            created_by_role=user.role.value
        )

        self.db.add(assessment)
        await self.db.commit()
        await self.db.refresh(assessment)

        return self._assessment_to_dict(assessment)

    async def get_assessment(self, assessment_id: uuid.UUID, user: User) -> Optional[Dict]:
        """Get assessment by ID"""
        assessment = await self.repo.get_by_id(assessment_id)
        if not assessment:
            return None

        # Scope check
        if user.role == UserRole.DEPARTMENT and assessment.department_id != user.department_id:
            return None

        return self._assessment_to_dict(assessment)

    async def update_assessment(self, assessment_id: uuid.UUID, data: Dict, user: User) -> Dict:
        """Update assessment"""
        assessment = await self.repo.get_by_id(assessment_id)
        if not assessment:
            raise ValueError("Assessment not found")

        # Only creator can update draft/returned
        if assessment.created_by_id != user.id:
            raise ValueError("Can only update own assessments")

        for field, value in data.items():
            if hasattr(assessment, field) and value is not None:
                setattr(assessment, field, value)

        await self.db.commit()
        await self.db.refresh(assessment)

        return self._assessment_to_dict(assessment)

    async def submit_assessment(self, assessment_id: uuid.UUID, user: User) -> Dict:
        """Submit assessment for review"""
        assessment = await self.repo.get_by_id(assessment_id)
        if not assessment:
            raise ValueError("Assessment not found")

        if assessment.created_by_id != user.id:
            raise ValueError("Can only submit own assessments")

        if assessment.status not in (AssessmentStatus.DRAFT, AssessmentStatus.RETURNED):
            raise ValueError("Can only submit draft or returned assessments")

        assessment.status = AssessmentStatus.SUBMITTED
        await self.db.commit()
        await self.db.refresh(assessment)

        return self._assessment_to_dict(assessment)

    async def approve_assessment(self, assessment_id: uuid.UUID, user: User) -> Dict:
        """Approve assessment"""
        assessment = await self.repo.get_by_id(assessment_id)
        if not assessment:
            raise ValueError("Assessment not found")

        if assessment.created_by_id == user.id:
            raise ValueError("Cannot approve own assessment")

        assessment.status = AssessmentStatus.UPCOMING
        assessment.reviewed_by_id = user.id
        assessment.reviewed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(assessment)

        return self._assessment_to_dict(assessment)

    async def return_assessment(self, assessment_id: uuid.UUID, comment: str, user: User) -> Dict:
        """Return assessment with comment"""
        assessment = await self.repo.get_by_id(assessment_id)
        if not assessment:
            raise ValueError("Assessment not found")

        assessment.status = AssessmentStatus.RETURNED
        assessment.review_comment = comment
        assessment.reviewed_by_id = user.id
        assessment.reviewed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(assessment)

        return self._assessment_to_dict(assessment)

    async def cancel_assessment(self, assessment_id: uuid.UUID, user: User) -> Dict:
        """Cancel assessment"""
        assessment = await self.repo.get_by_id(assessment_id)
        if not assessment:
            raise ValueError("Assessment not found")

        if assessment.created_by_id != user.id and user.role != UserRole.SUPER:
            raise ValueError("Can only cancel own assessments")

        assessment.status = AssessmentStatus.CANCELLED
        await self.db.commit()
        await self.db.refresh(assessment)

        return self._assessment_to_dict(assessment)

    async def update_invigilators(self, assessment_id: uuid.UUID, invigilators: List[Dict], user: User) -> Dict:
        """Update assessment invigilators"""
        # Implementation would update AssessmentInvigilator table
        return {"assessment_id": str(assessment_id), "invigilators": invigilators}

    def _assessment_to_dict(self, assessment: Assessment) -> Dict:
        """Convert assessment to dict"""
        return {
            "id": str(assessment.id),
            "course_id": str(assessment.course_id) if assessment.course_id else None,
            "course_code": assessment.course_code,
            "course_title": assessment.course_title,
            "department_id": str(assessment.department_id),
            "assessment_type": assessment.assessment_type.value,
            "delivery_mode": assessment.delivery_mode.value,
            "date": assessment.date.isoformat() if assessment.date else None,
            "start_time": assessment.start_time,
            "end_time": assessment.end_time,
            "location": assessment.location,
            "venue_code": assessment.venue_code,
            "cohorts": assessment.cohorts or [],
            "status": assessment.status.value,
            "scope": assessment.scope.value,
            "is_shared": assessment.is_shared,
            "created_by_id": str(assessment.created_by_id),
            "created_by_role": assessment.created_by_role,
            "review_comment": assessment.review_comment,
            "reviewed_by_id": str(assessment.reviewed_by_id) if assessment.reviewed_by_id else None,
            "reviewed_at": assessment.reviewed_at.isoformat() if assessment.reviewed_at else None
        }
