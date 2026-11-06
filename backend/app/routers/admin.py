from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import BackupOut
from ..security import require_admin
from ..services import backup_service, seed_service

router = APIRouter(prefix="/api", tags=["admin"])


@router.post("/admin/verify", dependencies=[Depends(require_admin)])
def verify():
    """Lets the Admin screen confirm a passcode before enabling actions."""
    return {"ok": True}


@router.post("/admin/seed", dependencies=[Depends(require_admin)])
def seed(db: Session = Depends(get_db)):
    return seed_service.load_demo(db, backup=True)


@router.post("/admin/seed-large", dependencies=[Depends(require_admin)])
def seed_large(db: Session = Depends(get_db)):
    return seed_service.load_large(db)


@router.get("/admin/backups", response_model=list[BackupOut], dependencies=[Depends(require_admin)])
def backups():
    return backup_service.list_backups()


@router.post("/admin/backups", response_model=BackupOut, status_code=201, dependencies=[Depends(require_admin)])
def backup_now():
    return backup_service.create_backup("manual")


@router.post("/admin/backups/{file}/restore", dependencies=[Depends(require_admin)])
def restore(file: str):
    out = backup_service.restore_backup(file)
    seed_service.warm_embeddings_async()
    return out


@router.post("/demo/start")
def demo_start(db: Session = Depends(get_db)):
    """Guided demo: loads demo data only if the database is EMPTY (non-destructive,
    so no passcode is needed), then returns the Cloud Data Engineer job id."""
    return seed_service.demo_start(db)
