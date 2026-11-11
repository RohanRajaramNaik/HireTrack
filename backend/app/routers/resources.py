from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import AllocationIn, AllocationOut, ProjectIn, ProjectOut, StaffIn, StaffOut
from ..security import ANY_ROLE, RESOURCING, require_roles
from ..services import resource_service as svc

router = APIRouter(prefix="/api", tags=["resources"])
READ = [Depends(require_roles(*ANY_ROLE))]
WRITE = [Depends(require_roles(*RESOURCING))]


# ---- staff
@router.get("/staff", response_model=list[StaffOut], dependencies=READ)
def list_staff(
    search: str | None = Query(default=None, max_length=100),
    band: str | None = Query(default=None, pattern="^(bench|light|healthy|full|inactive)$"),
    db: Session = Depends(get_db),
):
    return svc.list_staff(db, search, band)


@router.post("/staff", response_model=StaffOut, status_code=201, dependencies=WRITE)
def create_staff(data: StaffIn, db: Session = Depends(get_db)):
    return svc.staff_to_out(svc.create_staff(db, data))


@router.get("/staff/{staff_id}", response_model=StaffOut, dependencies=READ)
def get_staff(staff_id: int, db: Session = Depends(get_db)):
    return svc.staff_to_out(svc.get_staff(db, staff_id))


@router.put("/staff/{staff_id}", response_model=StaffOut, dependencies=WRITE)
def update_staff(staff_id: int, data: StaffIn, db: Session = Depends(get_db)):
    return svc.staff_to_out(svc.update_staff(db, staff_id, data))


@router.delete("/staff/{staff_id}", status_code=204, dependencies=WRITE)
def delete_staff(staff_id: int, db: Session = Depends(get_db)):
    svc.delete_staff(db, staff_id)
    return Response(status_code=204)


@router.get("/utilisation", dependencies=READ)
def utilisation(db: Session = Depends(get_db)):
    return svc.utilisation_summary(db)


# ---- projects
@router.get("/projects", response_model=list[ProjectOut], dependencies=READ)
def list_projects(
    status: str | None = Query(default=None, pattern="^(planned|active|on_hold|completed)$"),
    db: Session = Depends(get_db),
):
    return svc.list_projects(db, status)


@router.post("/projects", response_model=ProjectOut, status_code=201, dependencies=WRITE)
def create_project(data: ProjectIn, db: Session = Depends(get_db)):
    return svc.project_to_out(svc.create_project(db, data), with_allocations=True)


@router.get("/projects/{project_id}", response_model=ProjectOut, dependencies=READ)
def get_project(project_id: int, db: Session = Depends(get_db)):
    return svc.project_to_out(svc.get_project(db, project_id), with_allocations=True)


@router.put("/projects/{project_id}", response_model=ProjectOut, dependencies=WRITE)
def update_project(project_id: int, data: ProjectIn, db: Session = Depends(get_db)):
    return svc.project_to_out(svc.update_project(db, project_id, data), with_allocations=True)


@router.delete("/projects/{project_id}", status_code=204, dependencies=WRITE)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    svc.delete_project(db, project_id)
    return Response(status_code=204)


# ---- allocations
@router.get("/allocations", response_model=list[AllocationOut], dependencies=READ)
def list_allocations(
    staff_id: int | None = Query(default=None, ge=1),
    project_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    return svc.list_allocations(db, staff_id, project_id)


@router.post("/allocations", response_model=AllocationOut, status_code=201, dependencies=WRITE)
def create_allocation(data: AllocationIn, db: Session = Depends(get_db)):
    return svc.alloc_to_out(svc.create_allocation(db, data))


@router.put("/allocations/{allocation_id}", response_model=AllocationOut, dependencies=WRITE)
def update_allocation(allocation_id: int, data: AllocationIn, db: Session = Depends(get_db)):
    return svc.alloc_to_out(svc.update_allocation(db, allocation_id, data))


@router.delete("/allocations/{allocation_id}", status_code=204, dependencies=WRITE)
def delete_allocation(allocation_id: int, db: Session = Depends(get_db)):
    svc.delete_allocation(db, allocation_id)
    return Response(status_code=204)
