from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import LoginIn, PasswordChangeIn, TokenOut, UserIn, UserOut
from ..security import ADMIN, current_user, require_roles
from ..services import user_service as svc

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    return svc.login(db, data)


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.post("/auth/change-password", status_code=204)
def change_password(data: PasswordChangeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    svc.change_password(db, user, data)
    return Response(status_code=204)


@router.get("/users", response_model=list[UserOut], dependencies=[Depends(require_roles(*ADMIN))])
def list_users(db: Session = Depends(get_db)):
    return svc.list_users(db)


@router.post("/users", response_model=UserOut, status_code=201, dependencies=[Depends(require_roles(*ADMIN))])
def create_user(data: UserIn, db: Session = Depends(get_db)):
    return svc.create_user(db, data)


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int, data: UserIn, db: Session = Depends(get_db), acting: User = Depends(require_roles(*ADMIN))
):
    return svc.update_user(db, user_id, data, acting)
