import math
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int
    pageSize: int
    total: int
    totalPages: int
    hasNext: bool
    hasPrev: bool
    sortBy: Optional[str] = None
    order: Optional[str] = None

    @classmethod
    def build(
        cls,
        page: int,
        page_size: int,
        total: int,
        sort_by: Optional[str] = None,
        order: Optional[str] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        total_pages = math.ceil(total / page_size) if page_size else 0
        meta = {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": total_pages,
            "hasNext": page < total_pages,
            "hasPrev": page > 1,
        }
        if sort_by:
            meta["sortBy"] = sort_by
            meta["order"] = order or "asc"
        if extra:
            meta.update(extra)
        return meta
