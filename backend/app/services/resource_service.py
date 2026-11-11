"""Resource allocation: staff pool, projects, allocations and utilisation.

Utilisation is worked out for a reference day (today by default) from the
allocations that cover that day on projects that are planned or active.
Allocations on completed or on-hold projects do not count towards anyone's load.
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..engine.allocation import Booking, check_new_booking, load_on, utilisation_band
from ..errors import AppError, Conflict, NotFound
from ..models import Allocation, Project, StaffMember
from ..schemas import AllocationIn, AllocationOut, ProjectIn, ProjectOut, StaffIn, StaffOut

log = logging.getLogger("hiretrack.resources")

COUNTING = ("planned", "active")  # project statuses that use up a person's time


def today() -> date:
    return date.today()


# ------------------------------------------------------------------- staff
def _bookings(allocs: list[Allocation]) -> list[Booking]:
    return [
        Booking(a.allocation_percent, a.start_date, a.end_date, a.allocation_id)
        for a in allocs
        if a.project.status in COUNTING
    ]


def staff_to_out(s: StaffMember, on: date | None = None) -> StaffOut:
    on = on or today()
    load = load_on(_bookings(s.allocations), on)
    current = sorted(
        {a.project.name for a in s.allocations if a.start_date <= on <= a.end_date and a.project.status in COUNTING}
    )
    return StaffOut(
        staff_id=s.staff_id,
        full_name=s.full_name,
        email=s.email,
        role_title=s.role_title,
        location=s.location,
        source=s.source,
        candidate_id=s.candidate_id,
        is_active=s.is_active,
        utilisation=load,
        band=utilisation_band(load) if s.is_active else "inactive",
        current_projects=current,
    )


def _staff_query():
    return select(StaffMember).options(selectinload(StaffMember.allocations).joinedload(Allocation.project))


def list_staff(db: Session, search: str | None = None, band: str | None = None, on: date | None = None) -> list[StaffOut]:
    q = _staff_query().order_by(func.lower(StaffMember.full_name))
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        q = q.where(func.lower(StaffMember.full_name).like(term) | func.lower(StaffMember.role_title).like(term))
    rows = [staff_to_out(s, on) for s in db.scalars(q).unique().all()]
    if band:
        rows = [r for r in rows if r.band == band]
    return rows


def get_staff(db: Session, staff_id: int) -> StaffMember:
    s = db.scalar(_staff_query().where(StaffMember.staff_id == staff_id))
    if s is None:
        raise NotFound(f"Staff member {staff_id} not found")
    return s


def create_staff(db: Session, data: StaffIn) -> StaffMember:
    s = StaffMember(
        full_name=data.full_name,
        email=data.email,
        role_title=data.role_title,
        location=data.location or None,
        is_active=data.is_active,
        source="existing",
    )
    db.add(s)
    db.commit()
    log.info("Created staff id=%s", s.staff_id)
    return get_staff(db, s.staff_id)


def update_staff(db: Session, staff_id: int, data: StaffIn) -> StaffMember:
    s = get_staff(db, staff_id)
    s.full_name = data.full_name
    s.email = data.email
    s.role_title = data.role_title
    s.location = data.location or None
    s.is_active = data.is_active
    db.commit()
    db.expire_all()
    return get_staff(db, staff_id)


def delete_staff(db: Session, staff_id: int) -> None:
    s = get_staff(db, staff_id)
    db.delete(s)
    db.commit()
    log.info("Deleted staff id=%s", staff_id)


# ---------------------------------------------------------------- projects
def alloc_to_out(a: Allocation, on: date | None = None) -> AllocationOut:
    on = on or today()
    return AllocationOut(
        allocation_id=a.allocation_id,
        staff_id=a.staff_id,
        staff_name=a.staff.full_name,
        staff_role=a.staff.role_title,
        project_id=a.project_id,
        project_name=a.project.name,
        role_on_project=a.role_on_project,
        allocation_percent=a.allocation_percent,
        start_date=a.start_date,
        end_date=a.end_date,
        is_current=a.start_date <= on <= a.end_date,
    )


def project_to_out(p: Project, with_allocations: bool = False) -> ProjectOut:
    on = today()
    current = [a for a in p.allocations if a.start_date <= on <= a.end_date]
    return ProjectOut(
        project_id=p.project_id,
        name=p.name,
        client=p.client,
        description=p.description,
        start_date=p.start_date,
        end_date=p.end_date,
        status=p.status,
        team_size=len({a.staff_id for a in p.allocations}),
        allocated_percent=sum(a.allocation_percent for a in current),
        allocations=(
            [alloc_to_out(a, on) for a in sorted(p.allocations, key=lambda a: (a.start_date, a.staff.full_name))]
            if with_allocations
            else None
        ),
    )


def _project_query():
    return select(Project).options(selectinload(Project.allocations).joinedload(Allocation.staff))


def list_projects(db: Session, status: str | None = None) -> list[ProjectOut]:
    q = _project_query().order_by(Project.start_date.desc(), Project.name)
    if status:
        q = q.where(Project.status == status)
    return [project_to_out(p) for p in db.scalars(q).unique().all()]


def get_project(db: Session, project_id: int) -> Project:
    p = db.scalar(_project_query().where(Project.project_id == project_id))
    if p is None:
        raise NotFound(f"Project {project_id} not found")
    return p


def _name_taken(db: Session, name: str, except_id: int | None = None) -> bool:
    q = select(Project.project_id).where(func.lower(Project.name) == name.lower())
    if except_id is not None:
        q = q.where(Project.project_id != except_id)
    return db.scalar(q) is not None


def create_project(db: Session, data: ProjectIn) -> Project:
    if _name_taken(db, data.name):
        raise Conflict("A project with this name already exists", field="name")
    p = Project(**data.model_dump())
    db.add(p)
    db.commit()
    log.info("Created project id=%s", p.project_id)
    return get_project(db, p.project_id)


def update_project(db: Session, project_id: int, data: ProjectIn) -> Project:
    p = get_project(db, project_id)
    if _name_taken(db, data.name, except_id=project_id):
        raise Conflict("A project with this name already exists", field="name")
    outside = [a for a in p.allocations if a.start_date < data.start_date or a.end_date > data.end_date]
    if outside:
        raise AppError(
            f"{len(outside)} allocation(s) fall outside the new dates. Change or remove them first.",
            field="start_date",
            status_code=422,
        )
    for k, v in data.model_dump().items():
        setattr(p, k, v)
    db.commit()
    db.expire_all()
    return get_project(db, project_id)


def delete_project(db: Session, project_id: int) -> None:
    p = get_project(db, project_id)
    db.delete(p)
    db.commit()
    log.info("Deleted project id=%s", project_id)


# ------------------------------------------------------------- allocations
def _validate_allocation(db: Session, data: AllocationIn, ignore_id: int | None = None) -> tuple[StaffMember, Project]:
    staff = get_staff(db, data.staff_id)
    project = get_project(db, data.project_id)
    if not staff.is_active:
        raise AppError("This staff member is inactive and cannot be allocated", field="staff_id", status_code=422)
    if project.status == "completed":
        raise AppError("This project is completed; allocations cannot be added", field="project_id", status_code=422)
    if data.start_date < project.start_date or data.end_date > project.end_date:
        raise AppError(
            f"Dates must fall within the project ({project.start_date:%d %b %Y} to {project.end_date:%d %b %Y})",
            field="start_date",
            status_code=422,
        )
    if project.status in COUNTING:
        try:
            check_new_booking(
                _bookings(staff.allocations),
                Booking(data.allocation_percent, data.start_date, data.end_date),
                ignore_id=ignore_id,
            )
        except ValueError as exc:
            raise AppError(str(exc), field="allocation_percent", status_code=422) from exc
    return staff, project


def get_allocation(db: Session, allocation_id: int) -> Allocation:
    a = db.get(Allocation, allocation_id)
    if a is None:
        raise NotFound(f"Allocation {allocation_id} not found")
    return a


def create_allocation(db: Session, data: AllocationIn) -> Allocation:
    _validate_allocation(db, data)
    a = Allocation(**data.model_dump())
    db.add(a)
    db.commit()
    log.info("Allocated staff id=%s to project id=%s at %s%%", data.staff_id, data.project_id, data.allocation_percent)
    db.expire_all()
    return get_allocation(db, a.allocation_id)


def update_allocation(db: Session, allocation_id: int, data: AllocationIn) -> Allocation:
    a = get_allocation(db, allocation_id)
    _validate_allocation(db, data, ignore_id=allocation_id)
    for k, v in data.model_dump().items():
        setattr(a, k, v)
    db.commit()
    db.expire_all()
    return get_allocation(db, allocation_id)


def delete_allocation(db: Session, allocation_id: int) -> None:
    a = get_allocation(db, allocation_id)
    db.delete(a)
    db.commit()
    log.info("Deleted allocation id=%s", allocation_id)


def list_allocations(db: Session, staff_id: int | None = None, project_id: int | None = None) -> list[AllocationOut]:
    q = select(Allocation).order_by(Allocation.start_date.desc())
    if staff_id is not None:
        q = q.where(Allocation.staff_id == staff_id)
    if project_id is not None:
        q = q.where(Allocation.project_id == project_id)
    return [alloc_to_out(a) for a in db.scalars(q).unique().all()]


# --------------------------------------------------------------- summary
def utilisation_summary(db: Session, on: date | None = None) -> dict:
    staff = [s for s in list_staff(db, on=on) if s.is_active]
    bands = {"bench": 0, "light": 0, "healthy": 0, "full": 0}
    for s in staff:
        bands[s.band] += 1
    avg = round(sum(s.utilisation for s in staff) / len(staff), 1) if staff else None
    return {"active_staff": len(staff), "average_utilisation": avg, "bands": bands}
