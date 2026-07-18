"""用户管理路由（仅 admin 可访问）"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth import hash_password, get_current_user, require_admin
from app.schemas import UserCreate, UserUpdate, UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    q:        str   = Query("", description="按用户名模糊搜索"),
    role:     str   = Query("", description="筛选角色：admin / user"),
    is_active: int  = Query(-1, description="-1=全部 / 0=停用 / 1=启用"),
    db:       Session     = Depends(get_db),
    _:        User        = Depends(require_admin),
):
    query = db.query(User)
    if q:
        query = query.filter(User.username.like(f"%{q}%"))
    if role in ("admin", "user"):
        query = query.filter(User.role == role)
    if is_active in (0, 1):
        query = query.filter(User.is_active == is_active)
    return query.order_by(User.id.asc()).all()


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    db:   Session      = Depends(get_db),
    _:    User         = Depends(require_admin),
):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail=f"用户名「{body.username}」已存在")
    user = User(
        username      = body.username,
        password_hash = hash_password(body.password),
        role          = body.role,
        is_active     = 1 if body.is_active else 0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db:     Session = Depends(get_db),
    _:      User    = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body:    UserUpdate,
    db:      Session = Depends(get_db),
    admin:   User    = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 防止最后一个 admin 被降级 / 停用
    if body.role == "user" and user.role == "admin":
        admin_count = db.query(User).filter(User.role == "admin", User.is_active == 1).count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="至少保留一个启用中的管理员")
    if body.is_active is False and user.role == "admin" and user.is_active == 1:
        admin_count = db.query(User).filter(User.role == "admin", User.is_active == 1).count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="至少保留一个启用中的管理员")

    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = 1 if body.is_active else 0
    if body.password:
        user.password_hash = hash_password(body.password)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db:     Session = Depends(get_db),
    admin:  User    = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    if user.role == "admin" and user.is_active == 1:
        admin_count = db.query(User).filter(User.role == "admin", User.is_active == 1).count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="至少保留一个启用中的管理员")

    db.delete(user)
    db.commit()
    return {"ok": True, "message": f"用户「{user.username}」已删除"}
