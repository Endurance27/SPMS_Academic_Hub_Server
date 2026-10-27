from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models.user import User, UserRole
from app.schemas.imports import (
    ImportListResponse,
    ImportResponse,
    ImportRowListResponse,
    ImportRowResponse,
)
from app.services.import_service import ImportService

router = APIRouter()


@router.post(
    "/students",
    response_model=ImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_students(
    file: UploadFile = File(...),
    student_category: str = Form(...),
    academic_year: str = Form(...),
    programme_id: Optional[UUID] = Form(None),
    level: Optional[int] = Form(None),
    current_user: User = Depends(require_permission("imports.manage")),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.department_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department context required.",
        )

    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a CSV file so its columns and rows can be validated.",
        )

    service = ImportService(db)
    content = await file.read()

    try:
        import_obj = await service.create_student_import(
            file_content=content,
            filename=file.filename,
            department_id=current_user.department_id,
            student_category=student_category,
            academic_year=academic_year,
            programme_id=programme_id,
            level=level,
            created_by_id=current_user.id,
        )
        return ImportResponse.model_validate(import_obj)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.post(
    "/course-roster",
    response_model=ImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_course_roster(
    file: UploadFile = File(...),
    course_id: UUID = Form(...),
    student_category: str = Form(...),
    academic_year: str = Form(...),
    semester_id: UUID = Form(...),
    current_user: User = Depends(require_permission("imports.manage")),
    db: AsyncSession = Depends(get_db),
):
    dept_id = current_user.department_id
    if not dept_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department context required.",
        )

    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a CSV file so its columns and rows can be validated.",
        )

    service = ImportService(db)
    content = await file.read()

    try:
        import_obj = await service.create_course_roster_import(
            file_content=content,
            filename=file.filename,
            course_id=course_id,
            department_id=dept_id,
            student_category=student_category,
            academic_year=academic_year,
            semester_id=semester_id,
            created_by_id=current_user.id,
        )
        return ImportResponse.model_validate(import_obj)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.get("", response_model=ImportListResponse)
async def list_imports(
    kind: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_permission("imports.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ImportService(db)

    dept_id = None
    if current_user.role == UserRole.DEPARTMENT:
        dept_id = current_user.department_id

    skip = (page - 1) * page_size
    imports = await service.list_imports(
        kind=kind, department_id=dept_id, skip=skip, limit=page_size
    )

    return ImportListResponse(
        data=[ImportResponse.model_validate(i) for i in imports],
        meta={"page": page, "pageSize": page_size},
    )


@router.get("/{import_id}", response_model=ImportResponse)
async def get_import(
    import_id: UUID,
    current_user: User = Depends(require_permission("imports.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ImportService(db)
    import_obj = await service.get_import(import_id)

    if not import_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Import not found"
        )

    return ImportResponse.model_validate(import_obj)


@router.get("/{import_id}/rows", response_model=ImportRowListResponse)
async def get_import_rows(
    import_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_permission("imports.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ImportService(db)
    skip = (page - 1) * page_size
    rows = await service.get_import_rows(import_id, skip=skip, limit=page_size)

    return ImportRowListResponse(
        data=[ImportRowResponse.model_validate(r) for r in rows],
        meta={"page": page, "pageSize": page_size},
    )
