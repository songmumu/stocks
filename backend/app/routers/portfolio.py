"""持仓操作系统 — 纯回撤策略，三重止损模式"""
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import TradeRecord, WatchlistStock, PortfolioPeakProfit, PriceHistory
from app.services.eastmoney_service import fetch_realtime_batch, fetch_and_save_price_history

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


# ──────────────── Pydantic Schema ────────────────────────────

class HoldingItem(BaseModel):
    code: str
    name: str
    stock_type: str
    index_code: Optional[str]
    index_type: str = 'A'
    qty: int
    cost: float
    cost_per_unit: float
    market_value: float
    profit: float
    profit_pct: float
    weight: float


class PositionSummary(BaseModel):
    total_cost: float
    total_market_value: float
    total_profit: float
    total_profit_pct: float
    total_return: float = 0.0
    total_return_pct: float = 0.0
    holdings: list[HoldingItem]


class PeakProfitInfo(BaseModel):
    peak_profit: float
    peak_date: Optional[str]
    current_profit: float
    drawdown: float
    drawdown_pct: float


class OperationAdvice(BaseModel):
    code: str
    name: str
    stock_type: str
    index_type: str
    market_value: float
    cost: float
    qty: int
    cost_per_unit: float
    profit: float
    profit_pct: float
    current_profit: float
    peak_profit: float
    drawdown: float
    drawdown_pct: float
    action: str
    action_ratio: Optional[float]
    action_desc: str
    reason: str
    warnings: list[str] = []

    model_config = {"populate_by_name": True}


class PortfolioAdvices(BaseModel):
    holdings: list[OperationAdvice]
    summary: dict


# ──────────────── 五档策略规则（新版）───────────────────────────
#
# 止盈：创新高后启动移动止盈
#   止盈1：高点回撤 N% → 减仓 40%
#   止盈2：高点回撤 M% → 清仓剩余 60%
#
# 止损（三重模式，任一触发即执行）：
#   硬性本金止损：浮亏达阈值 → 无条件清仓
#   趋势均线止损：跌破关键均线 → 减半/清仓
#   极端行情止损：放量暴跌 → 分批减仓（当日 + 次日）
#
# 特殊：C类换手率≥7%+放量滞涨 → 直接全部清仓

RULES = {
    "A": {  # 大盘宽基ETF
        "stop_profit_1": 12.0,      # 高点回撤 12% → 减 40%
        "stop_profit_2": 18.0,      # 高点回撤 18% → 清仓剩余
        "stop_loss_hard": -8.0,     # 硬性止损阈值
        # 趋势均线止损
        "ma10_action": "observe_3d",  # 仅破10日线：观察3日，未收回则减半
        "ma20_action": "clear",        # 破20日线：全部清仓
        # 极端行情
        "extreme_vol_pct": 5.0,       # 跌幅阈值 %
        "extreme_vol_ratio": 1.5,     # 量能放大倍数（较前日）
        "extreme_today_pct": 0.5,     # 当日减仓 50%
        "extreme_next_action": "clear_unrecovered",  # 次日未企稳清剩余
        "type_name": "大盘宽基ETF",
    },
    "B": {  # 科创50/创业板ETF
        "stop_profit_1": 13.0,      # 高点回撤 13% → 减 40%
        "stop_profit_2": 20.0,      # 高点回撤 20% → 清仓剩余
        "stop_loss_hard": -8.0,
        "ma10_action": "observe_3d",
        "ma20_action": "clear",
        "extreme_vol_pct": 6.0,
        "extreme_vol_ratio": None,       # 不要求量能放大，看板块内80%标的收跌
        "extreme_condition": "80pct_drop",  # 板块内≥80%标的收跌
        "extreme_today_pct": 0.6,
        "extreme_next_action": "recover_ma10",
        "type_name": "科创50/创业板ETF",
    },
    "C": {  # 科技赛道ETF
        "stop_profit_1": 15.0,      # 高点回撤 15% → 减 40%
        "stop_profit_2": 25.0,      # 高点回撤 25% → 清仓剩余
        "stop_loss_hard": -9.0,
        "ma10_action": "half",           # 仅破10日线：减半
        "ma20_action": "clear",
        "extreme_vol_pct": 7.0,
        "extreme_vol_ratio": None,        # 看换手率≥8%
        "extreme_condition": "turnover_8",  # 板块换手率≥8%
        "extreme_today_pct": 0.7,
        "extreme_next_action": "clear_unrecovered",
        "type_name": "科技赛道ETF",
        # C类特殊：换手率≥7%+放量滞涨直接全部清仓
        "special_clear_turnover": 7.0,
        "special_clear_action": "hot_market_clear",
    },
    "D": {  # 恒生科技ETF
        "stop_profit_1": 15.0,     # 高点回撤 15% → 减 40%
        "stop_profit_2": 25.0,     # 高点回撤 25% → 清仓剩余
        "stop_loss_hard": -9.0,
        "ma10_action": "half",           # 破10日线减半，3日未收清仓
        "ma20_action": "clear",
        "extreme_vol_pct": 6.0,
        "extreme_vol_ratio": 1.5,
        "extreme_today_pct": 0.5,
        "extreme_next_action": "judge_next",  # 剩余仓位次日判断
        "type_name": "恒生科技ETF",
        # D类特殊：重大利空尾盘减80%
        "special_black_swan_pct": 0.8,
    },
    "E": {  # 红利ETF
        "stop_profit_1": 20.0,      # 高点回撤 20% → 减 40%
        "stop_profit_2": 30.0,      # 高点回撤 30% → 清仓剩余
        "stop_loss_hard": -6.0,
        "ma10_action": "observe_5d",  # 仅破10日线：观察5日，无需急减
        "ma20_action": "clear",
        "extreme_vol_pct": 4.0,
        "extreme_vol_ratio": 1.4,
        "extreme_today_pct": 0.5,
        "extreme_next_action": "judge_next",
        "type_name": "红利ETF",
    },
}

DEFAULT_TYPE = "A"


# ──────────────── 标的类型自动判定 ────────────────────────────

def get_index_type(code: str, index_code: Optional[str]) -> str:
    target = (index_code or code).upper()
    if target in {"HSTECH", "HSCEI", "HSSI"} or code.upper() in {
        "513500", "159920", "164701", "000071", "159381"}:
        return "D"
    if code.upper() in {"510880", "512170", "159628", "008171", "100032", "501009"}:
        return "E"
    if target in {"000688", "399688", "159915", "588080", "588000"}:
        return "B"
    if code.upper() in {
        "512760", "159995", "515980", "159819", "588050",
        "512230", "159509", "159801", "513050", "515980",
        "159636", "159732", "516800", "515980", "159407"}:
        return "C"
    if target in {"000300", "000016", "000905", "000852", "399001", "399006", "399673"}:
        return "A"
    if code.upper() in {"513100", "513300", "161130", "040046"}:
        return "B"
    return DEFAULT_TYPE


# ──────────────── 价格历史查询 ────────────────────────────

def get_recent_bars(db: Session, code: str, count: int = 60) -> list[dict]:
    """
    从 price_history 表拉最近 N 条日K，按日期正序。
    若不足 20 条，自动从腾讯 API 补全并入库。
    """
    rows = (
        db.query(PriceHistory)
        .filter(PriceHistory.code == code)
        .order_by(PriceHistory.date.desc())
        .limit(count)
        .all()
    )
    bars = [
        {
            "date": str(r.date),
            "open": r.open_price or r.close_price,
            "close": r.close_price,
            "high": r.high_price or r.close_price,
            "low": r.low_price or r.close_price,
            "volume": r.volume or 0,
        }
        for r in rows
    ]
    bars.reverse()  # 恢复为正序（oldest→newest）
    # 不足 20 条时，尝试从网络补全
    if len(bars) < 20:
        try:
            inserted = fetch_and_save_price_history(db, code)
            if inserted > 0:
                rows = (
                    db.query(PriceHistory)
                    .filter(PriceHistory.code == code)
                    .order_by(PriceHistory.date.desc())
                    .limit(count)
                    .all()
                )
                bars = [
                    {
                        "date": str(r.date),
                        "open": r.open_price or r.close_price,
                        "close": r.close_price,
                        "high": r.high_price or r.close_price,
                        "low": r.low_price or r.close_price,
                        "volume": r.volume or 0,
                    }
                    for r in rows
                ]
                bars.reverse()
        except Exception:
            pass
    return bars


def calc_ma(bars: list[dict], period: int) -> Optional[float]:
    """计算简单移动平均（SMA），需要至少 period 条数据"""
    if len(bars) < period:
        return None
    closes = [b["close"] for b in bars[-period:]]
    return sum(closes) / period


def get_today_bar(bars: list[dict], today_str: str) -> Optional[dict]:
    """找到今日或最近一个交易日的数据"""
    if not bars:
        return None
    # 优先精确匹配今日
    for b in reversed(bars):
        if b["date"] == today_str:
            return b
    # 否则返回最后一条（最新数据）
    return bars[-1] if bars else None


def get_prev_bar(bars: list[dict], today_str: str) -> Optional[dict]:
    """获取今日前一个交易日的数据"""
    for i, b in enumerate(bars):
        if b["date"] == today_str and i > 0:
            return bars[i - 1]
    # 没有精确匹配，返回倒数第二条
    return bars[-2] if len(bars) >= 2 else None


# ──────────────── 预警计算 ────────────────────────────

def build_warnings(code: str, idx_type: str, bars: list[dict],
                   quote_today: dict) -> list[str]:
    """
    基于均线和成交量生成文字预警（仅提醒，不自动操作）。
    返回预警文案列表。
    """
    warnings = []
    rules = RULES.get(idx_type, RULES[DEFAULT_TYPE])
    today_str = str(date.today())
    today_bar = get_today_bar(bars, today_str)
    prev_bar = get_prev_bar(bars, today_str)
    ma10 = calc_ma(bars, 10)
    ma20 = calc_ma(bars, 20)

    # ── 均线预警 ──
    if len(bars) >= 20:
        close_last = bars[-1]["close"] if bars else None
        close_prev = bars[-2]["close"] if len(bars) >= 2 else None

        if ma10 and close_last and close_last < ma10:
            # 判断连续性：前一日是否也在10日线下
            below_10_count = sum(1 for b in bars[-5:] if b["close"] < ma10)
            if below_10_count >= 2:
                warnings.append(
                    f"⚠️ 收盘价已连续跌破10日线（MA10={ma10:.2f}），"
                    f"当前收盘{close_last:.2f}，留意趋势转弱"
                )
                if ma20 and close_last < ma20:
                    below_20_count = sum(1 for b in bars[-5:] if b["close"] < ma20)
                    if below_20_count >= 2:
                        warnings.append(
                            f"🔴 收盘价已连续跌破20日线（MA20={ma20:.2f}），"
                            f"当前收盘{close_last:.2f}，建议关注趋势止损"
                        )
                        # 10日线下穿20日线（金叉死叉反向）
                        if close_prev and close_prev > ma20 and close_last < ma20:
                            warnings.append(
                                f"🔴 均线死叉：10日线下穿20日线，趋势转空信号"
                            )

    # ── 极端行情预警（放量暴跌）──
    if today_bar and prev_bar:
        today_close = today_bar["close"]
        today_vol = today_bar["volume"]
        prev_close = prev_bar["close"]
        prev_vol = prev_bar["volume"]

        if prev_close > 0:
            today_change_pct = (today_close - prev_close) / prev_close * 100
            vol_ratio = (today_vol / prev_vol) if prev_vol > 0 else 0

            # 跌幅达到极端行情阈值
            extreme_pct = rules["extreme_vol_pct"]
            if today_change_pct <= -extreme_pct:
                vol_str = f"，成交量较前日放大{vol_ratio:.1f}倍" if vol_ratio > 1.0 else ""
                warnings.append(
                    f"🚨 极端行情预警：今日跌幅{today_change_pct:.1f}%"
                    f"{vol_str}，触及极端止损条件，需尾盘执行减仓"
                )

    # ── C类特殊：换手率过高预警 ──
    if idx_type == "C" and quote_today:
        turnover = quote_today.get("turnover_rate", 0) or 0
        if turnover >= rules["special_clear_turnover"]:
            warnings.append(
                f"🔥 C类特殊预警：板块换手率{turnover:.1f}%，"
                f"≥{rules['special_clear_turnover']}%警戒线，若放量滞涨需全部清仓"
            )

    return warnings


# ──────────────── 持仓计算 ────────────────────────────

def calc_holdings() -> list[HoldingItem]:
    db: Session = SessionLocal()
    try:
        trades = (
            db.query(TradeRecord)
            .filter(TradeRecord.price > 0.01)
            .order_by(TradeRecord.code, TradeRecord.trade_date)
            .all()
        )

        holdings_map: dict[str, dict] = {}
        for t in trades:
            if t.code not in holdings_map:
                holdings_map[t.code] = {"name": t.name, "qty": 0, "cost": 0.0}
            if t.trade_type == "buy":
                holdings_map[t.code]["qty"] += t.quantity
                holdings_map[t.code]["cost"] += t.price * t.quantity + t.fee
            elif t.trade_type == "sell":
                if holdings_map[t.code]["qty"] > 0:
                    avg_cost = holdings_map[t.code]["cost"] / holdings_map[t.code]["qty"]
                    holdings_map[t.code]["cost"] -= avg_cost * t.quantity
                    holdings_map[t.code]["cost"] = max(0, holdings_map[t.code]["cost"])
                holdings_map[t.code]["qty"] -= t.quantity

        active_codes = [code for code, d in holdings_map.items() if d["qty"] > 0]
        if not active_codes:
            return []

        quotes = fetch_realtime_batch(active_codes)
        quote_map = {q.get("code", ""): q for q in quotes}
        watchlist = db.query(WatchlistStock).all()
        watchlist_map = {w.code: w for w in watchlist}

        holdings = []
        total_value = 0.0
        total_cost = 0.0

        for code, data in holdings_map.items():
            if data["qty"] <= 0:
                continue
            quote = quote_map.get(code, {})
            current_price = quote.get("price", 0)
            if not current_price or current_price <= 0:
                current_price = data["cost"] / data["qty"]

            avg_cost = data["cost"] / data["qty"]
            market_value = current_price * data["qty"]
            profit = market_value - data["cost"]
            profit_pct = (profit / data["cost"] * 100) if data["cost"] > 0 else 0

            total_cost += data["cost"]
            total_value += market_value

            watch = watchlist_map.get(code)
            holdings.append(HoldingItem(
                code=code,
                name=data["name"],
                stock_type="stock",
                index_code=watch.index_code if watch else None,
                index_type=get_index_type(code, watch.index_code if watch else None),
                qty=data["qty"],
                cost=round(data["cost"], 2),
                cost_per_unit=round(avg_cost, 4),
                market_value=round(market_value, 2),
                profit=round(profit, 2),
                profit_pct=round(profit_pct, 2),
                weight=0,
            ))

        for h in holdings:
            if total_value > 0:
                h.weight = round(h.market_value / total_value * 100, 2)

        return holdings
    finally:
        db.close()


def calc_position_summary(holdings: list[HoldingItem],
                          total_return: float = 0.0,
                          total_return_pct: float = 0.0) -> PositionSummary:
    total_cost = sum(h.cost for h in holdings)
    total_mv = sum(h.market_value for h in holdings)
    total_profit = total_mv - total_cost
    return PositionSummary(
        total_cost=round(total_cost, 2),
        total_market_value=round(total_mv, 2),
        total_profit=round(total_profit, 2),
        total_profit_pct=round((total_profit / total_cost * 100) if total_cost > 0 else 0, 2),
        total_return=round(total_return, 2),
        total_return_pct=round(total_return_pct, 2),
        holdings=holdings
    )


def _calc_drawdown(current_profit: float, peak_profit: float) -> tuple[float, float]:
    if current_profit <= 0 or peak_profit <= 0:
        return 0.0, 0.0
    drawdown = peak_profit - current_profit
    drawdown_pct = round(drawdown / peak_profit * 100, 2) if peak_profit > 0 else 0.0
    return round(drawdown, 2), drawdown_pct


def get_peak_profit(code: str) -> PeakProfitInfo:
    db: Session = SessionLocal()
    try:
        record = db.query(PortfolioPeakProfit).filter(
            PortfolioPeakProfit.code == code
        ).first()
        if not record:
            return PeakProfitInfo(peak_profit=0.0, peak_date=None,
                                  current_profit=0.0, drawdown=0.0, drawdown_pct=0.0)
        return PeakProfitInfo(
            peak_profit=record.peak_profit,
            peak_date=str(record.peak_date) if record.peak_date else None,
            current_profit=0.0, drawdown=0.0, drawdown_pct=0.0
        )
    finally:
        db.close()


def update_peak_profit(code: str, current_profit: float) -> PeakProfitInfo:
    db: Session = SessionLocal()
    try:
        record = db.query(PortfolioPeakProfit).filter(
            PortfolioPeakProfit.code == code
        ).first()
        today = date.today()
        if not record:
            record = PortfolioPeakProfit(code=code, peak_profit=current_profit, peak_date=today)
            db.add(record)
        elif current_profit > record.peak_profit:
            record.peak_profit = current_profit
            record.peak_date = today
        db.commit()
        drawdown, drawdown_pct = _calc_drawdown(current_profit, record.peak_profit)
        return PeakProfitInfo(
            peak_profit=record.peak_profit,
            peak_date=str(record.peak_date) if record.peak_date else None,
            current_profit=current_profit,
            drawdown=drawdown,
            drawdown_pct=drawdown_pct
        )
    finally:
        db.close()


# ──────────────── 操作建议计算（三重止损 + 移动止盈）───────────────────────────

def calc_action(holding: HoldingItem, peak_info: PeakProfitInfo,
                bars: list[dict], quote_today: dict) -> OperationAdvice:
    """
    三重止损 + 两档止盈，纯回撤驱动。

    执行优先级（从高到低）：
      1. 硬性本金止损 — 浮亏达阈值，立即清仓
      2. 极端行情止损 — 放量暴跌，尾盘分批减仓
      3. C类特殊 — 换手率过热，直接清仓
      4. 趋势均线止损 — 跌破均线，减半/清仓
      5. 移动止盈 — 盈利状态下高点回撤，减仓/清仓
      6. 持有 — 无任何触发条件
    """
    idx_type = holding.index_type or DEFAULT_TYPE
    rules = RULES.get(idx_type, RULES[DEFAULT_TYPE])
    current_profit = holding.profit
    peak_profit = peak_info.peak_profit
    drawdown, drawdown_pct = _calc_drawdown(current_profit, peak_profit)

    # 更新历史最高
    updated_peak = update_peak_profit(holding.code, current_profit)
    peak_profit = updated_peak.peak_profit
    drawdown, drawdown_pct = updated_peak.drawdown, updated_peak.drawdown_pct

    # 生成预警（用于界面提醒）
    warnings = build_warnings(holding.code, idx_type, bars, quote_today)

    # ── 默认：持有 ──
    action = "持有"
    action_ratio: Optional[float] = None
    action_desc = "走势正常，无触发条件，继续持有"
    reason = ""

    # ── 1. 硬性本金止损（最高优先级）──
    if holding.profit_pct <= rules["stop_loss_hard"]:
        action = "清仓"
        action_ratio = 1.0
        action_desc = (
            f"浮亏 {holding.profit_pct:.1f}% 触及硬止损阈值 "
            f"({rules['stop_loss_hard']}%)，无条件全部清仓"
        )
        reason = f"硬性止损（{rules['type_name']}）"
        return _build(holding, idx_type, peak_profit, drawdown, drawdown_pct,
                      action, action_ratio, action_desc, reason, warnings)

    # ── 2. 趋势均线止损 ──
    today_str = str(date.today())
    today_bar = get_today_bar(bars, today_str)
    close_last = today_bar["close"] if today_bar else None
    ma10 = calc_ma(bars, 10)
    ma20 = calc_ma(bars, 20)

    if close_last is not None and len(bars) >= 20:
        ma10_action = rules["ma10_action"]
        # 收盘价连续2日低于MA10 → 触发10日线止损
        if ma10:
            below_10_days = sum(1 for b in bars[-5:] if b["close"] < ma10)
            if below_10_days >= 2 and close_last < ma10:
                if ma10_action == "half":
                    action = "减仓"
                    action_ratio = 0.5
                    action_desc = (
                        f"收盘价连续跌破10日线（MA10={ma10:.2f}），"
                        f"当前收盘{close_last:.2f}，按规则减半仓"
                    )
                    reason = f"趋势止损：跌破10日线减半（{rules['type_name']}）"
                    return _build(holding, idx_type, peak_profit, drawdown, drawdown_pct,
                                  action, action_ratio, action_desc, reason, warnings)
                elif ma10_action in ("observe_3d", "observe_5d"):
                    days = 5 if ma10_action == "observe_5d" else 3
                    action = "观察"
                    action_ratio = None
                    action_desc = (
                        f"收盘价跌破10日线（MA10={ma10:.2f}），"
                        f"当前收盘{close_last:.2f}，建议观察{days}日，"
                        f"若未收复则减半仓"
                    )
                    reason = f"趋势预警：跌破10日线观察{days}日（{rules['type_name']}）"
                    return _build(holding, idx_type, peak_profit, drawdown, drawdown_pct,
                                  action, action_ratio, action_desc, reason, warnings)

        # 收盘价连续2日低于MA20 → 全部清仓
        if ma20:
            below_20_days = sum(1 for b in bars[-5:] if b["close"] < ma20)
            if below_20_days >= 2 and close_last < ma20:
                action = "清仓"
                action_ratio = 1.0
                action_desc = (
                    f"收盘价连续跌破20日线（MA20={ma20:.2f}），"
                    f"当前收盘{close_last:.2f}，趋势转空，全部清仓"
                )
                reason = f"趋势止损：有效跌破20日线清仓（{rules['type_name']}）"
                return _build(holding, idx_type, peak_profit, drawdown, drawdown_pct,
                              action, action_ratio, action_desc, reason, warnings)

    # ── 3. 极端行情止损 ──
    if today_bar and len(bars) >= 2:
        prev_bar = bars[-2]
        today_vol = today_bar["volume"] or 0
        prev_vol = prev_bar["volume"] or 0
        today_close = today_bar["close"]
        prev_close = prev_bar["close"]

        if prev_close > 0 and prev_vol > 0:
            today_chg_pct = (today_close - prev_close) / prev_close * 100
            vol_ratio = today_vol / prev_vol

            extreme_pct = rules["extreme_vol_pct"]
            extreme_today_pct = rules["extreme_today_pct"]

            # 跌幅达标
            if today_chg_pct <= -extreme_pct:
                # 判断量能是否达标（D/E/A）
                vol_ok = (
                    vol_ratio >= rules["extreme_vol_ratio"]
                    if rules.get("extreme_vol_ratio")
                    else True
                )
                if vol_ok:
                    action = "减仓"
                    action_ratio = extreme_today_pct
                    action_desc = (
                        f"今日跌幅{today_chg_pct:.1f}%（≥{extreme_pct}%）"
                        f"触及极端行情止损，建议今日尾盘减仓 "
                        f"{int(extreme_today_pct * 100)}%，"
                        f"剩余仓位次日根据走势判断"
                    )
                    reason = f"极端行情止损（{rules['type_name']}）"
                    return _build(holding, idx_type, peak_profit, drawdown, drawdown_pct,
                                  action, action_ratio, action_desc, reason, warnings)

    # ── 4. C类特殊：过热直接清仓 ──
    if idx_type == "C" and quote_today:
        turnover = quote_today.get("turnover_rate", 0) or 0
        if turnover >= rules["special_clear_turnover"] and quote_today.get("change", 0) < 2:
            # 换手率高但涨幅小（滞涨）
            action = "清仓"
            action_ratio = 1.0
            action_desc = (
                f"板块换手率{turnover:.1f}%且放量滞涨，"
                f"超过{rules['special_clear_turnover']}%警戒线，"
                f"C类规则直接全部清仓，跳过止盈档位"
            )
            reason = "C类特殊清仓：板块过热+放量滞涨"
            return _build(holding, idx_type, peak_profit, drawdown, drawdown_pct,
                          action, action_ratio, action_desc, reason, warnings)

    # ── 5. 移动止盈（盈利状态下）──
    if current_profit > 0 and peak_profit > 0:
        sp1 = rules["stop_profit_1"]
        sp2 = rules["stop_profit_2"]
        if drawdown_pct >= sp2:
            action = "清仓"
            action_ratio = 1.0
            action_desc = (
                f"高点回撤 {drawdown_pct:.1f}% 触发第2档（≥{sp2}%）"
                f"，全部清仓波段仓"
            )
            reason = f"止盈第2档：回撤{sp2}%全部清仓（{rules['type_name']}）"
        elif drawdown_pct >= sp1:
            action = "减仓"
            action_ratio = 0.4
            action_desc = (
                f"高点回撤 {drawdown_pct:.1f}% 触发第1档（≥{sp1}%）"
                f"，减仓40%"
            )
            reason = f"止盈第1档：回撤{sp1}%减仓40%（{rules['type_name']}）"

    return _build(holding, idx_type, peak_profit, drawdown, drawdown_pct,
                  action, action_ratio, action_desc, reason, warnings)


def _build(holding: HoldingItem, idx_type: str,
            peak_profit: float, drawdown: float, drawdown_pct: float,
            action: str, action_ratio: Optional[float],
            action_desc: str, reason: str,
            warnings: list[str]) -> OperationAdvice:
    return OperationAdvice(
        code=holding.code,
        name=holding.name,
        stock_type=holding.stock_type,
        index_type=idx_type,
        market_value=holding.market_value,
        cost=holding.cost,
        qty=holding.qty,
        cost_per_unit=holding.cost_per_unit,
        profit=holding.profit,
        profit_pct=holding.profit_pct,
        current_profit=round(holding.profit, 2),
        peak_profit=peak_profit,
        drawdown=round(drawdown, 2),
        drawdown_pct=drawdown_pct,
        action=action,
        action_ratio=action_ratio,
        action_desc=action_desc,
        reason=reason,
        warnings=warnings,
    )


# ──────────────── API 路由 ────────────────────────────

@router.get("/holdings", response_model=PositionSummary)
async def get_holdings():
    holdings = calc_holdings()
    summary = calc_position_summary(holdings)
    db: Session = SessionLocal()
    try:
        trades = db.query(TradeRecord).filter(TradeRecord.price > 0.01).all()
        total_buy = sum(t.price * t.quantity + (t.fee or 0)
                        for t in trades if t.trade_type == 'buy')
        total_sell = sum(t.price * t.quantity - (t.fee or 0)
                         for t in trades if t.trade_type == 'sell')
    finally:
        db.close()
    current_value = sum(h.market_value for h in holdings)
    total_return = (current_value + total_sell) - total_buy
    total_return_pct = (total_return / total_buy * 100) if total_buy > 0 else 0
    return calc_position_summary(holdings, total_return, total_return_pct)


@router.get("/prices")
async def get_live_prices():
    db = SessionLocal()
    try:
        holdings = db.query(
            TradeRecord.code,
            func.max(TradeRecord.name).label('name')
        ).filter(TradeRecord.price > 0.01).group_by(TradeRecord.code).all()
        codes = [h.code for h in holdings]
        if not codes:
            return {"prices": {}, "date": None}
        quotes = fetch_realtime_batch(codes)
        prices = {q.get('code', ''): float(q.get('price', 0) or 0) for q in quotes}
        return {"prices": prices}
    finally:
        db.close()


@router.post("/advices", response_model=PortfolioAdvices)
async def get_advices(payload: dict = Body(default={})):
    """
    获取所有持仓的操作建议（含均线/放量预警）。
    payload 可选包含 manual_types: {code: 'A'|'B'|'C'|'D'|'E'} 手动覆盖类型。
    """
    manual_types = (payload or {}).get("manual_types", {}) or {}
    holdings = calc_holdings()

    db: Session = SessionLocal()
    try:
        # 批量拉取实时行情（用于极端行情预警）
        all_codes = [h.code for h in holdings]
        quotes = fetch_realtime_batch(all_codes) if all_codes else []
        quote_map = {q.get("code", ""): q for q in quotes}

        advices = []
        for holding in holdings:
            if holding.code in manual_types:
                holding = holding.model_copy(
                    update={"index_type": manual_types[holding.code]}
                )

            peak_info = get_peak_profit(holding.code)
            peak_info.current_profit = holding.profit
            peak_info.drawdown, peak_info.drawdown_pct = _calc_drawdown(
                holding.profit, peak_info.peak_profit
            )

            # 获取价格历史（用于均线计算）
            bars = get_recent_bars(db, holding.code, count=60)
            quote_today = quote_map.get(holding.code, {})

            advice = calc_action(holding, peak_info, bars, quote_today)
            advices.append(advice)

        total_profit = sum(a.current_profit for a in advices)
        peak_profit = max((a.peak_profit for a in advices), default=0)

        return PortfolioAdvices(
            holdings=advices,
            summary={
                "total_holdings": len(advices),
                "total_profit": round(total_profit, 2),
                "total_peak_profit": round(peak_profit, 2),
                "need_action_count": sum(
                    1 for a in advices
                    if a.action in ["清仓", "减仓", "止损清仓", "观察"]
                )
            }
        )
    finally:
        db.close()


@router.post("/update-peak")
async def post_update_peak(code: str, current_profit: float):
    result = update_peak_profit(code, current_profit)
    return {"code": code, "result": result}


@router.get("/history")
async def get_portfolio_history(days: int = 30):
    """根据交易记录 + price_history 逐日回放组合盈亏

    返回 [{date, totalProfit, totalCost, dailyPnl, cumPnlPct}, ...]

    实现细节：
    1. 为每个持仓标的自动 fetch 今日/昨日 close_price 插入 price_history (如果缺失)
    2. 从首笔交易日起逐日回放 totalCost/marketValue/totalProfit/cumPnlPct/marketPnlPct
    """
    db: Session = SessionLocal()
    try:
        # step 0: 拉取今日实时价补齐 price_history
        trades_pre = db.query(TradeRecord).filter(TradeRecord.price > 0.01).all()
        codes = sorted({t.code for t in trades_pre})
        if codes:
            today = date.today()
            quotes = fetch_realtime_batch(codes)
            from sqlalchemy import and_
            for q in quotes:
                code = q.get('code', '')
                price = float(q.get('price', 0) or 0)
                if not code or price <= 0:
                    continue
                # 该 code 今天是否已有记录？
                exists = (db.query(PriceHistory)
                            .filter(and_(PriceHistory.code == code, PriceHistory.date == today))
                            .first())
                if not exists:
                    db.add(PriceHistory(code=code, date=today, close_price=price,
                                        open_price=price, high_price=price, low_price=price, volume=0))
            try:
                db.commit()
            except Exception:
                db.rollback()
    finally:
        db.close()

    # === 真实回放交易 + 历史价 ===
    db = SessionLocal()
    try:
        trades = db.query(TradeRecord).filter(TradeRecord.price > 0.01).order_by(TradeRecord.trade_date).all()
        if not trades:
            return {"history": []}

        # 1. 按 code 取所有 close date 序列 (升序)
        codes = sorted({t.code for t in trades})
        hist = {}
        for code in codes:
            rows = (db.query(PriceHistory)
                      .filter(PriceHistory.code == code)
                      .order_by(PriceHistory.date)
                      .all())
            hist[code] = {r.date: r.close_price for r in rows}

        # 2. 找到所有需要回放的日期 (从首个交易日起 ±30 天)
        first_trade = trades[0].trade_date
        last_close = max((max(d.keys()) for d in hist.values() if d), default=first_trade)
        start = first_trade
        end = min(last_close, date.today())
        all_dates = sorted({d for code_dict in hist.values() for d in code_dict.keys()
                            if start <= d <= end})
        # 限制 days
        if len(all_dates) > days:
            all_dates = all_dates[-days:]

        # 3. 逐日回放
        history = []
        prev_close_per_code = {}  # code -> 上一个有效 close (用于计算日收益率)

        for d in all_dates:
            cum_buy_cost = 0.0
            cum_buy_qty = {}  # code -> 累计净持仓
            cum_sell_amt = 0.0
            for t in trades:
                if t.trade_date > d:
                    continue
                qty = float(t.quantity)
                price = float(t.price)
                fee = float(t.fee or 0)
                if t.trade_type == 'buy':
                    cum_buy_cost += price * qty + fee
                    cum_buy_qty[t.code] = cum_buy_qty.get(t.code, 0) + qty
                else:
                    cum_buy_qty[t.code] = cum_buy_qty.get(t.code, 0) - qty
                    cum_sell_amt += price * qty - fee
            # 当前持仓市值 + 各标的的日收益率加权
            market_value = 0.0
            today_close_per_code = {}
            today_value_per_code = {}
            for code, qty in cum_buy_qty.items():
                if qty <= 0:
                    continue
                # 找该日或之前最近的 close
                close = hist.get(code, {}).get(d)
                if close is None:
                    valid_dates = [dt for dt in hist.get(code, {}).keys() if dt <= d]
                    if valid_dates:
                        close = hist[code][max(valid_dates)]
                    else:
                        continue
                value = close * qty
                market_value += value
                today_close_per_code[code] = close
                today_value_per_code[code] = value
            # 在计算完总市值后再加权各标的口收益率
            weighted_pnl_pct = 0.0
            for code, value in today_value_per_code.items():
                prev_close = prev_close_per_code.get(code)
                close = today_close_per_code[code]
                if prev_close and prev_close > 0 and market_value > 0:
                    code_daily_pct = (close - prev_close) / prev_close * 100
                    weighted_pnl_pct += code_daily_pct * (value / market_value)

            total_value = market_value + cum_sell_amt
            total_profit = total_value - cum_buy_cost
            cum_pnl_pct = (total_profit / cum_buy_cost * 100) if cum_buy_cost > 0 else 0

            history.append({
                "date": d.isoformat(),
                "totalProfit": round(total_profit, 2),
                "totalCost":   round(cum_buy_cost, 2),
                "marketValue": round(market_value, 2),
                "cumPnlPct":   round(cum_pnl_pct, 4),
                "marketPnlPct": round(weighted_pnl_pct, 4),
            })
            prev_close_per_code = today_close_per_code
        return {"history": history}
    finally:
        db.close()
