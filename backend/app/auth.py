"""认证工具：密码哈希 + JWT 签发/校验"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

# ─── 配置 ───────────────────────────────────────────────────────────
SECRET_KEY       = os.environ.get("TRADING_SECRET_KEY", "change-me-in-production-7f3a9c2e8b1d4f6a")
JWT_ALGORITHM    = "HS256"
JWT_EXPIRE_HOURS = 24
DEV_BOOTSTRAP_TOKEN = "dev-bootstrap-token"
DEV_OPEN_ADMIN   = os.environ.get("TRADING_DEV_OPEN", "1") == "1"

# ─── 密码哈希（passlib 提供的 PBKDF2，零依赖、Python 3.13 兼容）───
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ─── JWT ────────────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def create_access_token(user_id: int, username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub":  str(user_id),
        "usr":  username,
        "role": role,
        "exp":  expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    """解码 token，失败抛 401"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token 无效：{e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ─── 依赖：当前用户 ────────────────────────────────────────────────
def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db:    Session        = Depends(get_db),
) -> User:
    # 开发模式：dev-bootstrap-token 视为首个 admin
    if DEV_OPEN_ADMIN and token == DEV_BOOTSTRAP_TOKEN:
        admin = db.query(User).filter(User.role == "admin", User.is_active == 1).order_by(User.id.asc()).first()
        if not admin:
            raise HTTPException(status_code=503, detail="DEV 模式启动但找不到 admin 用户")
        return admin

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token 缺少 sub")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已停用")
    return user

def require_admin(current: User = Depends(get_current_user)) -> User:
    """要求 admin 角色"""
    if current.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current
