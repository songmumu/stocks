"""用户手动填写的 10 年历史分位路由

GET    /api/valuation/holding-percentile            - 列出全部
GET    /api/valuation/holding-percentile/{code}     - 获取单个
PUT    /api/valuation/holding-percentile/{code}     - 创建/更新（部分字段可空）
DELETE /api/valuation/holding-percentile/{code}     - 删除
"""
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import HoldingPercentile
from app.schemas import HoldingPercentileUpdate, HoldingPercentileOut

router = APIRouter(prefix="/api/valuation/holding-percentile", tags=["holding-percentile"])


def _to_out(row: HoldingPercentile) -> dict:
    return {
        "code": row.code,
        "pe_pct": row.pe_pct,
        "pb_pct": row.pb_pct,
        "note": row.note or "",
        "updated_at": row.updated_at,
    }


@router.get("", response_model=list[HoldingPercentileOut])
def list_all():
    """列出全部手动填写的分位"""
    db: Session = SessionLocal()
    try:
        rows = db.query(HoldingPercentile).order_by(HoldingPercentile.code).all()
        return [_to_out(r) for r in rows]
    finally:
        db.close()


@router.get("/{code}", response_model=HoldingPercentileOut)
def get_one(code: str):
    """获取单个品种的手动分位；不存在时返回空记录（避免前端报错）"""
    db: Session = SessionLocal()
    try:
        row = db.query(HoldingPercentile).filter(HoldingPercentile.code == code).first()
        if not row:
            return {"code": code, "pe_pct": None, "pb_pct": None,
                    "note": "", "updated_at": None}
        return _to_out(row)
    finally:
        db.close()


@router.put("/{code}", response_model=HoldingPercentileOut)
def upsert(code: str, payload: HoldingPercentileUpdate):
    """创建或更新单个品种的手动分位（部分字段可空）"""
    db: Session = SessionLocal()
    try:
        row = db.query(HoldingPercentile).filter(HoldingPercentile.code == code).first()
        if not row:
            row = HoldingPercentile(
                code=code,
                pe_pct=payload.pe_pct,
                pb_pct=payload.pb_pct,
                note=payload.note or "",
            )
            db.add(row)
        else:
            # 只更新传入的非空字段
            if payload.pe_pct  is not None: row.pe_pct  = payload.pe_pct
            if payload.pb_pct  is not None: row.pb_pct  = payload.pb_pct
            if payload.note    is not None: row.note    = payload.note
        db.commit()
        db.refresh(row)
        return _to_out(row)
    finally:
        db.close()


@router.delete("/{code}")
def delete(code: str):
    """删除单个品种的手动分位（回退到自动信号）"""
    db: Session = SessionLocal()
    try:
        row = db.query(HoldingPercentile).filter(HoldingPercentile.code == code).first()
        if not row:
            raise HTTPException(status_code=404, detail="该品种未填写手动分位")
        db.delete(row)
        db.commit()
        return {"code": code, "deleted": True}
    finally:
        db.close()
