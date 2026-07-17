"""估值路由：宽基指数 + CSI 行业指数实时 PE/PB + 分位

数据来源：
- 腾讯行情：宽基指数实时 PE/PB
- 中证指数 CSI：行业/主题指数实时 PE + 10年+ 历史 PE 序列 → 自动计算分位
- 手动分位：用户手动填入的 HoldingPercentile 记录
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import requests

from app.database import SessionLocal
from app.models import HoldingPercentile, CustomIndex, HiddenIndex
from app.services.valuation_service import (
    fetch_index_valuation,
    pe_band,
    CSI_INDICES,
    WATCHED_INDICES,
    calc_pe_pb_percentile,
)

router = APIRouter(prefix="/api/valuation", tags=["估值"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_BAND_LABELS = {
    "extreme_low": "极度低估",
    "low": "偏低",
    "normal": "适中",
    "high": "偏高",
    "extreme_high": "极度高估",
    "unknown": "未填分位",
}

_TENCENT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://gu.qq.com/",
}


def _secid(code: str) -> str:
    """指数代码 -> 腾讯 secid（向后兼容别名）"""
    if code.startswith(("000", "100", "110")):
        return "sh" + code
    if code.startswith(("399", "200")):
        return "sz" + code
    return "sh" + code


def _fetch_tencent_single(code: str) -> dict | None:
    """从腾讯 API 拉单个宽基指数实时 PE/PB"""
    try:
        r = requests.get(
            f"https://qt.gtimg.cn/q={_secid(code)}",
            headers=_TENCENT_HEADERS, timeout=8
        )
        parts = r.text.split("~")
        if len(parts) < 40 or not parts[1]:
            return None
        pe = float(parts[39]) if parts[39] and parts[39] not in ("-", "") else None
        pb = float(parts[43]) if len(parts) > 43 and parts[43] and parts[43] not in ("-", "") else None
        price = float(parts[3]) if parts[3] and parts[3] not in ("-", "") else None
        pre_close = float(parts[4]) if len(parts) > 4 and parts[4] and parts[4] not in ("-", "") else None
        pct = round((price - pre_close) / pre_close * 100, 2) if price and pre_close else None
        return {
            "code": code,
            "name": parts[1],
            "price": price,
            "pct": pct,
            "pe": pe,
            "pb": pb,
        }
    except Exception:
        return None


def _append_fields(code: str, item: dict, db: Session) -> dict:
    """
    给指数条目注入分位 + 档位 + 来源字段。

    分位来源优先级：
    1. 手动 HoldingPercentile 记录（用户主动填入）
    2. CSI 历史 PE 序列自动计算（行业指数，10年+历史）
    3. 本地快照自动计算（宽基指数，需积累 >= 30 天）
    """
    # 1. 先查手动记录
    manual = db.query(HoldingPercentile).filter(HoldingPercentile.code == code).first()
    pe_pct = manual.pe_pct if manual else None
    pb_pct = manual.pb_pct if manual else None
    history_days = 0
    data_source = "manual" if (pe_pct is not None or pb_pct is not None) else None

    # 2. 手动无 → 尝试 CSI 历史分位（行业指数）
    if pe_pct is None and pb_pct is None and code in CSI_INDICES:
        from app.services.csi_service import fetch_csi_realtime_pe, fetch_csi_pe_history
        current_pe = item.get("pe")
        if current_pe:
            csi_history = fetch_csi_pe_history(code, start_year=2010)
            if len(csi_history) >= 30:
                pe_vals = [h["pe"] for h in csi_history if h.get("pe")]
                if pe_vals:
                    from app.services.valuation_service import _calc_percentile
                    pe_pct = _calc_percentile(current_pe, pe_vals)
                    history_days = len(pe_vals)
                    data_source = "csi_10y"

    # 3. 手动无 + 非CSI → 尝试本地快照分位
    if pe_pct is None and pb_pct is None and code not in CSI_INDICES:
        current_pe = item.get("pe")
        current_pb = item.get("pb")
        pe_pct, pb_pct, history_days = calc_pe_pb_percentile(code, current_pe, current_pb)
        if history_days >= 30:
            data_source = "local_snapshot"

    # 档位判断
    if pe_pct is not None:
        band = pe_band(pe_pct)
    elif pb_pct is not None:
        band = pe_band(pb_pct)
    else:
        band = "unknown"

    return {
        **item,
        "pe_pct": pe_pct,
        "pb_pct": pb_pct,
        "history_days": history_days,
        "band": band,
        "band_label": _BAND_LABELS[band],
        "data_source": data_source or "none",
        "updated_at": manual.updated_at if manual else None,
    }


@router.get("/indices")
def get_index_valuation(db: Session = Depends(get_db)) -> list[dict]:
    """
    宽基指数 + CSI 行业指数实时 PE/PB + 自动/手动分位。

    返回字段说明：
    - data_source: "tencent"=宽基腾讯|"csi"=行业CSI | "manual"=手动|"csi_10y"=CSI历史|
                   "local_snapshot"=本地快照|"none"=无分位
    - history_days: 自动分位的历史数据条数（CSI=10年约2500条，本地快照=积累天数）
    """
    # 1. fetch_index_valuation 已包含宽基(腾讯) + CSI行业指数
    raw = fetch_index_valuation()
    # 过滤掉用户已隐藏的指数
    hidden_codes = {h.code for h in db.query(HiddenIndex).all()}
    raw = [item for item in raw if item["code"] not in hidden_codes]
    result = [_append_fields(item["code"], item, db) for item in raw]

    # 2. 用户自定义指数
    # WATCHED_INDICES + CSI_INDICES 中的指数已在上面覆盖，跳过避免重复
    covered_codes = set(WATCHED_INDICES) | set(CSI_INDICES)
    custom_rows = db.query(CustomIndex).all()
    for row in custom_rows:
        if row.code in hidden_codes:
            continue  # 用户已隐藏
        if row.code in covered_codes:
            continue  # WATCHED 或 CSI 已含此指数，跳过
        live = _fetch_tencent_single(row.code)
        if live:
            item = _append_fields(row.code, live, db)
        else:
            # 腾讯查不到，保留基本信息（腾讯不支持行业指数代码格式）
            item = {
                "code": row.code, "name": row.name,
                "price": None, "pct": None, "pe": None, "pb": None,
                "pe_pct": None, "pb_pct": None,
                "history_days": 0, "band": "unknown",
                "band_label": "未填分位",
                "data_source": "none", "updated_at": None,
            }
            # 注入手动分位
            manual = db.query(HoldingPercentile).filter(HoldingPercentile.code == row.code).first()
            if manual:
                from app.services.valuation_service import _calc_percentile
                pe_pct = manual.pe_pct
                pb_pct = manual.pb_pct
                band = pe_band(pe_pct) if pe_pct else pe_band(pb_pct) if pb_pct else "unknown"
                item.update({
                    "pe_pct": pe_pct, "pb_pct": pb_pct,
                    "band": band, "band_label": _BAND_LABELS[band],
                    "data_source": "manual",
                    "updated_at": manual.updated_at,
                })
        item["is_custom"] = True
        result.append(item)

    return result


# ── 向后兼容：stocks.py 依赖的旧函数名 ──
_fetch_single_index = _fetch_tencent_single
