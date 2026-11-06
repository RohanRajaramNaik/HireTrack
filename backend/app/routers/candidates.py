from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import CandidateIn, CandidateListOut, CandidateOut
from ..services import candidate_service as svc

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.get("", response_model=CandidateListOut)
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


@router.post("", response_model=CandidateOut, status_code=201)
def create_candidate(data: CandidateIn, db: Session = Depends(get_db)):
    return svc.to_out(svc.create_candidate(db, data))


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    return svc.to_out(svc.get_candidate(db, candidate_id))


@router.put("/{candidate_id}", response_model=CandidateOut)
def update_candidate(candidate_id: int, data: CandidateIn, db: Session = Depends(get_db)):
    return svc.to_out(svc.update_candidate(db, candidate_id, data))


@router.delete("/{candidate_id}", status_code=204)
def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    svc.delete_candidate(db, candidate_id)
    return Response(status_code=204)
