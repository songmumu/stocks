"""估值服务：指数 PE/PB + 主动基金 NAV 历史分位

数据来源：
- 腾讯行情：实时 PE/PB（宽基指数）
- 中证指数 CSI：行业/主题指数 PE（可追溯 10+ 年历史 PE 序列）
- 本地快照：每日积累，长期用于宽基指数精确分位计算
"""
import codecs
import requests
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import IndexValuationSnapshot
from app.services import csi_service


# ──────────────── 腾讯行情常量 ────────────────────────────

TENCENT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://gu.qq.com/",
}

# 腾讯行情能覆盖的宽基指数（腾讯 API 有 PE/PB 字段）
WATCHED_INDICES = {
    "000300": ("sh000300", "沪深300"),
    "000016": ("sh000016", "上证50"),
    "399001": ("sz399001", "深证成指"),
    "399006": ("sz399006", "创业板指"),
    "000688": ("sh000688", "科创50"),
    "000905": ("sh000905", "中证500"),
    "000852": ("sh000852", "中证1000"),
}

# 腾讯行情无 PE 的行业/主题指数代码列表 → 用 CSI API
CSI_INDICES = {
    "930901": "中证动漫游戏指数",
    "H30533":  "中证海外中国互联网50",
    "931484":  "中证医药创新",
    "931152":  "中证创新药",
    "931087":  "中证科技龙头",
    "399986":  "中证金融",
}

ETF_TO_INDEX = {
    "512000": "000300",
    "512880": "000300",
    "510300": "000300",
    "510050": "000016",
    "159915": "399006",
}

# 韭圈儿 API 配置
JIUCAI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": "https://www.funddb.cn/",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.funddb.cn",
}

# 经验 PE 阈值：(extreme_low, low, normal, high, extreme_high)
EXPERIENCE_PE_THRESHOLDS = {
    "000300": (12, 14, 18, 22),
    "000016": (10, 12, 16, 20),
    "399001": (18, 25, 35, 45),
    "399006": (30, 45, 60, 80),
    "000688": (40, 60, 90, 120),
    "000905": (20, 28, 40, 55),
    "000852": (25, 35, 50, 70),
}


# ──────────────── 工具函数 ────────────────────────────

def _decode(s: str) -> str:
    if not s:
        return s
    try:
        return codecs.decode(s, 'unicode_escape')
    except Exception:
        return s


def _calc_percentile(value: float, history: list[float]) -> float | None:
    """计算 value 在 history 中的历史分位 (0~100)"""
    if not history or value is None:
        return None
    valid = [h for h in history if h is not None]
    if not valid:
        return None
    count = sum(1 for h in valid if h < value)
    return round(count / len(valid) * 100, 1)


def _fetch_csi_history(code: str) -> list[dict]:
    """获取 CSI 历史 PE 序列（带内存缓存，同一进程内不重复拉）"""
    # 直接从 csi_service 拉，取 10 年历史
    return csi_service.fetch_csi_pe_history(code, start_year=2010)


# ──────────────── 腾讯行情 ────────────────────────────

def _fetch_tencent_realtime(secids: list[str]) -> dict:
    """批量获取腾讯实时行情，返回 {secid: {name, price, pct, pe, pb}}"""
    if not secids:
        return {}
    url = "https://qt.gtimg.cn/q=" + ",".join(secids)
    results = {}
    try:
        r = requests.get(url, headers=TENCENT_HEADERS, timeout=10)
        for line in r.text.strip().splitlines():
            if '="' not in line:
                continue
            key = line.split('="')[0].lstrip("v_")
            body = line.split('="', 1)[1].rstrip('";\n ')
            parts = body.split("~")
            if len(parts) < 45:
                continue
            name = _decode(parts[1])
            pe_str = parts[39].strip()
            pb_str = parts[43].strip()
            pe = float(pe_str) if pe_str and pe_str not in ("", "-", "N/A") else None
            pb = float(pb_str) if pb_str and pb_str not in ("", "-", "N/A") else None
            results[key] = {
                "name": name,
                "price": float(parts[3]) if parts[3] else None,
                "pct": float(parts[32]) if len(parts) > 32 and parts[32] else None,
                "pe": pe,
                "pb": pb,
            }
    except Exception:
        pass
    return results


def fetch_index_valuation() -> list[dict]:
    """获取宽基指数实时 PE/PB（腾讯 API）+ CSI 行业指数 PE"""
    # 1. 腾讯宽基
    secids = [v[0] for v in WATCHED_INDICES.values()]
    data = _fetch_tencent_realtime(secids)
    results = []
    for code, (secid, name) in WATCHED_INDICES.items():
        d = data.get(secid, {})
        pe = d.get("pe")
        pb = d.get("pb")
        results.append({
            "code": code,
            "name": name,
            "secid": secid,
            "price": d.get("price"),
            "pct": d.get("pct"),
            "pe": pe,
            "pb": pb,
            "data_source": "tencent",
        })

    # 2. CSI 行业指数（腾讯无 PE）
    for code, name in CSI_INDICES.items():
        csi_data = csi_service.fetch_csi_realtime_pe(code)
        if csi_data:
            results.append({
                "code": code,
                "name": name,
                "secid": code,   # CSI 代码格式不同
                "price": None,
                "pct": None,
                "pe": csi_data.get("pe"),
                "pb": None,
                "trade_date": csi_data.get("trade_date"),
                "data_source": "csi",
            })
        else:
            results.append({
                "code": code,
                "name": name,
                "secid": code,
                "price": None, "pct": None,
                "pe": None, "pb": None,
                "data_source": "csi",
            })
    return results


# ──────────────── 韭圈儿 10 年历史 PE ──────────────────────────

def _fetch_jiucai_pe_history() -> dict | None:
    """从韭圈儿 API 获取沪深300 10年 PE 历史序列。

    注意：韭圈儿的 newtubiaolinedata API 对 gu_code 参数存在服务器端 bug，
    无论传入什么指数代码，始终返回沪深300的数据。
    因此本函数只适用于获取沪深300的历史 PE 序列。

    返回: {"pe_values": [float, ...], "dates": [str, ...],
           "current_pe": float, "avg_pe": float, "percentile": float}
    """
    try:
        s = requests.Session()
        s.get('https://www.funddb.cn/', timeout=10)
        s.post(
            'https://api.jiucaishuo.com/v2/fund-lists/choosezs',
            timeout=8, headers=JIUCAI_HEADERS, json={}
        )

        r = s.get(
            'https://api.jiucaishuo.com/v2/guzhi/newtubiaolinedata',
            timeout=15,
            headers=JIUCAI_HEADERS,
            params={'gu_code': '000300.SH', 'pe_category': 'pe', 'year': '10', 'ver': 'new'}
        )
        resp = r.json()
        if resp.get('code') != 0:
            return None

        data = resp.get('data', {})
        series_list = data.get('tubiao', {}).get('series', [])

        # 找到市盈率 series
        pe_series = None
        for s_item in series_list:
            if s_item.get('name') == '市盈率':
                pe_series = s_item.get('data', [])
                break

        if not pe_series:
            return None

        # 解析时间序列
        import datetime
        pe_values, dates = [], []
        for pt in pe_series:
            if not isinstance(pt, list) or len(pt) < 2:
                continue
            val = pt[1]
            if val is None:
                continue
            ts = pt[0]
            d = datetime.datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d')
            pe_values.append(float(val))
            dates.append(d)

        if not pe_values:
            return None

        current_pe = float(data.get('new_pe', 0))
        avg_pe = float(data.get('ping_pe', 0))
        percentile = _calc_percentile(current_pe, pe_values)

        return {
            "pe_values": pe_values,
            "dates": dates,
            "current_pe": current_pe,
            "avg_pe": avg_pe,
            "percentile": percentile,
        }
    except Exception:
        return None


# 缓存韭圈儿数据（一天内不重复请求）
_JIUCAI_CACHE: dict | None = None
_JIUCAI_CACHE_DATE: str = ""


def get_jiucai_pe_history() -> dict | None:
    """带缓存的韭圈儿数据获取（每日刷新）"""
    global _JIUCAI_CACHE, _JIUCAI_CACHE_DATE
    today = str(date.today())
    if _JIUCAI_CACHE is None or _JIUCAI_CACHE_DATE != today:
        _JIUCAI_CACHE = _fetch_jiucai_pe_history()
        _JIUCAI_CACHE_DATE = today
    return _JIUCAI_CACHE


# ──────────────── 指数估值快照（本地积累）────────────────────────

def save_today_snapshot() -> dict:
    """抓取今日指数 PE/PB 并写入快照表（幂等：已存在则跳过）"""
    raw = fetch_index_valuation()
    today = date.today()
    saved, skipped = [], []
    db: Session = SessionLocal()
    try:
        for item in raw:
            code = item["code"]
            pe = item.get("pe")
            pb = item.get("pb")
            if pe is None and pb is None:
                skipped.append(code)
                continue
            existing = db.query(IndexValuationSnapshot).filter_by(
                code=code, snapshot_date=today
            ).first()
            if existing:
                skipped.append(code)
                continue
            snap = IndexValuationSnapshot(
                code=code,
                snapshot_date=today,
                pe=pe,
                pb=pb,
                source="tencent",
            )
            db.add(snap)
            saved.append(code)
        db.commit()
    finally:
        db.close()
    return {"saved": saved, "skipped": skipped, "today": str(today)}


def get_index_history(code: str, days: int = 2520) -> list[dict]:
    """从本地快照表读取某指数历史 PE/PB 序列"""
    db: Session = SessionLocal()
    try:
        rows = (
            db.query(IndexValuationSnapshot)
            .filter(IndexValuationSnapshot.code == code)
            .order_by(IndexValuationSnapshot.snapshot_date.desc())
            .limit(days)
            .all()
        )
        return [{"date": str(r.snapshot_date), "pe": r.pe, "pb": r.pb} for r in rows]
    finally:
        db.close()


def calc_pe_pb_percentile(
    code: str,
    current_pe: float | None,
    current_pb: float | None,
) -> tuple[float | None, float | None, int]:
    """基于 CSI 历史 PE 序列 + 本地快照计算 PE/PB 分位。

    优先级：
    1. 行业指数（如 930901）：用 CSI 10年+ 历史 PE 序列
    2. 宽基指数（腾讯有 PE）：优先用本地快照积累（>= 30 天才返回有效分位）
    3. 不足时：返回 None
    """
    # 行业指数：用 CSI 历史 PE
    if code in CSI_INDICES:
        csi_history = _fetch_csi_history(code)
        if len(csi_history) >= 30:
            pe_vals = [h["pe"] for h in csi_history if h.get("pe")]
            if current_pe:
                pe_pct = _calc_percentile(current_pe, pe_vals)
                return pe_pct, None, len(pe_vals)
        return None, None, len(csi_history)

    # 宽基指数：用本地快照历史
    pe_pct, pb_pct, history_days = _calc_from_local(code, current_pe, current_pb)
    return pe_pct, pb_pct, history_days


def get_index_pct(
    code: str,
    current_pe: float | None = None,
    current_pb: float | None = None,
) -> dict:
    """统一获取某指数的分位数据（供其他路由复用）。

    优先级（与 valuation.py 路由一致）：
    1. 手动 HoldingPercentile 记录
    2. CSI 10年+ 历史 PE 序列（行业指数）
    3. 本地快照 >= 30 天（宽基指数）
    4. 无 → 返回 None

    参数:
        code: 指数代码
        current_pe: 当前 PE（可选，未传时会主动从 CSI 拉取）
        current_pb: 当前 PB（可选）

    返回: {
        "pe_pct": float | None,
        "pb_pct": float | None,
        "history_days": int,
        "data_source": "manual" | "csi_10y" | "local_snapshot" | "none",
        "band": "extreme_low" | ... | "unknown",
        "note": str,
        "updated_at": datetime | None,
    }
    """
    from app.models import HoldingPercentile
    db: Session = SessionLocal()
    try:
        # 1. 手动记录优先
        manual = db.query(HoldingPercentile).filter(HoldingPercentile.code == code).first()
        if manual and (manual.pe_pct is not None or manual.pb_pct is not None):
            pct_v = manual.pe_pct if manual.pe_pct is not None else manual.pb_pct
            return {
                "pe_pct": manual.pe_pct,
                "pb_pct": manual.pb_pct,
                "history_days": 0,
                "data_source": "manual",
                "band": pe_band(pct_v),
                "note": manual.note or "",
                "updated_at": manual.updated_at,
            }

        # 2. CSI 10年历史分位（行业指数）
        if code in CSI_INDICES:
            from app.services.csi_service import fetch_csi_pe_history, fetch_csi_realtime_pe
            csi_history = fetch_csi_pe_history(code, start_year=2010)
            # 只要没拿到有效 PE（>= 0.1），就从 CSI 拉实时 PE
            pe_val = current_pe if current_pe and current_pe > 0 else None
            if pe_val is None:
                realtime = fetch_csi_realtime_pe(code)
                pe_val = realtime.get("pe") if realtime else None
            if len(csi_history) >= 30 and pe_val and pe_val > 0:
                pe_vals = [h["pe"] for h in csi_history if h.get("pe")]
                pe_pct = _calc_percentile(pe_val, pe_vals)
                if pe_pct is not None:
                    return {
                        "pe_pct": pe_pct,
                        "pb_pct": None,
                        "history_days": len(pe_vals),
                        "data_source": "csi_10y",
                        "band": pe_band(pe_pct),
                        "note": f"中证指数 10年历史 ({len(pe_vals)} 天)",
                        "updated_at": None,
                    }

        # 3. 宽基指数：本地快照分位
        elif code in WATCHED_INDICES:
            pe_pct, pb_pct, days = _calc_from_local(code, current_pe, current_pb)
            if days >= 30 and (pe_pct is not None or pb_pct is not None):
                pct_v = pe_pct if pe_pct is not None else pb_pct
                return {
                    "pe_pct": pe_pct,
                    "pb_pct": pb_pct,
                    "history_days": days,
                    "data_source": "local_snapshot",
                    "band": pe_band(pct_v),
                    "note": f"本地快照 ({days} 天)",
                    "updated_at": None,
                }
    finally:
        db.close()

    return {
        "pe_pct": None,
        "pb_pct": None,
        "history_days": 0,
        "data_source": "none",
        "band": "unknown",
        "note": "无分位",
        "updated_at": None,
    }


def _calc_from_local(
    code: str, current_pe: float | None, current_pb: float | None
) -> tuple[float | None, float | None, int]:
    """基于本地快照计算分位（通用）"""
    history = get_index_history(code, days=2520)
    if len(history) < 30:
        return None, None, len(history)
    pe_vals = [h["pe"] for h in history if h["pe"] is not None]
    pb_vals = [h["pb"] for h in history if h["pb"] is not None]
    pe_pct = _calc_percentile(current_pe, pe_vals) if pe_vals else None
    pb_pct = _calc_percentile(current_pb, pb_vals) if pb_vals else None
    return pe_pct, pb_pct, len(history)


def _calc_pb_from_local(code: str, current_pb: float | None) -> tuple[float | None, None, int]:
    """计算 PB 分位（当 PE 分位来自韭圈儿时调用）"""
    history = get_index_history(code, days=2520)
    if len(history) < 30:
        return None, None, len(history)
    pb_vals = [h["pb"] for h in history if h["pb"] is not None]
    pb_pct = _calc_percentile(current_pb, pb_vals) if pb_vals else None
    return pb_pct, None, len(history)


# ──────────────── 主动基金 NAV 历史分位 ─────────────────────────

def fetch_fund_nav_percentile(code: str, lookback_days: int = 250) -> dict | None:
    """获取场外基金 NAV 历史分位"""
    from app.services.eastmoney_service import _fetch_fund_nav_history
    bars = _fetch_fund_nav_history(code, days=lookback_days)
    if not bars:
        return None
    navs = [b["close"] for b in bars]
    latest = navs[0]
    prev = navs[1] if len(navs) > 1 else latest
    change_pct = round((latest - prev) / prev * 100, 2) if prev else 0
    percentile = _calc_percentile(latest, navs)
    return {
        "code": code,
        "nav": round(latest, 4),
        "change_pct": change_pct,
        "percentile": percentile,
        "history_count": len(navs),
        "valid": len(navs) >= 30,
    }


# ──────────────── 档位判断 ────────────────────────────

def pe_band(pe_pct: float | None) -> str:
    """PE分位 → 档位标签"""
    if pe_pct is None:
        return "unknown"
    if pe_pct < 20:
        return "extreme_low"
    if pe_pct < 40:
        return "low"
    if pe_pct < 60:
        return "normal"
    if pe_pct < 80:
        return "high"
    return "extreme_high"


def pb_band(pb_pct: float | None) -> str:
    """PB分位 → 档位标签"""
    return pe_band(pb_pct)


def nav_band(percentile: float | None) -> str:
    """NAV分位 → 档位标签（用于主动基金）"""
    return pe_band(percentile)


def band_from_experience(code: str, pe: float | None) -> str:
    """基于经验 PE 阈值判断档位（快照不足时的兜底）"""
    if pe is None or pe <= 0:
        return "unknown"
    t = EXPERIENCE_PE_THRESHOLDS.get(code, (15, 22, 35, 50))
    if pe < t[0]:
        return "extreme_low"
    if pe < t[1]:
        return "low"
    if pe < t[2]:
        return "normal"
    if pe < t[3]:
        return "high"
    return "extreme_high"
