"""Administration: data loading and backups.

Viewing and creating backups needs the Admin role. Anything that replaces data
(loading a dataset, restoring a backup) also needs the admin's password
re-entered in the X-Confirm-Password header.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import BackupOut
from ..security import ADMIN, HIRING, require_confirmed_admin, require_roles
from ..services import backup_service, seed_service

router = APIRouter(prefix="/api", tags=["admin"])


@router.post("/admin/verify", dependencies=[Depends(require_confirmed_admin)])
def verify():
    """Lets the Admin screen confirm the password before enabling destructive actions."""
    return {"ok": True}


@router.post("/admin/seed", dependencies=[Depends(require_confirmed_admin)])
def seed(db: Session = Depends(get_db)):
    """Reset to the small demo dataset (18 candidates, 3 jobs)."""
    return seed_service.load_demo(db, backup=True)


@router.post("/admin/seed-full", dependencies=[Depends(require_confirmed_admin)])
def seed_full(db: Session = Depends(get_db)):
    """Reset to the full dataset (600 candidates, 33 jobs, pipeline, staff, projects)."""
    return seed_service.load_full(db, backup=True)


@router.post("/admin/seed-large", dependencies=[Depends(require_confirmed_admin)])
def seed_large(db: Session = Depends(get_db)):
    """The full dataset plus about 2,000 extra generated candidates (scale testing)."""
    return seed_service.load_large(db)


@router.get("/admin/backups", response_model=list[BackupOut], dependencies=[Depends(require_roles(*ADMIN))])
def backups():
    return backup_service.list_backups()


@router.post(
    "/admin/backups", response_model=BackupOut, status_code=201, dependencies=[Depends(require_roles(*ADMIN))]
)
def backup_now():
    return backup_service.create_backup("manual")


@router.post("/admin/backups/{file}/restore", dependencies=[Depends(require_confirmed_admin)])
def restore(file: str):
    out = backup_service.restore_backup(file)
    seed_service.warm_embeddings_async()
    return out


@router.post("/demo/start", dependencies=[Depends(require_roles(*HIRING))])
def demo_start(db: Session = Depends(get_db)):
    """Guided demo: loads demo data only if the database is EMPTY (non-destructive),
    then returns the Cloud Data Engineer job id."""
    return seed_service.demo_start(db)
