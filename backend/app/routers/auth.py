"""认证路由：登录 / 登出 / 当前用户信息"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth import (
    verify_password, hash_password, create_access_token, get_current_user,
)
from app.schemas import LoginRequest, LoginResponse, UserOut, ChangePasswordRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """JSON 登录（前端用）"""
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="账号或密码错误")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码错误")

    user.last_login_at = datetime.utcnow()
    db.commit()

    token = create_access_token(user.id, user.username, user.role)
    return LoginResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login/form", response_model=LoginResponse, include_in_schema=False)
def login_form(
    form: OAuth2PasswordRequestForm = Depends(),
    db:   Session                  = Depends(get_db),
):
    """表单登录（Swagger Authorize 按钮用）"""
    return login(LoginRequest(username=form.username, password=form.password), db)


@router.post("/logout")
def logout(current: User = Depends(get_current_user)):
    """登出（前端清除 token 即可，这里只做占位）"""
    return {"ok": True, "message": f"再见，{current.username}"}


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    return current


@router.post("/change-password")
def change_password(
    body:    ChangePasswordRequest,
    current: User        = Depends(get_current_user),
    db:     Session      = Depends(get_db),
):
    """改自己密码"""
    if not verify_password(body.old_password, current.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    if body.old_password == body.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")

    current.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True, "message": "密码已更新"}
