from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import CandidateIn, CandidateListOut, CandidateOut, ImportOut
from ..security import ANY_ROLE, HIRING, require_roles
from ..services import candidate_service as svc
from ..services import import_service

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.get("", response_model=CandidateListOut, dependencies=[Depends(require_roles(*ANY_ROLE))])
def list_candidates(
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=5000),
    sort: str = Query(default="name", pattern="^(name|years|level|created)$"),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    items, total = svc.list_candidates(db, search, page, page_size, sort, order)
    return CandidateListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=CandidateOut, status_code=201, dependencies=[Depends(require_roles(*HIRING))])
def create_candidate(data: CandidateIn, db: Session = Depends(get_db)):
    return svc.to_out(svc.create_candidate(db, data))


@router.get("/import/template", dependencies=[Depends(require_roles(*HIRING))])
def import_template():
    """CSV template with the expected columns and one example row."""
    return Response(
        content="﻿" + import_service.template_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="hiretrack-candidate-import-template.csv"'},
    )


@router.post("/import", response_model=ImportOut, dependencies=[Depends(require_roles(*HIRING))])
async def import_candidates(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Bulk import from .csv or .xlsx. Valid rows are saved; invalid rows are reported."""
    content = await file.read()
    return import_service.import_candidates(db, file.filename or "", content)


@router.post("/parse-cv", dependencies=[Depends(require_roles(*HIRING))])
async def parse_cv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Extract text, skills and contact details from a CV to pre-fill the form (nothing is saved)."""
    content = await file.read()
    return import_service.extract_cv(db, file.filename or "", content)


@router.get("/{candidate_id}", response_model=CandidateOut, dependencies=[Depends(require_roles(*ANY_ROLE))])
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    return svc.to_out(svc.get_candidate(db, candidate_id))


@router.put("/{candidate_id}", response_model=CandidateOut, dependencies=[Depends(require_roles(*HIRING))])
def update_candidate(candidate_id: int, data: CandidateIn, db: Session = Depends(get_db)):
    return svc.to_out(svc.update_candidate(db, candidate_id, data))


@router.delete("/{candidate_id}", status_code=204, dependencies=[Depends(require_roles(*HIRING))])
def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    svc.delete_candidate(db, candidate_id)
    return Response(status_code=204)
