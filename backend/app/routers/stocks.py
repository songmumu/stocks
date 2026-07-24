"""自选股管理 API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db
from app.services.eastmoney_service import fetch_and_save_price_history
from app.models import WatchlistStock, CustomIndex
from app.schemas import WatchlistStockCreate, WatchlistStockUpdate, WatchlistStockOut
from app.services.eastmoney_service import (
    fetch_realtime_quote,
    fetch_stock_history,
    search_stock,
    fetch_batch_quotes,
)

router = APIRouter(prefix="/api/stocks", tags=["自选股"])

# 固定宽基指数列表
_FIXED_INDICES = [
    {"code": "000300", "name": "沪深300"},
    {"code": "000016", "name": "上证50"},
    {"code": "399001", "name": "深证成指"},
    {"code": "399006", "name": "创业板指"},
    {"code": "000688", "name": "科创50"},
    {"code": "000905", "name": "中证500"},
    {"code": "000852", "name": "中证1000"},
]


@router.get("/search")
def search_stocks(keyword: str = Query(..., min_length=1)):
    """搜索股票（从网络）"""
    results = search_stock(keyword)
    return {"items": results}


@router.get("/quote/{code}")
def realtime_quote(code: str):
    """获取个股实时行情"""
    data = fetch_realtime_quote(code)
    if data is None:
        raise HTTPException(404, f"未找到股票 {code}")
    return data


@router.post("/quotes/batch")
def batch_quotes(codes: List[str]):
    """批量获取实时行情"""
    data = fetch_batch_quotes(codes)
    return {"items": data}


@router.get("/history/{code}")
def stock_history(code: str, days: int = Query(120, ge=30, le=720)):
    """获取个股历史 K 线"""
    data = fetch_stock_history(code, days)
    return {"code": code, "bars": data}


# ── 自选股 CRUD ──

@router.get("/watchlist", response_model=List[WatchlistStockOut])
def list_watchlist(db: Session = Depends(get_db)):
    """列出所有自选股"""
    return db.query(WatchlistStock).order_by(WatchlistStock.created_at.desc()).all()


@router.post("/watchlist", response_model=WatchlistStockOut, status_code=201)
def add_watchlist(item: WatchlistStockCreate, db: Session = Depends(get_db)):
    """添加自选股"""
    exists = db.query(WatchlistStock).filter(
        WatchlistStock.code == item.code
    ).first()
    if exists:
        raise HTTPException(409, f"{item.code} 已在自选列表中")

    stock = WatchlistStock(**item.model_dump())
    db.add(stock)
    db.commit()
    db.refresh(stock)
    # 自动拉取3年K线入库（用于均线/放量预警）
    try:
        fetch_and_save_price_history(db, item.code)
    except Exception:
        pass  # K线入库失败不影响添加自选
    return stock


@router.delete("/watchlist/{stock_id}", status_code=204)
def remove_watchlist(stock_id: int, db: Session = Depends(get_db)):
    """删除自选股"""
    stock = db.query(WatchlistStock).filter(WatchlistStock.id == stock_id).first()
    if not stock:
        raise HTTPException(404, "未找到该自选股")
    db.delete(stock)
    db.commit()
    return


@router.put("/watchlist/{stock_id}", response_model=WatchlistStockOut)
def update_watchlist(stock_id: int, item: WatchlistStockUpdate, db: Session = Depends(get_db)):
    """更新自选股"""
    stock = db.query(WatchlistStock).filter(WatchlistStock.id == stock_id).first()
    if not stock:
        raise HTTPException(404, "未找到该自选股")
    for key, val in item.model_dump(exclude_none=True).items():
        setattr(stock, key, val)
    stock.updated_at = datetime.now()
    db.commit()
    db.refresh(stock)
    return stock


@router.get("/available-indices")
def available_indices(db: Session = Depends(get_db)):
    """
    返回所有可关联的指数（固定7个 + 用户自定义）。
    """
    result = [{"code": i["code"], "name": i["name"], "is_fixed": True} for i in _FIXED_INDICES]
    for row in db.query(CustomIndex).all():
        result.append({"code": row.code, "name": row.name, "is_fixed": False})
    return result


@router.put("/watchlist/{stock_id}/link-index", response_model=WatchlistStockOut)
def link_index(stock_id: int, payload: dict, db: Session = Depends(get_db)):
    """设置/取消自选股的关联指数。"""
    stock = db.query(WatchlistStock).filter(WatchlistStock.id == stock_id).first()
    if not stock:
        raise HTTPException(404, "未找到该自选股")
    stock.index_code = payload.get("index_code") or None
    stock.updated_at = datetime.now()
    db.commit()
    db.refresh(stock)
    return stock
