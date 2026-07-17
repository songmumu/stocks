import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// ── 大盘行情 ──

export function getCurrentIndices() {
  return api.get('/market/indices')
}

export function getIndexHistory(code = 'sh', days = 120) {
  return api.get('/market/index/history', { params: { code, days } })
}

// ── 自选股 ──

export function getWatchlist() {
  return api.get('/stocks/watchlist')
}

export function addWatchlist(data) {
  return api.post('/stocks/watchlist', data)
}

export function removeWatchlist(id) {
  return api.delete(`/stocks/watchlist/${id}`)
}

export function searchStocks(keyword) {
  return api.get('/stocks/search', { params: { keyword } })
}

export function getRealtimeQuote(code) {
  return api.get(`/stocks/quote/${code}`)
}

export function getStockHistory(code, days = 120) {
  return api.get(`/stocks/history/${code}`, { params: { days } })
}

// ── 估值 ──

export function getIndexValuation() {
  return api.get('/valuation/indices')
}

// ── 指数关联 ──

export function getAvailableIndices() {
  return api.get('/stocks/available-indices')
}

export function linkIndex(stockId, indexCode) {
  return api.put(`/stocks/watchlist/${stockId}/link-index`, { index_code: indexCode })
}

// ── 手动填写的 10 年分位（指数估值页用） ──

export function getHoldingPercentile(code) {
  return api.get(`/valuation/holding-percentile/${code}`)
}

export function updateHoldingPercentile(code, data) {
  return api.put(`/valuation/holding-percentile/${code}`, data)
}

export function deleteHoldingPercentile(code) {
  return api.delete(`/valuation/holding-percentile/${code}`)
}

// ── 交易记录 ──

export function getTrades() {
  return api.get('/trades')
}

export function addTrade(data) {
  return api.post('/trades', data)
}

export function addTradesBatch(data) {
  return api.post('/trades/batch', data)
}

export function deleteTrade(id) {
  return api.delete(`/trades/${id}`)
}

export function getDividends() {
  return api.get('/trades/dividends')
}

export function addDividend(data) {
  return api.post('/trades/dividends', data)
}
