"""持仓操作系统"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import TradeRecord, WatchlistStock, PortfolioPeakProfit
from app.services.valuation_service import get_index_pct, WATCHED_INDICES, ETF_TO_INDEX, CSI_INDICES
from app.services.eastmoney_service import fetch_realtime_batch

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


# ──────────────── Pydantic Schema ────────────────────────────

class HoldingItem(BaseModel):
    code: str
    name: str
    stock_type: str
    index_code: Optional[str]
    index_type: str = 'A'  # 宽基 A / 成长 B / 窄基 C
    qty: int
    cost: float
    cost_per_unit: float
    market_value: float
    profit: float
    profit_pct: float
    weight: float  # 仓位占比 %


class PositionSummary(BaseModel):
    total_cost: float
    total_market_value: float
    total_profit: float
    total_profit_pct: float
    holdings: list[HoldingItem]


class PeakProfitInfo(BaseModel):
    peak_profit: float
    peak_date: Optional[str]
    current_profit: float
    drawdown: float
    drawdown_pct: float


class PEInfo(BaseModel):
    code: str
    name: str
    pe_pct: Optional[float]
    band: str  # extreme_low / low / normal / high / extreme_high / unknown


class OperationAdvice(BaseModel):
    code: str
    name: str
    stock_type: str
    index_type: str  # A / B / C
    market_value: float
    cost: float
    qty: int
    cost_per_unit: float
    profit: float
    profit_pct: float
    pe_pct: Optional[float]
    pe_band: str
    current_profit: float
    peak_profit: float
    drawdown: float
    drawdown_pct: float
    action: str  # 买入/持有/止盈/观望
    action_ratio: Optional[float]  # 操作比例，如 0.4 表示减仓 40%
    action_desc: str
    reason: str


class PortfolioAdvices(BaseModel):
    holdings: list[OperationAdvice]
    summary: dict


# ──────────────── 指数分类 ────────────────────────────

# A类：宽基
INDEX_TYPE_A = {"000300", "000016", "000905", "000852", "399001", "399006", "000688"}
# B类：纳斯达克
INDEX_TYPE_B = {"IXIC", "NDX", "513100", "513300"}  # 纳指相关
# C类：窄基
INDEX_TYPE_C = {"399006", "000688"}  # 创业板、科创50

# 指数类型映射（ETF代码 → 指数代码）
ETF_TO_INDEX_MAP = {
    "510300": "000300",  # 沪深300ETF
    "512000": "000300",  # 沪深300ETF
    "512880": "000300",  # 沪深300ETF
    "510050": "000016",  # 上证50ETF
    "510500": "000905",  # 中证500ETF
    "159915": "399006",  # 创业板ETF
    "588000": "000688",  # 科创50ETF
    "513100": "NDX",     # 纳指ETF
    "513300": "NDX",     # 纳指ETF
}


def get_index_type(code: str, index_code: Optional[str]) -> str:
    """判断指数类型：A/B/C"""
    target = index_code or code
    if target in INDEX_TYPE_A:
        return "A"
    if target in {"NDX", "IXIC"} or code in ETF_TO_INDEX_MAP:
        mapped = ETF_TO_INDEX_MAP.get(code, "")
        if mapped in {"NDX", "IXIC"}:
            return "B"
        if mapped in {"000300", "000016", "000905", "000852"}:
            return "A"
        if mapped in {"399006", "000688"}:
            return "C"
    if target in INDEX_TYPE_C:
        return "C"
    # 默认 A 类
    return "A"


def get_pe_info(code: str, index_code: Optional[str]) -> PEInfo:
    """获取指数 PE 分位信息"""
    target = index_code or code
    
    # 先尝试获取关联指数的分位
    if index_code:
        pct_data = get_index_pct(index_code)
        return PEInfo(
            code=index_code,
            name=_get_index_name(index_code),
            pe_pct=pct_data.get("pe_pct"),
            band=pct_data.get("band", "unknown")
        )
    
    # 如果是 ETF，尝试获取其映射指数的分位
    if code in ETF_TO_INDEX_MAP:
        mapped = ETF_TO_INDEX_MAP[code]
        pct_data = get_index_pct(mapped)
        return PEInfo(
            code=mapped,
            name=_get_index_name(mapped),
            pe_pct=pct_data.get("pe_pct"),
            band=pct_data.get("band", "unknown")
        )
    
    # 直接查询
    pct_data = get_index_pct(target)
    return PEInfo(
        code=target,
        name=_get_index_name(target),
        pe_pct=pct_data.get("pe_pct"),
        band=pct_data.get("band", "unknown")
    )


def _get_index_name(code: str) -> str:
    """获取指数名称"""
    for c, (secid, name) in WATCHED_INDICES.items():
        if c == code:
            return name
    for csi, name in CSI_INDICES.items():
        if csi == code:
            return name
    if code == "NDX":
        return "纳斯达克100"
    if code == "IXIC":
        return "纳斯达克综合"
    return code


# ──────────────── 持仓计算 ────────────────────────────

def calc_holdings() -> list[HoldingItem]:
    """计算当前持仓（含真实行情市值）"""
    db: Session = SessionLocal()
    try:
        # 获取所有交易记录（price > 0.01 排除纯分红记录）
        trades = (
            db.query(TradeRecord)
            .filter(TradeRecord.price > 0.01)
            .order_by(TradeRecord.code, TradeRecord.trade_date)
            .all()
        )

        # 按标的分组计算持仓成本（FIFO）
        holdings_map: dict[str, dict] = {}
        for t in trades:
            if t.code not in holdings_map:
                holdings_map[t.code] = {
                    "name": t.name,
                    "qty": 0,
                    "cost": 0.0,
                }

            if t.trade_type == "buy":
                holdings_map[t.code]["qty"] += t.quantity
                holdings_map[t.code]["cost"] += t.price * t.quantity + t.fee
            elif t.trade_type == "sell":
                # FIFO：按平均成本减少
                if holdings_map[t.code]["qty"] > 0:
                    avg_cost = holdings_map[t.code]["cost"] / holdings_map[t.code]["qty"]
                    holdings_map[t.code]["cost"] -= avg_cost * t.quantity
                    holdings_map[t.code]["cost"] = max(0, holdings_map[t.code]["cost"])
                holdings_map[t.code]["qty"] -= t.quantity

        # 过滤净持仓（qty > 0）
        active_codes = [code for code, d in holdings_map.items() if d["qty"] > 0]
        if not active_codes:
            return []

        # 批量获取实时行情
        quotes = fetch_realtime_batch(active_codes)
        quote_map = {q.get("code", ""): q for q in quotes}

        # 获取自选股关联指数
        watchlist = db.query(WatchlistStock).all()
        watchlist_map = {w.code: w for w in watchlist}

        # 计算市值
        holdings = []
        total_value = 0.0
        total_cost = 0.0

        for code, data in holdings_map.items():
            if data["qty"] <= 0:
                continue

            # 优先用实时价格，兜底用成本价
            quote = quote_map.get(code, {})
            current_price = quote.get("price", 0)
            if not current_price or current_price <= 0:
                current_price = data["cost"] / data["qty"]  # 用持仓均价

            avg_cost = data["cost"] / data["qty"]
            market_value = current_price * data["qty"]
            profit = market_value - data["cost"]
            profit_pct = (profit / data["cost"] * 100) if data["cost"] > 0 else 0

            total_cost += data["cost"]
            total_value += market_value

            watch = watchlist_map.get(code)
            index_code = watch.index_code if watch else None

            holdings.append(HoldingItem(
                code=code,
                name=data["name"],
                stock_type="stock",
                index_code=index_code,
                index_type=get_index_type(code, index_code),
                qty=data["qty"],
                cost=round(data["cost"], 2),
                cost_per_unit=round(avg_cost, 4),
                market_value=round(market_value, 2),
                profit=round(profit, 2),
                profit_pct=round(profit_pct, 2),
                weight=0,
            ))

        # 计算仓位占比
        for h in holdings:
            if total_value > 0:
                h.weight = round(h.market_value / total_value * 100, 2)

        return holdings
    finally:
        db.close()


def calc_position_summary(holdings: list[HoldingItem]) -> PositionSummary:
    """计算持仓汇总"""
    total_cost = sum(h.cost for h in holdings)
    total_market_value = sum(h.market_value for h in holdings)
    total_profit = total_market_value - total_cost
    total_profit_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0
    
    return PositionSummary(
        total_cost=round(total_cost, 2),
        total_market_value=round(total_market_value, 2),
        total_profit=round(total_profit, 2),
        total_profit_pct=round(total_profit_pct, 2),
        holdings=holdings
    )


def _calc_drawdown(current_profit: float, peak_profit: float) -> tuple[float, float]:
    """计算回撤金额和百分比。
    仅在当前盈利 > 0 且历史最高盈利 > 0 时计算回撤。
    亏损时回撤为 0。
    """
    if current_profit <= 0 or peak_profit <= 0:
        return 0.0, 0.0
    drawdown = peak_profit - current_profit
    drawdown_pct = round(drawdown / peak_profit * 100, 2) if peak_profit > 0 else 0.0
    return round(drawdown, 2), drawdown_pct


def get_peak_profit(code: str) -> PeakProfitInfo:
    """获取历史最高浮盈信息"""
    db: Session = SessionLocal()
    try:
        record = db.query(PortfolioPeakProfit).filter(PortfolioPeakProfit.code == code).first()
        if not record:
            return PeakProfitInfo(
                peak_profit=0.0,
                peak_date=None,
                current_profit=0.0,
                drawdown=0.0,
                drawdown_pct=0.0
            )
        return PeakProfitInfo(
            peak_profit=record.peak_profit,
            peak_date=str(record.peak_date) if record.peak_date else None,
            current_profit=0.0,  # 后续填充
            drawdown=0.0,
            drawdown_pct=0.0
        )
    finally:
        db.close()


def update_peak_profit(code: str, current_profit: float) -> PeakProfitInfo:
    """更新历史最高浮盈"""
    db: Session = SessionLocal()
    try:
        record = db.query(PortfolioPeakProfit).filter(PortfolioPeakProfit.code == code).first()
        today = date.today()
        
        if not record:
            record = PortfolioPeakProfit(
                code=code,
                peak_profit=current_profit,
                peak_date=today
            )
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


# ──────────────── 操作建议计算 ────────────────────────────

def calc_action(holding: HoldingItem, pe_info: PEInfo, peak_info: PeakProfitInfo) -> OperationAdvice:
    """计算操作建议"""
    index_type = holding.index_type or get_index_type(holding.code, holding.index_code)
    pe_pct = pe_info.pe_pct
    pe_band = pe_info.band
    
    current_profit = holding.profit
    peak_profit = peak_info.peak_profit
    drawdown, drawdown_pct = _calc_drawdown(current_profit, peak_profit)
    
    # 更新历史最高浮盈
    update_peak_profit(holding.code, current_profit)
    
    action = "持有"
    action_ratio = None
    action_desc = ""
    reason = ""
    
    # Step 1: 根据 PE 分位判断
    if pe_pct is not None and pe_pct > 70:
        # PE 高估，检查回撤
        if drawdown_pct > 40:
            action = "清仓"
            action_ratio = 1.0
            action_desc = f"回撤 {drawdown_pct}% 超过 40%，保命优先，无条件清仓"
            reason = f"PE {pe_pct}% 极度高估，回撤严重"
        elif drawdown_pct > 25:
            action = "大幅减仓"
            action_ratio = 0.8
            action_desc = f"回撤 {drawdown_pct}%，建议减仓 80%"
            reason = f"PE {pe_pct}% 高估，趋势走弱"
        elif drawdown_pct > 15:
            action = "减仓"
            action_ratio = 0.4
            action_desc = f"回撤 {drawdown_pct}%，建议减仓 40%"
            reason = f"PE {pe_pct}% 高估，利润明显流失"
        else:
            action = "持仓观望"
            action_desc = f"PE {pe_pct}% 高估但回撤仅 {drawdown_pct}%，正常波动"
            reason = "高位震荡，暂不止盈"
    elif pe_pct is not None and pe_pct <= 70:
        # PE 正常或低估，只买不卖
        # A/B类：<=20% 极度低估(×2)，<=30% 低估(×1.5)
        # C类：<=25% 极度低估(×1.5)，<=40% 低估(持有)
        if index_type == "C":
            # C类（窄基）：更保守的阈值
            if pe_pct <= 25:
                action = "加半买入"
                action_ratio = 1.5
                action_desc = f"PE {pe_pct}% 极度低估，建议加半定投"
                reason = "C类极度低估区间"
            elif pe_pct <= 40:
                action = "正常持有"
                action_desc = f"PE {pe_pct}% 低估，正常持有"
                reason = "C类低估区间"
            else:
                action = "减半持有"
                action_ratio = 0.5
                action_desc = f"PE {pe_pct}% 合理偏高，减半定投"
                reason = "C类合理区间"
        else:
            # A类（宽基）/ B类（成长）
            if pe_pct <= 20:
                action = "加倍买入"
                action_ratio = 2.0
                action_desc = f"PE {pe_pct}% 极度低估，建议加倍定投"
                reason = f"{index_type}类极度低估区间"
            elif pe_pct <= 30:
                action = "加半买入"
                action_ratio = 1.5
                action_desc = f"PE {pe_pct}% 低估，建议加半定投"
                reason = f"{index_type}类低估区间"
            else:
                action = "正常持有"
                action_desc = f"PE {pe_pct}% 合理，正常持有"
                reason = "估值合理区间"
    else:
        # 无 PE 数据
        action = "正常持有"
        action_desc = "暂无估值数据，正常持有"
        reason = "估值数据缺失"
    
    return OperationAdvice(
        code=holding.code,
        name=holding.name,
        stock_type=holding.stock_type,
        index_type=index_type,
        market_value=holding.market_value,
        cost=holding.cost,
        qty=holding.qty,
        cost_per_unit=holding.cost_per_unit,
        profit=holding.profit,
        profit_pct=holding.profit_pct,
        pe_pct=pe_pct,
        pe_band=pe_band,
        current_profit=round(current_profit, 2),
        peak_profit=peak_profit,
        drawdown=round(drawdown, 2),
        drawdown_pct=drawdown_pct,
        action=action,
        action_ratio=action_ratio,
        action_desc=action_desc,
        reason=reason
    )


# ──────────────── API 路由 ────────────────────────────

@router.get("/holdings", response_model=PositionSummary)
async def get_holdings():
    """获取当前持仓汇总"""
    holdings = calc_holdings()
    return calc_position_summary(holdings)


@router.post("/advices", response_model=PortfolioAdvices)
async def get_advices(payload: dict = Body(default={})):
    """获取所有持仓的操作建议。
    payload 可选包含 manual_types: {code: 'A'|'B'|'C'} 手动覆盖类型。
    """
    manual_types = (payload or {}).get("manual_types", {}) or {}
    holdings = calc_holdings()

    advices = []
    for holding in holdings:
        # 如果有手动类型覆盖，用 model_copy 复制后覆盖
        if holding.code in manual_types:
            holding = holding.model_copy(update={"index_type": manual_types[holding.code]})

        pe_info = get_pe_info(holding.code, holding.index_code)
        peak_info = get_peak_profit(holding.code)
        # 填充当前浮盈到 peak_info
        peak_info.current_profit = holding.profit
        peak_info.drawdown, peak_info.drawdown_pct = _calc_drawdown(holding.profit, peak_info.peak_profit)

        advice = calc_action(holding, pe_info, peak_info)
        advices.append(advice)
    
    # 计算汇总
    total_profit = sum(a.current_profit for a in advices)
    peak_profit = max((a.peak_profit for a in advices), default=0)
    
    return PortfolioAdvices(
        holdings=advices,
        summary={
            "total_holdings": len(advices),
            "total_profit": round(total_profit, 2),
            "total_peak_profit": round(peak_profit, 2),
            "need_action_count": sum(1 for a in advices if a.action in ["清仓", "大幅减仓", "减仓", "加倍买入", "加半买入"])
        }
    )


@router.post("/update-peak")
async def post_update_peak(code: str, current_profit: float):
    """手动更新某标的的历史最高浮盈"""
    result = update_peak_profit(code, current_profit)
    return {"code": code, "result": result}


@router.get("/pe-info/{code}")
async def get_pe_info_api(code: str):
    """获取某标的关联指数的 PE 信息"""
    db: Session = SessionLocal()
    try:
        watch = db.query(WatchlistStock).filter(WatchlistStock.code == code).first()
        index_code = watch.index_code if watch else None
        pe_info = get_pe_info(code, index_code)
        return pe_info
    finally:
        db.close()
