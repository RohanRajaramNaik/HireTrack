from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..engine.skills import ALIASES
from ..models import EducationLevel
from ..schemas import EducationLevelOut, ResultsOut, StatsOut
from ..security import ANY_ROLE, HIRING, require_roles
from ..services import dashboard_service
from ..services import match_service as svc

router = APIRouter(prefix="/api", tags=["matching"])


@router.post("/jobs/{job_id}/match", response_model=ResultsOut, dependencies=[Depends(require_roles(*HIRING))])
def run_match(job_id: int, db: Session = Depends(get_db)):
    return svc.run_match(db, job_id)


@router.get("/jobs/{job_id}/results", response_model=ResultsOut, dependencies=[Depends(require_roles(*HIRING))])
def results(job_id: int, db: Session = Depends(get_db)):
    return svc.get_results(db, job_id)


@router.get("/jobs/{job_id}/results.csv", dependencies=[Depends(require_roles(*HIRING))])
def results_csv(job_id: int, db: Session = Depends(get_db)):
    text, fname = svc.results_csv(db, job_id)
    # Prepend a BOM so Excel opens UTF-8 names correctly.
    return Response(
        content="﻿" + text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get(
    "/education-levels", response_model=list[EducationLevelOut], dependencies=[Depends(require_roles(*ANY_ROLE))]
)
def education_levels(db: Session = Depends(get_db)):
    return db.scalars(select(EducationLevel).order_by(EducationLevel.level_id)).all()


@router.get("/skill-aliases", response_model=dict[str, str], dependencies=[Depends(require_roles(*ANY_ROLE))])
def skill_aliases():
    """Alias -> canonical skill table, so the frontend's duplicate checks use the same rules as the server."""
    return ALIASES


@router.get("/stats", response_model=StatsOut, dependencies=[Depends(require_roles(*ANY_ROLE))])
def stats(db: Session = Depends(get_db)):
    return svc.stats(db)


@router.get("/dashboard", dependencies=[Depends(require_roles(*ANY_ROLE))])
def dashboard(db: Session = Depends(get_db)):
    """Key counts and chart data for the Dashboard screen."""
    return dashboard_service.dashboard(db)
