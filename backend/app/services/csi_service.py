"""中证指数 CSI 数据源：行业指数 PE/PB 历史序列

数据源：https://www.csindex.com.cn/csindex-home/

关键 API：
- GET /perf/index-perf?indexCode={code}&startDate=&endDate=
  → 历史 K 线（含 peg 字段），可追溯 10+ 年，每指数数千条
- GET /perf/indexCsiDsPe?indexCode={code}
  → PE(TTM) 时间序列（最新到历史）

使用场景：
- 行业指数（腾讯无 PE）用 CSI 替代
- 宽基指数历史分位计算：用 CSI 10年+ 历史替代本地快照积累
"""
import requests
import time as _time
from datetime import date, datetime
from typing import Optional

CSI_BASE = "https://www.csindex.com.cn/csindex-home"

CSI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.csindex.com.cn/",
    "Accept": "application/json",
}

# ── 进程内缓存：避免重复请求 CSI API ──
# 实时 PE 缓存 1 小时，历史 PE 缓存 24 小时
_CACHE_REALTIME = {}  # {code: (timestamp, data)}
_CACHE_HISTORY = {}   # {code: (timestamp, data)}
_CACHE_TTL_REALTIME = 3600       # 1 小时
_CACHE_TTL_HISTORY = 24 * 3600   # 24 小时


def _cache_get(cache_dict, key, ttl):
    if key in cache_dict:
        ts, data = cache_dict[key]
        if _time.time() - ts < ttl:
            return data
    return None


def _cache_set(cache_dict, key, data):
    cache_dict[key] = (_time.time(), data)


# ──────────── 实时 PE ────────────

def fetch_csi_realtime_pe(code: str) -> dict | None:
    """
    获取单个指数最新 PE（从 index-perf 最近一个有 PE 的交易日）。
    返回: {"code", "pe", "trade_date", "pb": None, "source": "csi"}
    带 1 小时进程内缓存。
    """
    cached = _cache_get(_CACHE_REALTIME, code, _CACHE_TTL_REALTIME)
    if cached is not None:
        return cached
    today_str = date.today().strftime("%Y%m%d")
    # 取最近 5 个交易日数据，找第一个有 PE 的
    url = f"{CSI_BASE}/perf/index-perf"
    params = {
        "indexCode": code,
        "startDate": _n_trading_days_before(today_str, 5),
        "endDate": today_str,
    }
    result = None
    try:
        r = requests.get(url, params=params, headers=CSI_HEADERS, timeout=12)
        r.raise_for_status()
        data = r.json()
        items = data.get("data") or []
        # 从最新往旧找有 PE 的
        for item in items:
            peg = item.get("peg")
            if peg is not None and float(peg) > 0:
                result = {
                    "code": code,
                    "pe": float(peg),
                    "trade_date": item.get("tradeDate"),
                    "pb": None,
                    "source": "csi",
                }
                break
    except Exception as e:
        print(f"[csi] fetch_realtime_pe({code}) error: {e}")
    if result:
        _cache_set(_CACHE_REALTIME, code, result)
    return result


def fetch_csi_realtime_batch(codes: list[str]) -> dict[str, dict]:
    """批量获取多个指数最新 PE，返回 {code: {...}}"""
    result = {}
    for code in codes:
        item = fetch_csi_realtime_pe(code)
        if item:
            result[code] = item
    return result


# ──────────── 历史 PE 序列 ────────────

def fetch_csi_pe_history(
    code: str,
    start_year: int = 2010,
) -> list[dict]:
    """
    获取指数历史 PE 序列（从 start_year 到今天）。

    返回: [{"date": "YYYYMMDD", "pe": float}, ...] 倒序（最新在前）
    带 24 小时进程内缓存。
    """
    cache_key = (code, start_year)
    cached = _cache_get(_CACHE_HISTORY, cache_key, _CACHE_TTL_HISTORY)
    if cached is not None:
        return cached
    today_str = date.today().strftime("%Y%m%d")
    start_str = f"{start_year}0101"
    url = f"{CSI_BASE}/perf/index-perf"
    params = {
        "indexCode": code,
        "startDate": start_str,
        "endDate": today_str,
    }
    records = []
    try:
        r = requests.get(url, params=params, headers=CSI_HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        items = data.get("data") or []
        for item in items:
            peg = item.get("peg")
            if peg is None or float(peg) <= 0:
                continue
            records.append({
                "date": item["tradeDate"],
                "pe": round(float(peg), 4),
            })
    except Exception as e:
        print(f"[csi] fetch_pe_history({code}) error: {e}")
    _cache_set(_CACHE_HISTORY, cache_key, records)
    return records


# ──────────── 指数信息 ────────────

def fetch_csi_index_info(code: str) -> dict | None:
    """
    获取指数基本信息（名称、中文全称等）。
    通过 /perf/index-perf 接口，取第一条记录。
    """
    today_str = date.today().strftime("%Y%m%d")
    url = f"{CSI_BASE}/perf/index-perf"
    params = {
        "indexCode": code,
        "startDate": _n_trading_days_before(today_str, 10),
        "endDate": today_str,
    }
    try:
        r = requests.get(url, params=params, headers=CSI_HEADERS, timeout=12)
        r.raise_for_status()
        data = r.json()
        items = data.get("data") or []
        if not items:
            return None
        item = items[0]
        return {
            "code": item.get("indexCode"),
            "name_cn": item.get("indexNameCn"),
            "name_cn_full": item.get("indexNameCnAll"),
            "name_en": item.get("indexNameEn"),
            "name_en_full": item.get("indexNameEnAll"),
        }
    except Exception:
        return None


# ──────────── 搜索指数 ────────────

def search_csi_indices(keyword: str) -> list[dict]:
    """
    按关键词搜索中证指数（用东方财富搜索 API，SecurityType=5/11）。
    返回 [{code, name, type}]，type = "broad"(宽基) | "industry"(行业)
    """
    if not keyword:
        return []
    import requests as _requests
    url = "https://searchapi.eastmoney.com/api/suggest/get"
    params = {
        "input": keyword,
        "type": "14",
        "token": "D43BF722C8E33BDC906FB84D85E326E8",
        "count": "10",
        "_": "1622506200000",
    }
    try:
        r = _requests.get(url, params=params, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.eastmoney.com/",
            "Accept": "application/json",
        }, timeout=10)
        items = r.json().get("QuotationCodeTable", {}).get("Data", []) or []
        results = []
        for it in items:
            sec_type = it.get("SecurityType", "")
            if sec_type in ("5", "11"):
                # 宽基指数 (5) vs 行业/主题指数 (11)
                idx_type = "broad" if sec_type == "5" else "industry"
                results.append({
                    "code": it.get("Code"),
                    "name": it.get("Name"),
                    "type": idx_type,
                })
        return results
    except Exception:
        return []


# ──────────── 工具 ────────────

def _n_trading_days_before(date_str: str, n: int) -> str:
    """
    返回 date_str (YYYYMMDD) 往前推 n 个交易日的日期字符串。
    粗略估算：每年 ~250 个交易日，每 7 个自然日约 5 个交易日。
    """
    d = datetime.strptime(date_str, "%Y%m%d")
    # 粗估：每个自然周 5 个交易日
    delta_days = int(n * 7 / 5) + 5
    d_before = d - __import__("datetime").timedelta(days=delta_days)
    return d_before.strftime("%Y%m%d")
