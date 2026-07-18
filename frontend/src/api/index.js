import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// ── Token 管理 ──
const TOKEN_KEY = 'trading_token'
const USER_KEY  = 'trading_user'
const ROLE_KEY  = 'trading_role'

// ── 登录态 ──
export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}
export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY); localStorage.removeItem(ROLE_KEY) }
}
export function getRole() {
  return localStorage.getItem(ROLE_KEY) || ''
}
export function setRole(role) {
  if (role) localStorage.setItem(ROLE_KEY, role)
  else localStorage.removeItem(ROLE_KEY)
}
export function isAdmin() {
  return getRole() === 'admin'
}
export function getUsername() {
  return localStorage.getItem(USER_KEY) || ''
}
export function setUsername(name) {
  if (name) localStorage.setItem(USER_KEY, name)
  else localStorage.removeItem(USER_KEY)
}
export function isLoggedIn() {
  return !!getToken()
}

// 自动附带 Bearer token
api.interceptors.request.use(config => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 401 全局兜底：token 失效则清掉并跳登录页
api.interceptors.response.use(
  resp => resp,
  err => {
    if (err.response?.status === 401 && getToken() && location.pathname !== '/login') {
      setToken(null)
      location.href = '/login'
    }
    return Promise.reject(err)
  }
)

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

// ── 手动填写的 10 年分位 ──
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

// ── 我的持仓（操作系统） ──
export function getPortfolioHoldings() {
  return api.get('/portfolio/holdings')
}
export function getPortfolioAdvices(manualTypes = {}) {
  return api.post('/portfolio/advices', { manual_types: manualTypes })
}
export function getPortfolioPEInfo(code) {
  return api.get(`/portfolio/pe-info/${code}`)
}
export function updatePortfolioPeak(code, currentProfit) {
  return api.post('/portfolio/update-peak', null, { params: { code, current_profit: currentProfit } })
}

// ── 后台：登录 / 用户管理 ──
export function login(username, password) {
  return api.post('/auth/login', { username, password })
}
export function logoutApi() {
  return api.post('/auth/logout')
}
export function getMe() {
  return api.get('/auth/me')
}
export function changeMyPassword(oldPassword, newPassword) {
  return api.post('/auth/change-password', { old_password: oldPassword, new_password: newPassword })
}
export function listUsers(params = {}) {
  return api.get('/users', { params })
}
export function createUser(data) {
  return api.post('/users', data)
}
export function updateUser(id, data) {
  return api.patch(`/users/${id}`, data)
}
export function deleteUser(id) {
  return api.delete(`/users/${id}`)
}
