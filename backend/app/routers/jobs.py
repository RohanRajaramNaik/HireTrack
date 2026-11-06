from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import JobIn, JobOut
from ..services import job_service as svc

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    return svc.list_jobs(db)


@router.post("", response_model=JobOut, status_code=201)
def create_job(data: JobIn, db: Session = Depends(get_db)):
    return svc.job_out(db, svc.create_job(db, data))


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    return svc.job_out(db, svc.get_job(db, job_id))


@router.put("/{job_id}", response_model=JobOut)
def update_job(job_id: int, data: JobIn, db: Session = Depends(get_db)):
    return svc.job_out(db, svc.update_job(db, job_id, data))


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    svc.delete_job(db, job_id)
    return Response(status_code=204)
