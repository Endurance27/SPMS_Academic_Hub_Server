import csv
import io
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditCategory, AuditLog


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_logs(
        self,
        category: Optional[str] = None,
        actor_id: Optional[uuid.UUID] = None,
        entity_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 25,
    ) -> tuple[list[AuditLog], int]:
        query = select(AuditLog)
        count_query = select(func.count(AuditLog.id))

        conditions = []
        if category:
            conditions.append(AuditLog.category == category)
        if actor_id:
            conditions.append(AuditLog.user_id == actor_id)
        if entity_type:
            conditions.append(AuditLog.entity_type == entity_type)
        if from_date:
            conditions.append(AuditLog.created_at >= from_date)
        if to_date:
            conditions.append(AuditLog.created_at <= to_date)
        if search:
            conditions.append(
                or_(
                    AuditLog.summary.ilike(f"%{search}%"),
                    AuditLog.action.ilike(f"%{search}%"),
                    AuditLog.actor_name.ilike(f"%{search}%"),
                )
            )

        for cond in conditions:
            query = query.where(cond)
            count_query = count_query.where(cond)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        logs = list(result.scalars().all())

        return logs, total

    async def get_category_counts(self) -> dict[str, int]:
        counts = {}
        for cat in AuditCategory:
            result = await self.db.execute(
                select(func.count(AuditLog.id)).where(AuditLog.category == cat)
            )
            counts[cat.value] = result.scalar()

        total_result = await self.db.execute(select(func.count(AuditLog.id)))
        counts["All"] = total_result.scalar()
        return counts

    async def export_csv(
        self,
        category: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> str:
        query = select(AuditLog)
        if category:
            query = query.where(AuditLog.category == category)
        if from_date:
            query = query.where(AuditLog.created_at >= from_date)
        if to_date:
            query = query.where(AuditLog.created_at <= to_date)
        query = query.order_by(AuditLog.created_at.desc())

        result = await self.db.execute(query)
        logs = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Timestamp", "Actor", "Role", "Action", "Category",
            "Entity Type", "Summary", "IP Address",
        ])
        for log in logs:
            writer.writerow([
                log.created_at.isoformat() if log.created_at else "",
                log.actor_name,
                log.actor_role,
                log.action,
                log.category.value if log.category else "",
                log.entity_type or "",
                log.summary,
                log.ip_address or "",
            ])
        return output.getvalue()
