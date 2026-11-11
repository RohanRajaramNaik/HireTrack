from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import ApplicationIn, ApplicationOut, BulkApplicationIn, StageChangeIn
from ..security import ANY_ROLE, HIRING, require_roles
from ..services import pipeline_service as svc

router = APIRouter(prefix="/api/applications", tags=["pipeline"])

STAGE_PATTERN = "^(applied|screened|interview|offer|hired|rejected)$"


@router.get("", response_model=list[ApplicationOut], dependencies=[Depends(require_roles(*ANY_ROLE))])
def list_applications(
    job_id: int | None = Query(default=None, ge=1),
    stage: str | None = Query(default=None, pattern=STAGE_PATTERN),
    search: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
):
    return svc.list_applications(db, job_id, stage, search)


@router.get("/counts", dependencies=[Depends(require_roles(*ANY_ROLE))])
def counts(job_id: int | None = Query(default=None, ge=1), db: Session = Depends(get_db)):
    return svc.stage_counts(db, job_id)


@router.post("", response_model=ApplicationOut, status_code=201)
def create_application(
    data: ApplicationIn, db: Session = Depends(get_db), user: User = Depends(require_roles(*HIRING))
):
    return svc.to_out(svc.create_application(db, data, user), with_events=True)


@router.post("/bulk")
def bulk_add(data: BulkApplicationIn, db: Session = Depends(get_db), user: User = Depends(require_roles(*HIRING))):
    """Add a shortlist from the Results screen to a job's pipeline."""
    return svc.bulk_add(db, data, user)


@router.get("/{application_id}", response_model=ApplicationOut, dependencies=[Depends(require_roles(*ANY_ROLE))])
def get_application(application_id: int, db: Session = Depends(get_db)):
    return svc.to_out(svc.get_application(db, application_id), with_events=True)


@router.post("/{application_id}/stage", response_model=ApplicationOut)
def change_stage(
    application_id: int,
    data: StageChangeIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*HIRING)),
):
    return svc.to_out(svc.change_stage(db, application_id, data, user), with_events=True)


@router.delete("/{application_id}", status_code=204, dependencies=[Depends(require_roles(*HIRING))])
def delete_application(application_id: int, db: Session = Depends(get_db)):
    svc.delete_application(db, application_id)
    return Response(status_code=204)
