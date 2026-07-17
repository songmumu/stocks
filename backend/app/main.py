"""FastAPI 主入口"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routers import stocks, market, trades, valuation, watchlist_signals, holding_percentiles, custom_indices


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="个人交易系统",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router)
app.include_router(market.router)
app.include_router(trades.router)
app.include_router(valuation.router)
app.include_router(watchlist_signals.router)
app.include_router(holding_percentiles.router)
app.include_router(custom_indices.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
