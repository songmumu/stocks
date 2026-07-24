"""数据服务：行情 + 历史 K 线

数据源：腾讯股票 API（web.ifzq.gtimg.cn）
- 稳定，无明显反爬
- 覆盖 A 股 + 大盘指数
- 数据延迟较低
"""
import codecs
import requests
from datetime import datetime, timedelta

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://gu.qq.com/",
}


def _decode_uescape(s: str) -> str:
    """智能解码 \\uXXXX 转义：仅在含转义符时解码，避免破坏已解码的中文 str

    背景：东方财富 search/fundmobapi 等接口返回 JSON 字符串字面量（含 \\uXXXX），
    需要 unicode_escape 解码一次。
    而腾讯 qt.gtimg.cn 返回的是 GBK 解码后的纯中文 str，
    如果再走 unicode_escape 会把 UTF-8 字节误当作 latin-1 字符重新编码，
    产生 mojibake（如「游戏ETF华夏」→「æ¸¸æˆç¥¿ï¼æ²ç¥¿å¤」）。
    """
    if not s:
        return s
    # 关键：没有转义符的纯中文 str 不应再处理
    if "\\u" not in s and "\\x" not in s and "\\n" not in s:
        return s
    try:
        return codecs.decode(s, 'unicode_escape')
    except Exception:
        return s


def _get_json(url: str, params: dict, timeout: int = 12) -> dict:
    r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()


# ─────────── 实时行情 ───────────

def fetch_realtime_quote(code: str) -> dict | None:
    """个股实时行情。code 形如 600519 / 000001。场外基金返回 no_intraday 标记。"""
    secid = _to_tencent_secid(code)
    url = "https://qt.gtimg.cn/q=" + secid
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        text = r.text.strip()
        if '="' not in text:
            return None
        body = text.split('="', 1)[1].rstrip('";\n ')
        parts = body.split("~")
        # 场外基金返回字段不足，返回 no_intraday 标记让前端显示"暂无实时行情"
        if len(parts) < 40:
            name = _decode_uescape(parts[1]) if len(parts) > 1 else code
            return {
                "code": code,
                "name": name,
                "no_intraday": True,
                "price": 0, "pre_close": 0, "open": 0, "high": 0, "low": 0,
                "change": 0, "change_amount": 0, "volume": 0, "amount": 0,
                "turnover_rate": 0, "pe": 0, "market_cap": 0,
            }
        # 正常场内股票/ETF
        name = _decode_uescape(parts[1])
        return {
            "code": code,
            "name": name,
            "price": float(parts[3] or 0),
            "pre_close": float(parts[4] or 0),
            "open": float(parts[5] or 0),
            "volume": float(parts[6] or 0) * 100,
            "amount": float(parts[37] or 0) * 10000 if len(parts) > 37 else 0,
            "high": float(parts[33] or 0),
            "low": float(parts[34] or 0),
            "change": float(parts[32] or 0),
            "change_amount": float(parts[31] or 0),
            "turnover_rate": float(parts[38] or 0) if len(parts) > 38 else 0,
            "pe": float(parts[39] or 0) if len(parts) > 39 else 0,
            "market_cap": float(parts[45] or 0) * 1e8 if len(parts) > 45 else 0,
        }
    except Exception:
        return None


def fetch_realtime_batch(codes: list[str]) -> list[dict]:
    """批量拉取实时行情。"""
    if not codes:
        return []
    secids = [_to_tencent_secid(c) for c in codes]
    url = "https://qt.gtimg.cn/q=" + ",".join(secids)
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        r.raise_for_status()
        results = []
        for line in r.text.strip().splitlines():
            if '="' not in line:
                continue
            body = line.split('="', 1)[1].rstrip('";\n ')
            parts = body.split("~")
            if len(parts) < 40:
                continue
            name = _decode_uescape(parts[1])
            results.append({
                "code": parts[2],
                "name": name,
                "price": float(parts[3] or 0),
                "pre_close": float(parts[4] or 0),
                "open": float(parts[5] or 0),
                "volume": float(parts[6] or 0) * 100,
                "amount": float(parts[37] or 0) * 10000 if len(parts) > 37 else 0,
                "high": float(parts[33] or 0),
                "low": float(parts[34] or 0),
                "change": float(parts[32] or 0),
                "change_amount": float(parts[31] or 0),
                "turnover_rate": float(parts[38] or 0) if len(parts) > 38 else 0,
                "pe": float(parts[39] or 0) if len(parts) > 39 else 0,
                "market_cap": float(parts[45] or 0) * 1e8 if len(parts) > 45 else 0,
            })
        return results
    except Exception:
        return []


# ─────────── 历史 K 线 ───────────

def _is_fund_code(code: str) -> bool:
    """判断是否为场外基金代码（非6位股票代码，或非标准股票代码段）"""
    if len(code) != 6:
        return True
    # 6位数字：股票代码以 0/3/6 开头，基金以其他开头（如 1 开头）
    if code[0] in '036':
        # 进一步区分：0开头但非 000/001/002/003 可能是基金
        if code.startswith('0') and not code.startswith(('000', '001', '002', '003')):
            return True
        return False
    return True


def _fetch_fund_nav_history(code: str, days: int = 120) -> list[dict]:
    """场外基金净值历史（天天基金网）
    
    注意：天天基金网对 Python requests 有反爬，使用 PowerShell 作为数据获取方式
    """
    import subprocess
    import json as json_mod
    
    url = (
        f"https://fundmobapi.eastmoney.com/FundMNewApi/FundMNHisNetList"
        f"?FCODE={code}&pageIndex=1&pageSize={max(days, 60)}"
        f"&deviceid=wap&plat=Wap&product=EFund&version=2.0.0"
    )
    
    ps_cmd = f'Invoke-RestMethod -Uri "{url}" -UseBasicParsing | ConvertTo-Json -Depth 5'
    
    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True,
            timeout=30
        )
        if result.returncode != 0:
            stderr = result.stderr.decode('gbk', errors='ignore') if result.stderr else ''
            print(f"[fund nav] {code} ps error: {stderr}")
            return []
        
        # PowerShell 输出可能是 GBK 编码
        stdout = result.stdout.decode('utf-8', errors='ignore') or result.stdout.decode('gbk', errors='ignore')
        data = json_mod.loads(stdout)
        items = data.get("Datas") or []
        if not items:
            return []
        
        # 天天基金返回的是倒序（最新在前），需要反转
        result_list = []
        prev = None
        for item in reversed(items):
            date_str = item.get("FSRQ", "")
            nav = float(item.get("DWJZ") or 0)
            if nav <= 0 or not date_str:
                continue
            change_pct = 0.0
            if prev:
                change_pct = (nav - prev) / prev * 100
            result_list.append({
                "date": date_str,
                "open": nav,
                "close": nav,
                "high": nav,
                "low": nav,
                "volume": 0,
                "amount": 0,
                "change_pct": round(change_pct, 2),
            })
            prev = nav
        return result_list[-days:]
    except Exception as e:
        print(f"[fund nav] {code} error: {e}")
        return []


def fetch_stock_history(code: str, days: int = 120) -> list[dict]:
    """个股历史日 K 线（不复权）。场外基金用天天基金净值数据。"""
    # 场外基金：用天天基金网净值
    if _is_fund_code(code):
        return _fetch_fund_nav_history(code, days)

    # 股票/场内基金：用腾讯K线(不复权 bfq，与手机券商 App 价格口径一致)
    secid = _to_tencent_secid(code)
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {
        "param": f"{secid},day,,,{max(days, 60)},bfq",
    }
    try:
        data = _get_json(url, params)
        info = data.get("data", {}).get(secid, {})
        klines = info.get("qfqday") or info.get("day") or []
        return _parse_klines(klines)[-days:]
    except Exception:
        return []


def fetch_index_history(index_code: str, days: int = 120) -> list[dict]:
    """大盘指数历史日 K 线（不复权）"""
    secid_map = {
        "sh": "sh000001",
        "sz": "sz399001",
        "cy": "sz399006",
        "hs300": "sh000300",
        "kc50": "sh000688",
    }
    secid = secid_map.get(index_code, "sh000001")
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {
        "param": f"{secid},day,,,{max(days, 60)},",
    }
    try:
        data = _get_json(url, params)
        info = data.get("data", {}).get(secid, {})
        klines = info.get("qfqday") or info.get("day") or []
        return _parse_klines(klines)[-days:]
    except Exception:
        return []


def _parse_klines(klines: list) -> list[dict]:
    """腾讯 K 线格式: [date, open, close, high, low, volume, ...]"""
    result = []
    for k in klines:
        if not isinstance(k, list) or len(k) < 6:
            continue
        try:
            result.append({
                "date": k[0],
                "open": float(k[1]),
                "close": float(k[2]),
                "high": float(k[3]),
                "low": float(k[4]),
                "volume": float(k[5]) * 100,  # 手 → 股
                "amount": 0.0,
                "change_pct": round((float(k[2]) - float(k[1])) / float(k[1]) * 100, 2) if float(k[1]) else 0.0,
            })
        except (ValueError, TypeError, IndexError):
            continue
    return result


# ─────────── 大盘指数行情 ───────────

def fetch_current_indices() -> list[dict]:
    """四大指数实时行情"""
    secids = ["sh000001", "sz399001", "sz399006", "sh000300"]
    url = "https://qt.gtimg.cn/q=" + ",".join(secids)
    names = {
        "sh000001": "上证指数",
        "sz399001": "深证成指",
        "sz399006": "创业板指",
        "sh000300": "沪深300",
    }
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        r.raise_for_status()
        items = []
        for line in r.text.strip().splitlines():
            if '="' not in line:
                continue
            key = line.split('="', 1)[0].lstrip("v_")
            body = line.split('="', 1)[1].rstrip('";\n ')
            parts = body.split("~")
            if len(parts) < 40:
                continue
            code = key.replace("sh", "").replace("sz", "")
            items.append({
                "code": code,
                "name": names.get(key, _decode_uescape(parts[1])),
                "price": float(parts[3] or 0),
                "change_pct": float(parts[32] or 0),
                "change_amount": float(parts[31] or 0),
                "volume": float(parts[6] or 0) * 100,
                "amount": float(parts[37] or 0) * 10000 if len(parts) > 37 else 0,
            })
        return items
    except Exception:
        return []


# ─────────── 股票搜索 ───────────

def search_stocks(keyword: str) -> list[dict]:
    """模糊搜索股票（按代码或名称）"""
    if not keyword:
        return []
    url = "https://smartbox.gtimg.cn/s3/"
    params = {
        "q": keyword,
        "t": "all",
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        text = r.text.strip()
        if '="' not in text:
            return []
        body = text.split('="', 1)[1].rstrip('";\n ')
        # body 形如 "sh~600519~\u8d35\u5dde\u8305\u53f0~gzmt~GP-A"
        parts = body.split("~")
        if len(parts) < 3:
            return []
        market = parts[0]
        code = parts[1]
        name_raw = parts[2]
        if not code or not name_raw:
            return []
        name = _decode_uescape(name_raw)
        stock_type = "fund" if code.startswith(("15", "16", "18", "5")) else "stock"
        return [{
            "code": code,
            "name": name,
            "type": stock_type,
            "type_desc": "ETF" if stock_type == "fund" else "股票",
        }]
    except Exception:
        return []


# ─────────── 指数验证 ───────────

def verify_index(code: str) -> dict | None:
    """
    验证指数代码，返回指数名称。
    优先用东方财富搜索 API（SecurityType=5/11），失败时 fallback 到腾讯 API。
    覆盖场景：国证指数（如 399303 国证2000）在东方财富可能搜不到，但腾讯有数据。
    """
    if not code:
        return None

    # 1. 尝试东方财富（宽基/行业指数）
    url = "https://searchapi.eastmoney.com/api/suggest/get"
    params = {
        "input": code,
        "type": "14",
        "token": "D43BF722C8E33BDC906FB84D85E326E8",
        "count": "5",
        "_": "1622506200000",
    }
    try:
        r = requests.get(url, params=params, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.eastmoney.com/",
            "Accept": "application/json",
        }, timeout=10)
        r.raise_for_status()
        items = r.json().get("QuotationCodeTable", {}).get("Data", [])
        # SecurityType=5 = 宽基指数，11 = 行业指数
        for item in items:
            if item.get("Code") == code and item.get("SecurityType") in ("5", "11"):
                return {
                    "code": item["Code"],
                    "name": item.get("Name", ""),
                }
    except Exception:
        pass

    # 2. Fallback：用腾讯 API 验证（覆盖国证指数等东方财富未收录的指数）
    # 国证指数通常是 sz 开头（399xxx, 980xxx）
    for prefix in ["sz", "sh"]:
        secid = prefix + code
        url = f"https://qt.gtimg.cn/q={secid}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=8)
            if r.status_code == 200 and 'pv_none_match' not in r.text:
                # 解析腾讯返回格式: v_sz399303="51~国证2000~399303~..."
                if '~' in r.text:
                    parts = r.text.split('~')
                    if len(parts) >= 3:
                        name = _decode_uescape(parts[1])
                        returned_code = parts[2]
                        if returned_code == code and name:
                            return {"code": code, "name": name}
        except Exception:
            pass

    # 3. Fallback：中证指数 CSI API（覆盖 930xxx 等中证系列指数）
    # 中证指数代码通常是 930xxx、931xxx、932xxx 等
    if code.startswith(("930", "931", "932", "933", "934", "935", "936", "937", "938", "939")):
        try:
            csi_url = "https://www.csindex.com.cn/csindex-home/perf/index-perf"
            csi_params = {
                "indexCode": code,
                "startDate": "20250101",  # 近期数据即可
                "endDate": "20251231",
            }
            csi_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.csindex.com.cn/",
                "Accept": "application/json",
            }
            r = requests.get(csi_url, params=csi_params, headers=csi_headers, timeout=10)
            if r.status_code == 200:
                csi_json = r.json()
                items = csi_json.get("data", [])
                if items and len(items) > 0:
                    # 从第一条数据获取指数名称
                    name = items[0].get("indexNameCn", "")
                    if name:
                        return {"code": code, "name": name}
        except Exception:
            pass

    return None


# ─────────── 工具 ───────────

def _to_tencent_secid(code: str) -> str:
    """600519 -> sh600519 ; 000001 -> sz000001 ; 300750 -> sz300750"""
    if code.startswith(("60", "68", "9", "5")):
        return "sh" + code
    return "sz" + code


# ─────────── 价格历史入库（均线/放量预警用）──────────────────────────

def fetch_price_history_3years(code: str) -> list[dict]:
    """
    拉取近3年日K线（不复权），用于均线止损/放量预警计算。
    腾讯接口每次最多返回约350条，3年约750条交易日，分两次请求。
    """
    secid = _to_tencent_secid(code)
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    results = []

    for param_suffix in ["bfq", "bfq"]:
        try:
            params = {
                "param": f"{secid},day,,,350,{param_suffix}",
            }
            data = _get_json(url, params)
            info = data.get("data", {}).get(secid, {})
            # 优先取不复权 day，其次取 qfqday
            klines = info.get("day") or info.get("qfqday") or []
            parsed = _parse_klines(klines)
            if parsed:
                results.extend(parsed)
            break  # 成功就跳出
        except Exception:
            continue

    if not results:
        return []

    # 去重（按日期），保留最新（腾讯接口可能重叠）
    seen, unique = set(), []
    for k in reversed(results):
        if k["date"] not in seen:
            seen.add(k["date"])
            unique.append(k)
    unique.reverse()  # 时间正序
    return unique


def save_price_history(db_session, code: str, bars: list[dict]) -> int:
    """
    将 K线数据批量写入 price_history 表。
    已存在的 (code, date) 跳过（upsert 逻辑）。
    返回新增记录数。
    """
    from app.models import PriceHistory
    from datetime import datetime

    inserted = 0
    for bar in bars:
        date_str = bar["date"]
        try:
            trade_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue

        existing = db_session.query(PriceHistory).filter(
            PriceHistory.code == code,
            PriceHistory.date == trade_date,
        ).first()

        if existing:
            # 更新当日数据（价格可能修正）
            existing.close_price = bar["close"]
            existing.open_price = bar["open"]
            existing.high_price = bar["high"]
            existing.low_price = bar["low"]
            existing.volume = bar.get("volume", 0)
        else:
            db_session.add(PriceHistory(
                code=code,
                date=trade_date,
                close_price=bar["close"],
                open_price=bar.get("open", bar["close"]),
                high_price=bar.get("high", bar["close"]),
                low_price=bar.get("low", bar["close"]),
                volume=bar.get("volume", 0),
            ))
            inserted += 1

    db_session.commit()
    return inserted


def fetch_and_save_price_history(db_session, code: str) -> int:
    """拉取3年K线并存入数据库，返回新增条数。"""
    bars = fetch_price_history_3years(code)
    if not bars:
        return 0
    return save_price_history(db_session, code, bars)


# ── 旧 API 名兼容（避免路由器报 ImportError） ──
search_stock = search_stocks
fetch_batch_quotes = fetch_realtime_batch
fetch_indices_realtime = fetch_current_indices
fetch_index_realtime = fetch_realtime_quote
