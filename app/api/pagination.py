from dataclasses import dataclass
from typing import Optional

from fastapi import Query


@dataclass
class PaginationParams:
    page: int
    page_size: int
    sort_by: Optional[str]
    order: str

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size


def get_pagination(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order"),
) -> PaginationParams:
    return PaginationParams(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        order=order,
    )
