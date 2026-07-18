"""数据 schema"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import date, datetime


# ── 自选股 ──

class WatchlistStockCreate(BaseModel):
    code: str = Field(..., description="股票/基金代码")
    name: str
    exchange: Optional[str] = "SSE"
    stock_type: Optional[str] = "stock"
    notes: Optional[str] = ""


class WatchlistStockUpdate(BaseModel):
    name: Optional[str] = None
    exchange: Optional[str] = None
    stock_type: Optional[str] = None
    notes: Optional[str] = None
    index_code: Optional[str] = None


class WatchlistStockOut(BaseModel):
    id: int
    code: str
    name: str
    exchange: str
    stock_type: str
    notes: str
    index_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── 交易记录 ──

class TradeRecordCreate(BaseModel):
    code: str
    name: str
    trade_type: str = Field(..., pattern=r"^(buy|sell)$")
    trade_date: date
    price: float = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    fee: float = 0.0
    dividend: float = 0.0
    notes: str = ""


class TradeRecordOut(BaseModel):
    id: int
    code: str
    name: str
    trade_type: str
    trade_date: date
    price: float
    quantity: int
    fee: float
    dividend: float
    notes: str
    created_at: datetime


class DividendRecordCreate(BaseModel):
    """独立分红记录 — 不强制要求价格/数量/方向"""
    code: str
    name: str
    trade_date: date
    dividend: float = Field(..., gt=0)
    notes: str = ""


class DividendRecordOut(BaseModel):
    id: int
    code: str
    name: str
    trade_date: date
    dividend: float
    notes: str
    created_at: datetime

    model_config = {"from_attributes": True}

    model_config = {"from_attributes": True}


# ── 大盘行情 ──

class MarketIndexOut(BaseModel):
    code: str
    name: str
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: float
    change_pct: float


# ── 估值 ──

class IndexValuationOut(BaseModel):
    """单个宽基指数的 PE/PB 估值，含历史分位"""
    code: str           # 如 000300
    name: str           # 如 沪深300
    secid: str          # 腾讯 secid，如 sh000300
    price: Optional[float]
    pct: Optional[float]       # 今日涨跌%
    pe: Optional[float]
    pb: Optional[float]
    pe_pct: Optional[float]    # PE 历史分位（0-100）
    pb_pct: Optional[float]    # PB 历史分位（0-100）
    history_days: int = 0       # 快照历史天数
    band: str = "unknown"     # extreme_low/low/normal/high/extreme_high/unknown


class FundValuationOut(BaseModel):
    """场外主动基金的 NAV 分位"""
    code: str
    nav: float
    change_pct: float
    percentile: Optional[float]   # NAV 历史分位
    history_count: int
    valid: bool
    band: str = "unknown"


# ── 用户手动填写的 10 年历史分位 ──

class HoldingPercentileUpdate(BaseModel):
    """手动填写分位：PE / PB（0-100），指数分位专用"""
    pe_pct: Optional[float] = Field(None, ge=0, le=100)
    pb_pct: Optional[float] = Field(None, ge=0, le=100)
    note: Optional[str] = ""


class HoldingPercentileOut(BaseModel):
    code: str
    pe_pct: Optional[float] = None
    pb_pct: Optional[float] = None
    note: str = ""
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── 自选指数 ──

class CustomIndexCreate(BaseModel):
    code: str = Field(..., description="指数代码，如 000300 / 399006")
    name: str = Field(..., description="指数名称，如 沪深300 / 创业板指")


class CustomIndexOut(BaseModel):
    id: int
    code: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 用户管理（后台） ──

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=32)
    password: str = Field(..., min_length=6, max_length=64)

class LoginResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         "UserOut"

class UserBase(BaseModel):
    username:  str                       = Field(..., min_length=2, max_length=32)
    role:      Literal["admin", "user"]  = "user"
    is_active: bool                      = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=64)

class UserUpdate(BaseModel):
    role:      Optional[Literal["admin", "user"]] = None
    is_active: Optional[bool] = None
    password:  Optional[str]   = Field(None, min_length=6, max_length=64)

class UserOut(UserBase):
    id:            int
    last_login_at: Optional[datetime] = None
    created_at:    datetime
    updated_at:    datetime

    model_config = ConfigDict(from_attributes=True)

class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6, max_length=64)
    new_password: str = Field(..., min_length=6, max_length=64)

LoginResponse.model_rebuild()
