from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Clash:
    kind: str  # level, not-free, venue-taken, pending-venue, student, lecturer, capacity
    severity: str  # danger, warning
    message: str
    other_request_id: Optional[str] = None
    other_schedule_item_id: Optional[str] = None


class ClashDetector:
    """Detect scheduling conflicts"""
    
    @staticmethod
    def overlap(a: Dict, b: Dict) -> bool:
        """Check if two placements overlap in time"""
        return (
            a["day"] == b["day"] and
            a["start_period"] < b["start_period"] + b["period_count"] and
            b["start_period"] < a["start_period"] + a["period_count"]
        )
    
    @staticmethod
    def detect_clashes(
        placement: Dict[str, Any],
        free_cells: set,
        other_requests: List[Dict],
        schedule_items: List[Dict],
        assessments: List[Dict],
        course: Dict,
        capacity_tolerance: int = 0
    ) -> List[Clash]:
        """Detect all clashes for a placement"""
        clashes = []
        
        # 1. Level clash (danger)
        if "cohorts" in course:
            placement_level = placement.get("level")
            for cohort in course["cohorts"]:
                if cohort["level"] != placement_level:
                    clashes.append(Clash(
                        kind="level",
                        severity="danger",
                        message=f"{course['code']} is taken by Level {cohort['level']} students, but this FREE slot is on the Level {placement_level} timetable"
                    ))
        
        # 2. Not-free check (danger, blocking)
        for period in range(placement["start_period"], placement["start_period"] + placement["period_count"]):
            cell_key = f"{placement['day']}|{period}|{placement['venue_code']}"
            if cell_key not in free_cells:
                clashes.append(Clash(
                    kind="not-free",
                    severity="danger",
                    message=f"{placement['venue_code']} is not FREE for this slot in the active master timetable"
                ))
                return clashes  # Block on not-free
        
        # 3. Check against other requests
        for other in other_requests:
            if other["id"] == placement.get("id"):
                continue
            if other["status"] not in ("Pending", "Approved"):
                continue
            
            if ClashDetector.overlap(placement, other):
                if placement["venue_code"] == other["venue_code"]:
                    if other["status"] == "Approved":
                        clashes.append(Clash(
                            kind="venue-taken",
                            severity="danger",
                            message=f"{placement['venue_code']} is already allocated to {other['course_code']} for this slot",
                            other_request_id=other["id"]
                        ))
                    else:
                        dept = other.get("department_code", "another department")
                        msg = f"Requested by {dept} for {other['course_code']}"
                        if other.get("department_id") == placement.get("department_id"):
                            msg = f"Your department already requested {other['course_code']} for this slot"
                        clashes.append(Clash(
                            kind="pending-venue",
                            severity="warning",
                            message=msg,
                            other_request_id=other["id"]
                        ))
                
                # Student cohort clash
                if placement.get("course_id") != other.get("course_id"):
                    if ClashDetector._has_shared_cohort(course, other.get("course", {})):
                        status_suffix = ", pending approval" if other["status"] == "Pending" else ""
                        clashes.append(Clash(
                            kind="student",
                            severity="danger",
                            message=f"Same student cohort also enrolled in {other['course_code']}{status_suffix}",
                            other_request_id=other["id"]
                        ))
                
                # Lecturer clash
                if course.get("lecturer_id") and other.get("lecturer_id"):
                    if course["lecturer_id"] == other["lecturer_id"]:
                        lecturer_name = course.get("lecturer_name", "the lecturer")
                        clashes.append(Clash(
                            kind="lecturer",
                            severity="danger",
                            message=f"{lecturer_name} also teaches {other['course_code']} at this time",
                            other_request_id=other["id"]
                        ))
        
        # 4. Capacity check (warning)
        if course.get("student_count") and placement.get("venue_capacity"):
            tolerance = capacity_tolerance / 100
            max_capacity = placement["venue_capacity"] * (1 + tolerance)
            if course["student_count"] > max_capacity:
                clashes.append(Clash(
                    kind="capacity",
                    severity="warning",
                    message=f"{course['code']} has {course['student_count']} students but {placement['venue_code']} seats {placement['venue_capacity']}"
                ))
        
        return clashes
    
    @staticmethod
    def _has_shared_cohort(course_a: Dict, course_b: Dict) -> bool:
        """Check if two courses share a student cohort"""
        cohorts_a = {f"{c['programme_id']}|{c['level']}" for c in course_a.get("cohorts", [])}
        cohorts_b = {f"{c['programme_id']}|{c['level']}" for c in course_b.get("cohorts", [])}
        return bool(cohorts_a & cohorts_b)
