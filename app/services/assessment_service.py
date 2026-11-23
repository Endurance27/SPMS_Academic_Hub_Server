import uuid
from typing import Optional, List, Dict
from datetime import datetime

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.course import Course
from app.models.registration import CourseRegistration, RegistrationStatus
from app.models.semester import Semester
from app.models.user import User, UserRole
from app.repositories.assessment_repository import AssessmentRepository
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService
from app.models.notification import NotificationCategory, NotificationPriority
from app.schemas.notification import NotificationCreate


class AssessmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AssessmentRepository(db)
        self.email_service = EmailService()
        self.notification_service = NotificationService(db)

    async def list_assessments(
        self,
        status: Optional[str],
        scope: Optional[str],
        course_id: Optional[uuid.UUID],
        search: Optional[str],
        user: User,
        skip: int = 0,
        limit: int = 25,
    ) -> tuple[List[Dict], int, Dict]:
        """List assessments with scoping. Returns (items, total, status_counts)."""
        assessments, total = await self.repo.list_filtered(
            status=status,
            scope=scope,
            course_id=course_id,
            search=search,
            user_role=user.role,
            user_department_id=user.department_id,
            user_id=user.id,
            skip=skip,
            limit=limit,
        )

        result = [self._assessment_to_dict(a) for a in assessments]

        counts = {
            "Draft": sum(1 for a in assessments if a.status == AssessmentStatus.DRAFT),
            "Submitted": sum(1 for a in assessments if a.status == AssessmentStatus.SUBMITTED),
            "Upcoming": sum(1 for a in assessments if a.status == AssessmentStatus.UPCOMING),
            "Returned": sum(1 for a in assessments if a.status == AssessmentStatus.RETURNED),
        }

        return result, total, counts

    async def create_assessment(self, data: Dict, save_as_draft: bool, user: User) -> Dict:
        """Create assessment.

        Access rules:
        - Lecturer: may only create for their own department and for courses
          they are assigned to teach.
        - Department admin: may only create for their own department.
        - Super admin: unrestricted.
        """
        # --- Parse date string → datetime ---
        from datetime import datetime as dt
        raw_date = data["date"]
        if isinstance(raw_date, str):
            try:
                parsed_date = dt.fromisoformat(raw_date)
            except ValueError:
                raise ValueError(f"Invalid date format '{raw_date}'. Use YYYY-MM-DD.")
        else:
            parsed_date = raw_date
        # --- Ownership validation ---
        if user.role == UserRole.LECTURER:
            # Must belong to the target department
            if str(data["department_id"]) != str(user.department_id):
                raise ValueError("You can only create assessments for your own department")

            # Must be the assigned lecturer for the course (when course_id is supplied)
            if data.get("course_id"):
                course_result = await self.db.execute(
                    select(Course).where(Course.id == data["course_id"])
                )
                course = course_result.scalar_one_or_none()
                if not course:
                    raise ValueError("Course not found")
                if str(course.lecturer_id) != str(user.id):
                    raise ValueError("You can only create assessments for courses you teach")

        elif user.role == UserRole.DEPARTMENT:
            if str(data["department_id"]) != str(user.department_id):
                raise ValueError("You can only create assessments for your own department")

        # --- Status based on role and save_as_draft flag ---
        if save_as_draft:
            status = AssessmentStatus.DRAFT
        elif user.role == UserRole.SUPER:
            # Super admin publishes directly — no review needed
            status = AssessmentStatus.UPCOMING
        elif user.role == UserRole.DEPARTMENT:
            # Department admin is the approver, so their own assessments
            # go straight to Upcoming (they are both creator and reviewer)
            status = AssessmentStatus.UPCOMING
        else:
            # Lecturers submit for departmental review
            status = AssessmentStatus.SUBMITTED

        assessment = Assessment(
            course_id=data.get("course_id"),
            course_code=data["course_code"],
            course_title=data["course_title"],
            department_id=data["department_id"],
            assessment_type=data["assessment_type"],
            delivery_mode=data["delivery_mode"],
            date=parsed_date,
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

        # Notify students immediately when assessment goes straight to Upcoming
        if status == AssessmentStatus.UPCOMING:
            await self._notify_enrolled_students(assessment)

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
        """Approve a submitted assessment.

        Only assessments in Submitted status can be approved.
        The approver cannot be the same person who created the assessment.
        On approval the status moves to Upcoming and enrolled students are notified.
        """
        assessment = await self.repo.get_by_id(assessment_id)
        if not assessment:
            raise ValueError("Assessment not found")

        if assessment.status != AssessmentStatus.SUBMITTED:
            raise ValueError(
                f"Only submitted assessments can be approved. "
                f"Current status: {assessment.status.value}"
            )

        if assessment.created_by_id == user.id:
            raise ValueError("Cannot approve your own assessment")

        assessment.status = AssessmentStatus.UPCOMING
        assessment.reviewed_by_id = user.id
        assessment.reviewed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(assessment)

        # Notify all enrolled students now that the assessment is confirmed
        await self._notify_enrolled_students(assessment)

        return self._assessment_to_dict(assessment)

    async def return_assessment(self, assessment_id: uuid.UUID, comment: str, user: User) -> Dict:
        """Return a submitted assessment with a review comment."""
        assessment = await self.repo.get_by_id(assessment_id)
        if not assessment:
            raise ValueError("Assessment not found")

        if assessment.status != AssessmentStatus.SUBMITTED:
            raise ValueError(
                f"Only submitted assessments can be returned. "
                f"Current status: {assessment.status.value}"
            )

        if not comment or not comment.strip():
            raise ValueError("A review comment is required when returning an assessment")

        assessment.status = AssessmentStatus.RETURNED
        assessment.review_comment = comment.strip()
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

    async def _notify_enrolled_students(self, assessment: Assessment) -> None:
        """Notify every student enrolled in the assessed course.

        Finds all active CourseRegistrations for the assessment's course in the
        current active semester, then sends each student both an in-app
        notification and an email.  Failures on individual sends are logged and
        swallowed so they never surface as an HTTP error to the caller.
        """
        from loguru import logger

        try:
            # Determine which students to notify
            students = await self._get_enrolled_students(assessment)
            if not students:
                return

            assessment_date = (
                assessment.date.strftime("%A, %d %B %Y")
                if assessment.date
                else "Date TBC"
            )
            time_range = f"{assessment.start_time} – {assessment.end_time}"
            assessment_type = (
                assessment.assessment_type.value
                if hasattr(assessment.assessment_type, "value")
                else str(assessment.assessment_type)
            )
            delivery_mode = (
                assessment.delivery_mode.value
                if hasattr(assessment.delivery_mode, "value")
                else str(assessment.delivery_mode)
            )
            _labels = {
                "IN_PERSON": "In-person",
                "ONLINE": "Online",
                "TAKE_HOME_ASSIGNMENT": "Take-home Assignment",
                "TERM_PAPER": "Term Paper",
            }
            delivery_mode = _labels.get(delivery_mode, delivery_mode)

            title = (
                f"{assessment_type}: {assessment.course_code}"
            )
            detail = (
                f"{assessment.course_title} — {assessment_type} scheduled for "
                f"{assessment_date} from {time_range} at {assessment.location}."
            )

            for student in students:
                # In-app notification (individual, not broadcast)
                try:
                    await self.notification_service.create_notification(
                        NotificationCreate(
                            recipient_id=student.id,
                            title=title,
                            detail=detail,
                            page="assessments",
                            category=NotificationCategory.ASSESSMENT,
                            priority=NotificationPriority.HIGH,
                            entity_type="assessment",
                            entity_id=assessment.id,
                        )
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to create in-app notification for student {} — {}",
                        student.id,
                        exc,
                    )

                # Email notification
                try:
                    await self.email_service.send_assessment_notification_email(
                        to_email=student.email,
                        student_name=student.name,
                        course_code=assessment.course_code,
                        course_title=assessment.course_title,
                        assessment_type=assessment_type,
                        delivery_mode=delivery_mode,
                        assessment_date=assessment_date,
                        start_time=assessment.start_time,
                        end_time=assessment.end_time,
                        location=assessment.location,
                        venue_code=assessment.venue_code,
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to send assessment email to {} — {}",
                        student.email,
                        exc,
                    )

        except Exception as exc:
            from loguru import logger as _logger
            _logger.error("Error in _notify_enrolled_students for assessment {} — {}", assessment.id, exc)

    async def _get_enrolled_students(self, assessment: Assessment) -> List[User]:
        """Return all active students registered for the assessment's course."""
        from app.models.user import UserStatus

        if assessment.course_id:
            # Look up via course registrations — most precise path
            active_semester_result = await self.db.execute(
                select(Semester).where(Semester.is_active == True)
            )
            active_semester = active_semester_result.scalar_one_or_none()
            semester_condition = (
                CourseRegistration.semester_id == active_semester.id
                if active_semester
                else True
            )

            result = await self.db.execute(
                select(User)
                .join(CourseRegistration, CourseRegistration.student_id == User.id)
                .where(
                    and_(
                        CourseRegistration.course_id == assessment.course_id,
                        CourseRegistration.status == RegistrationStatus.REGISTERED,
                        semester_condition,
                        User.status == UserStatus.ACTIVE,
                    )
                )
            )
            return list(result.scalars().all())

        # Fallback: use cohorts (programme_id + level) to find registered students
        if assessment.cohorts:
            from app.models.user import UserRole as URole
            students = []
            seen_ids: set = set()
            for cohort in assessment.cohorts:
                programme_id = cohort.get("programmeId") or cohort.get("programme_id")
                level = cohort.get("level")
                if not programme_id or not level:
                    continue
                result = await self.db.execute(
                    select(User).where(
                        and_(
                            User.programme_id == programme_id,
                            User.level == int(level),
                            User.role == URole.STUDENT,
                            User.status == UserStatus.ACTIVE,
                        )
                    )
                )
                for student in result.scalars().all():
                    if student.id not in seen_ids:
                        students.append(student)
                        seen_ids.add(student.id)
            return students

        return []

    def _assessment_to_dict(self, assessment: Assessment) -> Dict:
        """Convert assessment to dict"""
        _delivery_mode_labels = {
            "IN_PERSON": "In-person",
            "ONLINE": "Online",
            "TAKE_HOME_ASSIGNMENT": "Take-home Assignment",
            "TERM_PAPER": "Term Paper",
        }
        raw_mode = assessment.delivery_mode.value if hasattr(assessment.delivery_mode, "value") else str(assessment.delivery_mode)
        return {
            "id": str(assessment.id),
            "course_id": str(assessment.course_id) if assessment.course_id else None,
            "course_code": assessment.course_code,
            "course_title": assessment.course_title,
            "department_id": str(assessment.department_id),
            "assessment_type": assessment.assessment_type.value,
            "delivery_mode": raw_mode,
            "delivery_mode_label": _delivery_mode_labels.get(raw_mode, raw_mode),
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
