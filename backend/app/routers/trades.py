"""交易记录 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import TradeRecord
from app.schemas import TradeRecordCreate, TradeRecordOut, DividendRecordCreate, DividendRecordOut

router = APIRouter(prefix="/api/trades", tags=["交易记录"])


@router.get("", response_model=List[TradeRecordOut])
def list_trades(db: Session = Depends(get_db)):
    """列出所有交易记录，排除分红占位记录，按交易日期倒序"""
    return (
        db.query(TradeRecord)
        .filter((TradeRecord.price > 0.01) | (TradeRecord.dividend <= 0))
        .order_by(TradeRecord.trade_date.desc())
        .all()
    )


@router.post("", response_model=TradeRecordOut, status_code=201)
def add_trade(item: TradeRecordCreate, db: Session = Depends(get_db)):
    """新增一笔交易记录"""
    trade = TradeRecord(**item.model_dump())
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


@router.post("/batch", response_model=List[TradeRecordOut], status_code=201)
def add_trades_batch(items: List[TradeRecordCreate], db: Session = Depends(get_db)):
    """批量新增交易记录（同一只股票的多笔操作）"""
    if not items:
        return []
    if len(items) > 500:
        raise HTTPException(400, f"单次最多 500 笔（当前 {len(items)}）")
    rows = [TradeRecord(**it.model_dump()) for it in items]
    db.add_all(rows)
    db.commit()
    for r in rows:
        db.refresh(r)
    return rows


@router.delete("/{trade_id}", status_code=204)
def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    """删除一条交易记录"""
    trade = db.query(TradeRecord).filter(TradeRecord.id == trade_id).first()
    if not trade:
        raise HTTPException(404, "未找到该交易记录")
    db.delete(trade)
    db.commit()
    return


# ─── 分红记录（独立接口，不混入交易表单） ───────────────────────────────────────

@router.get("/dividends", response_model=List[DividendRecordOut])
def list_dividends(db: Session = Depends(get_db)):
    """列出所有有分红的记录（dividend > 0），按日期倒序"""
    return (
        db.query(TradeRecord)
        .filter(TradeRecord.dividend > 0)
        .order_by(TradeRecord.trade_date.desc())
        .all()
    )


@router.post("/dividends", response_model=DividendRecordOut, status_code=201)
def add_dividend(item: DividendRecordCreate, db: Session = Depends(get_db)):
    """新增一条独立分红记录（不入买卖统计）"""
    trade = TradeRecord(
        code=item.code,
        name=item.name,
        trade_type="buy",          # 占位，不参与买卖统计
        trade_date=item.trade_date,
        price=0.01,                # 占位价格
        quantity=1,                 # 占位数量
        fee=0,
        dividend=item.dividend,
        notes=item.notes,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade
