"""akshare 数据服务"""
from datetime import datetime, timedelta
import akshare as ak
import pandas as pd


# ── 股票实时行情 ──

def fetch_realtime_quote(code: str) -> dict | None:
    """获取个股最新实时行情"""
    try:
        df = ak.stock_zh_a_spot_em()
        row = df[df["代码"] == code]
        if row.empty:
            return None
        r = row.iloc[0]
        return {
            "code": r["代码"],
            "name": r["名称"],
            "price": float(r["最新价"]),
            "change": float(r["涨跌幅"]),
            "change_amount": float(r["涨跌额"]),
            "volume": float(r["成交量"]),
            "amount": float(r["成交额"]),
            "high": float(r["最高"]),
            "low": float(r["最低"]),
            "open": float(r["今开"]),
            "pre_close": float(r["昨收"]),
            "turnover_rate": float(r.get("换手率", 0)),
            "pe": float(r.get("市盈率-动态", 0)),
            "market_cap": float(r.get("总市值", 0)),
        }
    except Exception as e:
        return None


def fetch_stock_history(code: str, days: int = 120) -> list[dict]:
    """获取历史日K数据"""
    try:
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                start_date=start, end_date=end, adjust="qfq")
        result = []
        for _, r in df.iterrows():
            result.append({
                "date": str(r["日期"]),
                "open": float(r["开盘"]),
                "close": float(r["收盘"]),
                "high": float(r["最高"]),
                "low": float(r["最低"]),
                "volume": float(r["成交量"]),
                "amount": float(r["成交额"]),
                "change_pct": float(r["涨跌幅"]),
            })
        return result
    except Exception as e:
        return []


# ── 大盘指数行情 ──

def fetch_market_index(index_code: str = "sh", days: int = 120) -> list[dict]:
    """获取大盘指数历史数据

    index_code: sh=上证, sz=深证, cy=创业板, sh50=上证50
    """
    index_map = {
        "sh": "上证指数",
        "sz": "深证成指",
        "cy": "创业板指",
        "sh50": "上证50",
        "hs300": "沪深300",
    }
    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    try:
        df = ak.stock_zh_index_daily(symbol=f"{index_code}000001" if index_code == "sh" else index_code)
        df = df[df["date"] >= start]
        result = []
        for _, r in df.iterrows():
            result.append({
                "date": str(r["date"])[:10],
                "open": float(r["open"]),
                "close": float(r["close"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "volume": float(r["volume"]),
            })
        return result
    except Exception as e:
        return []


def fetch_current_index() -> list[dict]:
    """获取当前大盘实时行情"""
    indices = [
        ("sh", "sh000001", "上证指数"),
        ("sz", "sz399001", "深证成指"),
        ("cy", "sz399006", "创业板指"),
        ("hs300", "sh000300", "沪深300"),
    ]
    result = []
    try:
        df = ak.stock_zh_index_spot_em()
        for key, _, name in indices:
            row = df[df["代码"] == key]
            if not row.empty:
                r = row.iloc[0]
                result.append({
                    "code": key,
                    "name": name if name else r["名称"],
                    "price": float(r["最新价"]),
                    "change_pct": float(r["涨跌幅"]),
                    "change_amount": float(r["涨跌额"]),
                    "volume": float(r.get("成交量", 0)),
                    "amount": float(r.get("成交额", 0)),
                })
    except Exception as e:
        pass
    return result


# ── 搜索股票 ──

def search_stock(keyword: str) -> list[dict]:
    """搜索股票/基金"""
    try:
        df = ak.stock_zh_a_spot_em()
        mask = df["代码"].str.contains(keyword) | df["名称"].str.contains(keyword)
        matches = df[mask].head(20)
        result = []
        for _, r in matches.iterrows():
            result.append({
                "code": r["代码"],
                "name": r["名称"],
                "price": float(r["最新价"]),
                "change_pct": float(r["涨跌幅"]),
            })
        return result
    except Exception as e:
        return []
