"""自选股/持仓估值信号路由

设计原则：
- 个股/ETF/基金本身不再填分位
- 分位数据来自关联指数的 HoldingPercentile 记录
- 实时行情（价格、涨跌、实时 PE）保留作为参考
- 宽基指数参考区：实时 PE/PB + 手动分位（指数自己的分位在指数估值页填）
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import WatchlistStock, HoldingPercentile
from app.services.valuation_service import (
    fetch_index_valuation,
    pe_band,
    get_index_pct,
    CSI_INDICES,
    WATCHED_INDICES,
)
from app.services.eastmoney_service import fetch_realtime_quote, verify_index

router = APIRouter(prefix="/api/valuation/watchlist", tags=["估值"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_BAND_LABELS = {
    "extreme_low": "极度低估", "low": "偏低",
    "normal": "适中",         "high": "偏高",
    "extreme_high": "极度高估", "unknown": "未填分位",
}
_BAND_ACTIONS = {
    "extreme_low": "强烈买入",  "low": "适当买入",
    "normal": "持有",          "high": "减少买入",
    "extreme_high": "考虑减仓", "unknown": "待填分位",
}


def _load_index_pct(db: Session, index_code: str, current_pe: float | None = None, current_pb: float | None = None) -> dict | None:
    """读取关联指数的分位数据（手动 → CSI → 本地快照三路优先级）"""
    return get_index_pct(index_code, current_pe, current_pb)


def _infer_type(code: str, stock_type: str) -> str:
    if stock_type == "fund":
        return "fund"
    if code.startswith(("510", "511", "513", "515", "588", "159")):
        return "etf"
    return "stock"


def _get_index_name(index_code: str) -> str:
    """获取指数名称，优先从本地映射，否则尝试验证API"""
    if index_code in _INDEX_NAMES:
        return _INDEX_NAMES[index_code]
    # 尝试从 verify_index 获取
    verified = verify_index(index_code)
    if verified and verified.get("name"):
        # 缓存到本地映射
        _INDEX_NAMES[index_code] = verified["name"]
        return verified["name"]
    return index_code


def _build_signal(item: WatchlistStock, db: Session) -> dict:
    """为单个自选品种构建信号，读关联指数的分位数据"""
    code = item.code
    name = item.name
    stype = _infer_type(code, item.stock_type)
    index_code = item.index_code  # 可能为 None

    # 实时行情
    quote = fetch_realtime_quote(code)
    if stype == "fund":
        price    = None
        nav      = quote.get("price") if quote else None
        chg      = quote.get("change_pct") if quote else None
        pe, pb  = None, None
    else:
        price    = quote.get("price") if quote else None
        chg      = quote.get("change_pct") if quote else None
        nav      = None
        pe       = quote.get("pe") if quote else None
        pb       = None

    # 无关联指数
    if not index_code:
        return {
            "id": item.id, "type": stype, "code": code, "name": name,
            "index_code": None, "index_name": None,
            "signal": None, "signal_label": "未关联",
            "band": "unknown", "band_label": "未关联指数",
            "nav": nav, "price": price, "change_pct": chg, "pe": pe, "pb": pb,
            "note": "请点击「关联指数」选择追踪指数",
            "data_source": "none", "updated_at": None,
            "action": "点击「关联指数」",
        }

    # 有关联指数：读指数分位
    idx_pct = _load_index_pct(db, index_code, current_pe=pe, current_pb=pb)
    if idx_pct and (idx_pct["pe_pct"] is not None or idx_pct["pb_pct"] is not None):
        pct_v = idx_pct["pe_pct"] if idx_pct["pe_pct"] is not None else idx_pct["pb_pct"]
        band = idx_pct["band"]
        # data_source 区分：手动=manual，其余表示是哪种自动分位
        ds = idx_pct["data_source"]
        # 对 watchlist 场景，只要是关联指数取得的分位都标记为 linked
        watch_ds = "linked" if ds == "manual" else f"linked_{ds}"
        return {
            "id": item.id, "type": stype, "code": code, "name": name,
            "index_code": index_code, "index_name": _get_index_name(index_code),
            "signal": pct_v, "signal_label": f"{pct_v:.1f}%",
            "band": band, "band_label": _BAND_LABELS[band],
            "nav": nav, "price": price, "change_pct": chg, "pe": pe, "pb": pb,
            "pe_pct": idx_pct["pe_pct"], "pb_pct": idx_pct["pb_pct"],
            "note": idx_pct["note"] or f"数据来自关联指数 {index_code}",
            "data_source": watch_ds,
            "updated_at": idx_pct["updated_at"],
            "history_days": idx_pct["history_days"],
            "action": _BAND_ACTIONS[band],
        }

    # 已关联但指数尚未填分位
    return {
        "id": item.id, "type": stype, "code": code, "name": name,
        "index_code": index_code, "index_name": _get_index_name(index_code),
        "signal": None, "signal_label": "指数未填分位",
        "band": "unknown", "band_label": "指数未填分位",
        "nav": nav, "price": price, "change_pct": chg, "pe": pe, "pb": pb,
        "note": f"关联 {index_code}，但该指数尚未填分位",
        "data_source": "linked", "updated_at": None,
        "action": "请先填指数分位",
    }


# 指数代码 → 中文名称（固定7个宽基 + 6 个 CSI 行业指数 + 兑底）
_INDEX_NAMES = {
    "000300": "沪深300",
    "000016": "上证50",
    "399001": "深证成指",
    "399006": "创业板指",
    "000688": "科创50",
    "000905": "中证500",
    "000852": "中证1000",
    # CSI 行业指数
    "930901": "中证动漫游戏",
    "H30533":  "中证海外中国互联网50",
    "931484":  "中证医药创新",
    "931152":  "中证创新药",
    "931087":  "中证科技龙头",
    "399986":  "中证金融",
}


@router.get("/signals")
def get_watchlist_signals(db: Session = Depends(get_db)) -> dict:
    """
    自选品种的专属估值信号。

    信号数据来源：
    - 关联指数的 HoldingPercentile 记录
    - 未关联 → 提示「关联指数」
    - 已关联但指数未填分位 → 提示「指数未填分位」
    """
    # 先更新内存中的指数名称映射（含自定义 + HoldingPercentile 里所有）
    all_fixed = [v["code"] for v in fetch_index_valuation() if not v.get("is_custom")]
    custom_rows = db.query(WatchlistStock).filter(
        WatchlistStock.index_code.isnot(None)
    ).all()
    for row in db.query(HoldingPercentile).all():
        if row.code not in _INDEX_NAMES:
            _INDEX_NAMES[row.code] = row.code  # 备用
    # 从 HoldingPercentile 拿手动名（有些自定义指数可能有名字）
    for hp in db.query(HoldingPercentile).all():
        if hp.note and hp.code not in _INDEX_NAMES:
            _INDEX_NAMES[hp.code] = hp.note

    items = db.query(WatchlistStock).order_by(WatchlistStock.created_at.desc()).all()
    signals = [_build_signal(item, db) for item in items]

    # 宽基指数参考区
    all_vals = fetch_index_valuation()
    index_signals = []
    for v in all_vals:
        pe = v.get("pe"); pb = v.get("pb")
        idx_pct = _load_index_pct(db, v["code"], current_pe=pe, current_pb=pb)
        if idx_pct and (idx_pct["pe_pct"] is not None or idx_pct["pb_pct"] is not None):
            pct_v = idx_pct["pe_pct"] if idx_pct["pe_pct"] is not None else idx_pct["pb_pct"]
            band = idx_pct["band"]
            index_signals.append({
                "code": v["code"], "name": v["name"],
                "is_custom": v.get("is_custom", False),
                "price": v.get("price"), "change_pct": v.get("pct"),
                "pe": pe, "pb": pb,
                "pe_pct": idx_pct["pe_pct"], "pb_pct": idx_pct["pb_pct"],
                "signal": pct_v, "signal_label": f"{pct_v:.1f}%",
                "band": band, "band_label": _BAND_LABELS[band],
                "data_source": idx_pct["data_source"],  # manual/csi_10y/local_snapshot
                "history_days": idx_pct["history_days"],
                "updated_at": idx_pct["updated_at"],
                "note": idx_pct["note"] or "分位数据",
                "action": _BAND_ACTIONS[band],
                "type": "index",
            })
        else:
            index_signals.append({
                "code": v["code"], "name": v["name"],
                "is_custom": v.get("is_custom", False),
                "price": v.get("price"), "change_pct": v.get("pct"),
                "pe": pe, "pb": pb,
                "pe_pct": None, "pb_pct": None,
                "signal": None, "signal_label": "未填",
                "band": "unknown", "band_label": "未填分位",
                "data_source": "none", "updated_at": None,
                "note": "在「指数估值」页面填入10年分位",
                "action": "去填分位",
                "type": "index",
            })

    return {
        "watchlist_signals": signals,
        "index_signals": index_signals,
        "summary": {
            "etf_count":   sum(1 for s in signals if s["type"] == "etf"),
            "fund_count":  sum(1 for s in signals if s["type"] == "fund"),
            "stock_count": sum(1 for s in signals if s["type"] == "stock"),
        }
    }
