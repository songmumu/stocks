"""数据模型"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Text, func
from app.database import Base


class WatchlistStock(Base):
    """自选股/持仓股"""
    __tablename__ = "watchlist_stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(12), nullable=False, index=True)          # 股票代码，如 "600519"
    name = Column(String(32), nullable=False)                       # 股票名称
    exchange = Column(String(8), default="SSE")                     # SSE/SZSE
    stock_type = Column(String(8), default="stock")                 # stock / fund
    notes = Column(Text, default="")                                # 备注
    index_code = Column(String(20), nullable=True, index=True)          # 关联指数代码，如 000300
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class TradeRecord(Base):
    """交易记录"""
    __tablename__ = "trade_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(12), nullable=False, index=True)
    name = Column(String(32), nullable=False)
    trade_type = Column(String(4), nullable=False)                  # buy / sell
    trade_date = Column(Date, nullable=False)
    price = Column(Float, nullable=False)                           # 成交价
    quantity = Column(Integer, nullable=False)                      # 股数/份额
    fee = Column(Float, default=0.0)                                # 手续费
    dividend = Column(Float, default=0.0)                           # 分红金额（到该笔交易日期累计，或当日新增）
    notes = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())


class IndexValuationSnapshot(Base):
    """指数 PE/PB 历史快照（每日一档）
    长期积累后可计算 10 年分位。初始默认以 Tencent API 为实时源。
    """
    __tablename__ = "index_valuation_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(8), nullable=False, index=True)       # 如 000300
    snapshot_date = Column(Date, nullable=False, index=True)
    pe = Column(Float, nullable=True)
    pb = Column(Float, nullable=True)
    source = Column(String(16), default="tencent")             # tencent / seed
    created_at = Column(DateTime, server_default=func.now())


class HoldingPercentile(Base):
    """用户手动填写的 10 年历史分位（场外基金 NAV / 个股 PE-PB / ETF 映射指数 PE-PB）

    优先级高于自动计算的估值，自动信号降级为参考。
    """
    __tablename__ = "holding_percentiles"

    code = Column(String(12), primary_key=True)                # 指数代码（如 000300）
    pe_pct = Column(Float, nullable=True)                       # PE 10 年分位 0-100
    pb_pct = Column(Float, nullable=True)                       # PB 10 年分位 0-100
    note = Column(String(255), default="")                      # 备注：数据来源 / 估值日期
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CustomIndex(Base):
    """用户自选添加的宽基/行业指数"""
    __tablename__ = "custom_indices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(64), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class HiddenIndex(Base):
    """用户已隐藏的指数（用于删除 CSI 行业指数、宽基指数或自定义指数后保留可恢复能力）"""
    __tablename__ = "hidden_indices"

    code = Column(String(20), primary_key=True)               # 指数代码
    name = Column(String(64), nullable=False)                 # 删除时快照
    source = Column(String(16), default="custom")             # custom / csi / tencent
    created_at = Column(DateTime, server_default=func.now())
