"""自定义指数路由：增 / 删 / 查 / 验证（宽基 + 行业指数）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import CustomIndex, HiddenIndex
from app.schemas import CustomIndexCreate, CustomIndexOut
from app.services.eastmoney_service import verify_index

router = APIRouter(prefix="/api/indices", tags=["自定义指数"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/custom", response_model=list[CustomIndexOut])
def list_custom(db: Session = Depends(get_db)):
    """列出所有用户添加的指数"""
    return db.query(CustomIndex).order_by(CustomIndex.created_at.desc()).all()


@router.post("/custom", response_model=CustomIndexOut, status_code=201)
def add_custom(data: CustomIndexCreate, db: Session = Depends(get_db)):
    """添加一个自定义指数"""
    existing = db.query(CustomIndex).filter(CustomIndex.code == data.code).first()
    if existing:
        raise HTTPException(400, f"指数 {data.code} 已存在")

    row = CustomIndex(code=data.code.strip(), name=data.name.strip())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/custom/{code}")
def remove_custom(code: str, name: str = "", db: Session = Depends(get_db)):
    """删除一个指数

    - 如果是自定义指数（CustomIndex表）→ 物理删除
    - 如果是 CSI / 腾讯内置指数 → 加入 HiddenIndex 表隐藏（可在数据库中恢复）
    """
    # 先查自定义表
    row = db.query(CustomIndex).filter(CustomIndex.code == code).first()
    if row:
        name = row.name
        db.delete(row)
        db.commit()
        return {"ok": True, "code": code, "name": name, "action": "deleted"}

    # 不是自定义指数，加入隐藏表
    if not name:
        raise HTTPException(404, f"指数 {code} 不存在，且未提供名称")

    existing = db.query(HiddenIndex).filter(HiddenIndex.code == code).first()
    if not existing:
        db.add(HiddenIndex(code=code, name=name, source="builtin"))
        db.commit()
    return {"ok": True, "code": code, "name": name, "action": "hidden"}


# ─── 指数验证（按代码查名称）───

@router.get("/verify/{code}")
def verify_index_api(code: str):
    """
    用东方财富搜索 API 验证指数代码（宽基/行业均可），返回指数名称。
    用于「添加指数」时的代码验证和自动填充名称。
    """
    result = verify_index(code)
    if result:
        return {"found": True, "code": result["code"], "name": result["name"]}
    raise HTTPException(404, f"未找到指数 {code}，请检查代码或手动填写名称")
