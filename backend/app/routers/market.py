"""大盘行情 & 市场概览 API"""
from fastapi import APIRouter, Query, HTTPException
from app.services.eastmoney_service import fetch_current_indices, fetch_index_history
from app.services.eastmoney_service import fetch_realtime_quote as _fetch_qt_quote

router = APIRouter(prefix="/api/market", tags=["大盘行情"])


@router.get("/indices")
def current_indices():
    """获取大盘指数实时行情"""
    data = fetch_current_indices()
    return {"items": data}


@router.get("/index/history")
def index_history(code: str = Query("sh", description="sh/sz/cy/hs300"), days: int = Query(120, ge=30, le=720)):
    """获取大盘指数历史 K 线（查询参数方式）"""
    data = fetch_index_history(code, days)
    return {"code": code, "bars": data}


@router.get("/index-history/{code}")
def index_history_path(code: str, days: int = Query(90, ge=30, le=720)):
    """获取大盘指数历史 K 线（路径参数方式，兼容前端）"""
    data = fetch_index_history(code, days)
    return {"code": code, "bars": data}


@router.get("/realtime/{code}")
def realtime_quote(code: str):
    """
    获取任意股票/指数的实时行情（腾讯 API）。
    code 形如 600519 / 000300 / 399006（自动处理 sh/sz）。
    """
    data = _fetch_qt_quote(code)
    if data is None or data.get("no_intraday"):
        raise HTTPException(404, f"未找到 {code} 的实时行情")
    return data
