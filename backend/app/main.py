"""FastAPI 主入口"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import init_db, SessionLocal
from app.routers import stocks, market, trades, custom_indices, portfolio, auth, users
from app.models import User
from app.auth import hash_password, get_current_user

# 临时开发模式：开启后用户管理接口可不传 token（等前端登录做完再关闭）
DEV_OPEN_ADMIN = os.environ.get("TRADING_DEV_OPEN", "1") == "1"
DEV_BOOTSTRAP_TOKEN = "dev-bootstrap-token"


def _bootstrap_admin():
    """启动时如果没有用户，创建默认 admin / admin123"""
    db: Session = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return
        admin = User(
            username      = "admin",
            password_hash = hash_password("admin123"),
            role          = "admin",
            is_active     = 1,
        )
        db.add(admin)
        db.commit()
        print("[OK] Created default admin: admin / admin123 (please change password after login)")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _bootstrap_admin()
    yield


app = FastAPI(
    title="个人交易系统",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router)
app.include_router(market.router)
app.include_router(trades.router)
app.include_router(custom_indices.router)
app.include_router(portfolio.router)
app.include_router(auth.router)
app.include_router(users.router)

if DEV_OPEN_ADMIN:
    @app.get("/api/_dev/whoami", tags=["dev"])
    def dev_whoami(current = Depends(get_current_user)):
        return {
            "dev_mode":   True,
            "bootstrap":  current.username == "dev" if current else False,
            "user":       current,
        }


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
