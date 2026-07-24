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


class PortfolioPeakProfit(Base):
    """持仓历史最高浮盈记录（单标的建仓以来）"""
    __tablename__ = "portfolio_peak_profits"

    code = Column(String(12), primary_key=True)               # 股票/ETF 代码
    peak_profit = Column(Float, default=0.0)                  # 历史最高浮盈金额
    peak_date = Column(Date, nullable=True)                   # 达到最高浮盈的日期
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PriceHistory(Base):
    """每日价格历史（用于均线/放量止损预警）"""
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(12), nullable=False, index=True)
    date = Column(Date, nullable=False)                # 交易日期
    close_price = Column(Float, nullable=False)        # 收盘价
    volume = Column(Float, default=0.0)                # 成交量（股数）
    open_price = Column(Float, default=0.0)            # 开盘价
    high_price = Column(Float, default=0.0)            # 最高价
    low_price = Column(Float, default=0.0)             # 最低价
    created_at = Column(DateTime, server_default=func.now())


class User(Base):
    """后台用户（后台管理）"""
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    username      = Column(String(32), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)        # passlib PBKDF2
    role          = Column(String(16), default="user")         # admin / user
    is_active     = Column(Integer, default=1)                 # 1 启用 / 0 停用
    last_login_at = Column(DateTime, nullable=True)
    created_at    = Column(DateTime, server_default=func.now())
    updated_at    = Column(DateTime, server_default=func.now(), onupdate=func.now())
