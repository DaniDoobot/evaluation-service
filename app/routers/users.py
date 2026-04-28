from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AppUser
from app.schemas import (
    UserCreate,
    UserUpdate,
    UserPasswordUpdate,
    UserOut,
)
from app.services.auth_service import hash_password
from app.dependencies.auth import require_admin

router = APIRouter(prefix="/users", tags=["Users"])


VALID_ROLES = {"admin", "user", "visitor"}


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_admin),
):
    return (
        db.query(AppUser)
        .order_by(AppUser.created_at.desc())
        .all()
    )


@router.post("", response_model=UserOut)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_admin),
):
    existing = (
        db.query(AppUser)
        .filter(AppUser.email == payload.email)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un usuario con ese email",
        )

    if payload.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail="Rol no válido. Usa admin, user o visitor.",
        )

    user = AppUser(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
        is_archived=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_admin),
):
    user = (
        db.query(AppUser)
        .filter(AppUser.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    data = payload.model_dump(exclude_unset=True)

    if "role" in data and data["role"] not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail="Rol no válido. Usa admin, user o visitor.",
        )

    if "email" in data:
        existing = (
            db.query(AppUser)
            .filter(AppUser.email == data["email"], AppUser.id != user_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Ya existe otro usuario con ese email",
            )

    for field, value in data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return user


@router.post("/{user_id}/archive", response_model=UserOut)
def archive_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_admin),
):
    user = (
        db.query(AppUser)
        .filter(AppUser.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="No puedes archivarte a ti mismo",
        )

    user.is_archived = True
    user.is_active = False

    db.commit()
    db.refresh(user)

    return user


@router.post("/{user_id}/unarchive", response_model=UserOut)
def unarchive_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_admin),
):
    user = (
        db.query(AppUser)
        .filter(AppUser.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.is_archived = False
    user.is_active = True

    db.commit()
    db.refresh(user)

    return user


@router.post("/{user_id}/reset-password", response_model=UserOut)
def reset_user_password(
    user_id: int,
    payload: UserPasswordUpdate,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_admin),
):
    user = (
        db.query(AppUser)
        .filter(AppUser.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.password_hash = hash_password(payload.password)

    db.commit()
    db.refresh(user)

    return user
