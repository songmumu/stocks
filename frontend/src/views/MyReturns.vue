<template>
  <div class="my-returns">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>我的收益</h2>
      <el-button size="small" link @click="loadData" :loading="loading">
        <span style="font-size:12px;color:#909399;">刷新</span>
      </el-button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" v-loading="true" class="loading-wrap" style="height:300px;"></div>

    <div v-else-if="hasData">
      <!-- 顶部统计卡片 -->
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-label">累计收益率</div>
          <div class="stat-value" :class="totalReturnPct >= 0 ? 'up' : 'down'">
            {{ totalReturnPct >= 0 ? '+' : '' }}{{ totalReturnPct.toFixed(2) }}%
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">累计收益（含已清仓）</div>
          <div class="stat-value" :class="totalProfit >= 0 ? 'up' : 'down'">
            {{ totalProfit >= 0 ? '+' : '' }}¥{{ formatMoney(totalProfit) }}
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">持仓浮盈</div>
          <div class="stat-value" :class="holdingProfit >= 0 ? 'up' : 'down'">
            {{ holdingProfit >= 0 ? '+' : '' }}¥{{ formatMoney(holdingProfit) }}
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">最大回撤</div>
          <div class="stat-value down">{{ maxDrawdownPct.toFixed(2) }}%</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">盈利天数 / 总天数</div>
          <div class="stat-value">{{ profitDays }} / {{ totalDays }}</div>
        </div>
      </div>

      <!-- 收益曲线 + 收益日历 -->
      <div class="main-panels">
        <div class="panel panel-left">
          <div class="panel-title">
            收益曲线
            <div class="display-toggle" style="margin-left:12px;">
              <button :class="{active: curveMode==='percent'}" @click="curveMode='percent'">收益率</button>
              <button :class="{active: curveMode==='amount'}" @click="curveMode='amount'">收益金额</button>
            </div>
          </div>
          <div class="chart-wrap">
            <div v-if="curveData.length === 0" class="empty-panel">
              <p>暂无收益数据</p>
            </div>
            <div ref="curveRef" class="chart-container"></div>
          </div>
        </div>

        <div class="panel panel-right">
          <div class="panel-title">收益日历</div>

          <!-- 视图切换 -->
          <div class="cal-controls">
            <div class="display-toggle">
              <button :class="{active: viewMode==='day'}"   @click="viewMode='day'">日</button>
              <button :class="{active: viewMode==='week'}"   @click="viewMode='week'">周</button>
              <button :class="{active: viewMode==='month'}"  @click="viewMode='month'">月</button>
              <button :class="{active: viewMode==='year'}"   @click="viewMode='year'">年</button>
            </div>
            <div class="display-toggle" style="margin-left:8px;">
              <button :class="{active: displayMode==='pct'}"    @click="displayMode='pct'">%</button>
              <button :class="{active: displayMode==='amount'}"  @click="displayMode='amount'">¥</button>
            </div>
            <div class="cal-nav" v-if="viewMode !== 'year'">
              <button @click="navigatePrev">&lt;</button>
              <span>{{ navLabel }}</span>
              <button @click="navigateNext" :disabled="isCurrentPeriod">&gt;</button>
            </div>
          </div>

          <!-- 日视图 -->
          <div v-if="viewMode==='day'" class="cal-day-view">
            <div class="cal-weekdays">
              <div v-for="w in weekdays" :key="w" class="weekday">{{ w }}</div>
            </div>
            <div class="cal-grid">
              <div
                v-for="(cell, idx) in dayCells" :key="idx"
                class="cal-cell"
                :class="[getCellClass(cell), { 'is-today': cell.isToday, 'is-future': cell.isFuture, 'has-trade': cell.tradeCount > 0 }]"
                :style="getPnlStyle(cell.pnlPct, cell.isEmpty, cell.isFuture)"
                :title="cell.tradeCount ? `${cell.tradeCount} 笔交易 (买${cell.buyCount}/卖${cell.sellCount})` : ''"
              >
                <span class="cell-date">{{ cell.day }}</span>
                <span class="cell-pnl" v-if="!cell.isEmpty && !cell.isFuture">{{ getPnlText(cell) }}</span>
                <span class="cell-mark" v-if="cell.tradeCount > 0">
                  <span class="dot dot-buy" v-if="cell.buyCount">B{{ cell.buyCount }}</span>
                  <span class="dot dot-sell" v-if="cell.sellCount">S{{ cell.sellCount }}</span>
                </span>
              </div>
            </div>
          </div>

          <!-- 月视图 -->
          <div v-else-if="viewMode==='month'" class="cal-month-view">
            <div v-for="m in monthCards" :key="m.key"
              class="month-card" :style="getPnlStyle(m.pnlPct, !m.hasData, false)">
              <div class="mc-label">{{ m.label }}</div>
              <div class="mc-pnl">{{ m.hasData ? getPnlText(m) : '--' }}</div>
            </div>
          </div>

          <!-- 周视图 -->
          <div v-else-if="viewMode==='week'" class="cal-week-view">
            <div v-for="w in weekCards" :key="w.key"
              class="week-card" :style="getPnlStyle(w.pnlPct, !w.hasData, false)">
              <div class="mc-label">{{ w.label }}</div>
              <div class="mc-pnl">{{ w.hasData ? getPnlText(w) : '--' }}</div>
            </div>
          </div>

          <!-- 年视图 -->
          <div v-else-if="viewMode==='year'" class="cal-year-view">
            <div v-for="y in yearCards" :key="y.key"
              class="year-card" :style="getPnlStyle(y.pnlPct, !y.hasData, false)">
              <div class="mc-label">{{ y.label }}</div>
              <div class="mc-pnl">{{ y.hasData ? getPnlText(y) : '--' }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>暂无交易数据，请先在「交易记录」中添加记录</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import axios from 'axios'
import { getToken, getPortfolioHoldings, getPortfolioPrices } from '../api/index.js'
import echarts from '../utils/echarts'

// === refs ===
const loading    = ref(true)
const tradeList  = ref([])        // 原始交易记录
const curveData  = ref([])        // 收益曲线数据
const histMap    = ref({})        // code -> {date: close}
const curveRef   = ref(null)
const curveChart = ref(null)
const resizeObserver = ref(null)

// === 视图状态 ===
const viewMode     = ref('month')    // day | week | month | year
const displayMode  = ref('pct')     // pct | amount
const curveMode    = ref('percent')  // percent | amount

const now0 = new Date()
const currentYear  = ref(now0.getFullYear())
const currentMonth = ref(now0.getMonth() + 1)
const weekdays     = ['日','一','二','三','四','五','六']

// === computed: 核心指标 ===
const hasData = computed(() => tradeList.value.length > 0)

const totalCost = computed(() => {
  return tradeList.value
    .filter(t => t.trade_type === 'buy')
    .reduce((s, t) => s + t.price * t.quantity, 0)
})

const totalReturnPct = computed(() => {
  if (!curveData.value.length || totalCost.value === 0) return 0
  const last = curveData.value[curveData.value.length - 1]
  if (!last) return 0
  // 累计收益率 = 末点 totalProfit / 累计投入资金 totalCost
  return (last.totalProfit / totalCost.value) * 100
})

const totalProfit = computed(() => {
  if (!curveData.value.length) return 0
  return curveData.value[curveData.value.length - 1].totalProfit || 0
})

const holdingProfit = computed(() => {
  return totalProfit.value  // 简化：已清仓+持仓统一口径
})

const maxDrawdownPct = computed(() => {
  if (!curveData.value.length) return 0
  // 取近期点（后N点）的资产价值，避免历史估值为0引起的畸高回撤
  const recent = curveData.value.slice(-30)
  let peakValue = 0
  let maxDD = 0
  let cumBuy = 0
  for (const d of recent) {
    cumBuy = Math.max(cumBuy, d.totalCost || 0)
    const value = cumBuy + (d.totalProfit || 0)
    if (value > peakValue) peakValue = value
    if (peakValue > 0) {
      const dd = ((value - peakValue) / peakValue) * 100
      if (dd < maxDD) maxDD = dd
    }
  }
  return maxDD
})

const profitDays = computed(() =>
  curveData.value.filter(d => d.pnl > 0).length
)
const totalDays  = computed(() => curveData.value.length)

// === 日历 computed ===
const firstTradeDate = computed(() => {
  if (!tradeList.value.length) return null
  return tradeList.value
    .map(t => t.trade_date)
    .sort()[0]
})

// 每天 P&L map — 使用累计 P&L 的日增量，避免 close 缺失引起的跳变
const dailyPnlMap = computed(() => {
  const map = {}
  const sorted = [...curveData.value].sort((a, b) => a.date.localeCompare(b.date))
  let prevProfit = 0
  let isFirst = true
  for (const d of sorted) {
    const cumProfit = d.totalProfit || 0
    const cumCost   = d.totalCost || 0
    const cumPct    = cumCost > 0 ? (cumProfit / cumCost) * 100 : 0
    // ¥ 模式：显示累计盈亏的日增量
    const dailyPnl = isFirst ? cumProfit : cumProfit - prevProfit
    // % 模式：使用 marketPnlPct（仅市场波动），跳过买入日成本跳变
    const dailyPct = d.marketPnlPct ?? (isFirst ? 0 : cumPct - 0)
    map[d.date] = { pnl: dailyPnl, pnlPct: dailyPct, cumPnlPct: cumPct, hasData: cumCost > 0 }
    prevProfit = cumProfit
    isFirst = false
  }
  return map
})

// 日视图
const dayCells = computed(() => {
  const year  = currentYear.value
  const month = currentMonth.value
  const firstDay = new Date(year, month - 1, 1)
  const lastDay  = new Date(year, month, 0)
  const startDow = firstDay.getDay()  // 0=周日
  const today    = new Date()
  const cells = []

  for (let i = 0; i < startDow; i++) cells.push({ empty: true })
  for (let d = 1; d <= lastDay.getDate(); d++) {
    const dateStr = `${year}-${String(month).padStart(2,'0')}-${String(d).padStart(2,'0')}`
    const isToday = year === today.getFullYear() &&
                    month === today.getMonth() + 1 &&
                    d === today.getDate()
    const isFuture = new Date(year, month - 1, d) > today
    const pnlData = dailyPnlMap.value[dateStr]
    const dayTrades = tradeList.value.filter(t => t.trade_date === dateStr)
    const buyCount  = dayTrades.filter(t => t.trade_type === 'buy').length
    const sellCount = dayTrades.filter(t => t.trade_type !== 'buy').length
    cells.push({
      day: d,
      date: dateStr,
      pnl:      pnlData?.pnl        || 0,
      pnlPct:   pnlData?.cumPnlPct  || pnlData?.pnlPct || 0,  // 累计收益率 (染色用)
      dailyPct: pnlData?.pnlPct     || 0,                     // 日增量变化 (数字用)
      isEmpty: !pnlData,
      isToday,
      isFuture,
      tradeCount: dayTrades.length,
      buyCount,
      sellCount,
    })
  }
  return cells
})

// 月视图
const monthCards = computed(() => {
  const year = currentYear.value
  const cards = []
  // 按月组织：当月内各日累计 totalProfit 最后一个 vs 前月最后一个 = 该月 P&L
  const allByMonth = {}
  for (const d of curveData.value) {
    if (!d.date) continue
    const ym = d.date.slice(0, 7)
    if (!allByMonth[ym]) allByMonth[ym] = []
    allByMonth[ym].push(d)
  }
  for (let m = 1; m <= 12; m++) {
    const key = `${year}-${String(m).padStart(2,'0')}`
    const monthEntries = (allByMonth[key] || []).sort((a, b) => a.date.localeCompare(b.date))
    const hasData = monthEntries.length > 0
    // 取该月末点的 totalProfit，以及上月末点（如有）
    let monthProfit = 0
    let monthCost = 0
    let prevMonthEnd = 0
    const prevKey = `${year}-${String(m-1).padStart(2,'0')}`
    if (m > 1) {
      const prevList = allByMonth[prevKey] || []
      if (prevList.length) prevMonthEnd = prevList[prevList.length - 1].totalProfit || 0
    }
    if (hasData) {
      const lastDay = monthEntries[monthEntries.length - 1]
      monthProfit = (lastDay.totalProfit || 0) - prevMonthEnd
      monthCost   = lastDay.totalCost || 0
    }
    const pnlPct = monthCost > 0 ? (monthProfit / monthCost) * 100 : 0
    cards.push({ label: `${m}月`, key, pnl: monthProfit, pnlPct, hasData })
  }
  return cards
})

// 周视图
const weekCards = computed(() => {
  const year  = currentYear.value
  const month = currentMonth.value
  const firstDay = new Date(year, month - 1, 1)
  const lastDay  = new Date(year, month, 0)
  const cards = []
  let weekStart = new Date(firstDay)
  weekStart.setDate(weekStart.getDate() - weekStart.getDay())

  let weekIdx = 1
  while (weekStart <= lastDay) {
    const weekEnd = new Date(weekStart)
    weekEnd.setDate(weekEnd.getDate() + 6)
    const startStr = weekStart.toISOString().slice(0, 10)
    const endStr   = weekEnd.toISOString().slice(0, 10)
    const label    = `W${weekIdx}`
    const weekMap  = {}
    for (const d of curveData.value) {
      if (d.date >= startStr && d.date <= endStr) weekMap[d.date] = d
    }
    const entries = Object.values(weekMap)
    const hasData = entries.length > 0
    const pnl   = hasData ? entries.reduce((s, e) => s + (e.pnl || 0), 0) : 0
    const pnlPct = hasData
      ? entries.reduce((s, e) => s + (e.pnlPct || 0), 0) / entries.length
      : 0
    cards.push({ label, key: startStr, pnl, pnlPct, hasData })
    weekStart.setDate(weekStart.getDate() + 7)
    weekIdx++
  }
  return cards
})

// 年视图
const yearCards = computed(() => {
  const years = new Set(curveData.value.map(d => d.date?.slice(0, 4)).filter(Boolean))
  return [...years].sort().map(y => {
    const yearEntries = curveData.value.filter(d => d.date?.startsWith(y))
    const hasData = yearEntries.length > 0
    const pnl    = hasData ? yearEntries.reduce((s, e) => s + (e.pnl || 0), 0) : 0
    const pnlPct = hasData
      ? yearEntries.reduce((s, e) => s + (e.pnlPct || 0), 0) / yearEntries.length
      : 0
    return { label: `${y}年`, key: y, pnl, pnlPct, hasData }
  })
})

// 导航
const navLabel = computed(() => {
  if (viewMode.value === 'day')   return `${currentYear.value}年${currentMonth.value}月`
  if (viewMode.value === 'month') return `${currentYear.value}年`
  if (viewMode.value === 'week')  return `${currentYear.value}年${currentMonth.value}月`
  return ''
})

const isCurrentPeriod = computed(() => {
  const now = new Date()
  if (viewMode.value === 'year')  return currentYear.value  >= now.getFullYear()
  if (viewMode.value === 'month' || viewMode.value === 'week')
    return currentYear.value  >= now.getFullYear() &&
           currentMonth.value >= now.getMonth() + 1
  return false
})

function navigatePrev() {
  if (viewMode.value === 'year')  currentYear.value--
  else if (viewMode.value === 'month' || viewMode.value === 'week') {
    if (currentMonth.value === 1) { currentMonth.value = 12; currentYear.value-- }
    else currentMonth.value--
  }
}

function navigateNext() {
  if (isCurrentPeriod.value) return
  if (viewMode.value === 'year')  currentYear.value++
  else if (viewMode.value === 'month' || viewMode.value === 'week') {
    if (currentMonth.value === 12) { currentMonth.value = 1; currentYear.value++ }
    else currentMonth.value++
  }
}

// === 样式方法 ===
function getPnlStyle(pnlPct, isEmpty, isFuture) {
  if (isFuture) return { background: '#f9f9f9' }
  if (isEmpty)   return {}
  // pnlPct 是该日累计收益率 (%)，参考范围 [-20, 20]
  const pct = Math.max(-20, Math.min(20, pnlPct || 0))
  const abs = Math.abs(pct)
  let bg
  if (abs < 0.1)      bg = 'rgba(200,200,200,0.2)'
  else if (abs < 2)   bg = pct > 0 ? 'rgba(239,68,68,0.25)' : 'rgba(34,197,94,0.25)'
  else if (abs < 6)   bg = pct > 0 ? 'rgba(239,68,68,0.45)' : 'rgba(34,197,94,0.45)'
  else if (abs < 12)  bg = pct > 0 ? 'rgba(239,68,68,0.65)' : 'rgba(34,197,94,0.65)'
  else                bg = pct > 0 ? 'rgba(239,68,68,0.85)' : 'rgba(34,197,94,0.85)'
  const color = abs > 0.3 ? (pct > 0 ? '#ef4444' : '#22c55e') : '#666'
  return { background: bg, color }
}

function getPnlText(cell) {
  if (!cell) return ''
  if (displayMode.value === 'amount') {
    const p = Number(cell.pnl) || 0
    return (p >= 0 ? '+' : '') + '¥' + (p / 1000).toFixed(1) + 'k'
  }
  const pct = Number(cell.dailyPct ?? cell.pnlPct) || 0
  return (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%'
}

function getCellClass(cell) {
  if (cell.isEmpty)   return 'is-empty'
  if (cell.pnl > 0)  return 'profit'
  if (cell.pnl < 0)  return 'loss'
  return ''
}

// === 工具 ===
function formatMoney(n) {
  return Math.abs(Number(n) || 0).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

// === 数据加载 ===
async function loadData() {
  loading.value = true
  try {
    // step 1: 拉交易记录
    const token = getToken()
    const tradesRes = await axios.get('/api/trades', {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    })
    tradeList.value = tradesRes.data || []

    if (!tradeList.value.length) { loading.value = false; return }

    // step 2: 收集所有 code
    const codes = [...new Set(tradeList.value.map(t => t.code))]

    // step 3: 并行拉各标的 K 线
    const histResults = {}
    await Promise.all(codes.map(async (code) => {
      try {
        const r = await axios.get(`/api/stocks/history/${code}`, { params: { days: 720 } })
        const bars = r.data?.bars || []
        histResults[code] = {}
        for (const b of bars) histResults[code][b.date] = b
      } catch { histResults[code] = {} }
    }))
    histMap.value = histResults

    // step 4: 构建曲线
    curveData.value = buildCurveData(tradeList.value, histResults)

    // step 4.5: 用后端 /api/portfolio/history 覆盖每日 totalProfit/totalCost/cumPnlPct
    try {
      const histRes = await axios.get('/api/portfolio/history', {
        params: { days: 720 },
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      })
      const backendHistory = histRes.data?.history || []
      if (backendHistory.length) {
        const backMap = {}
        for (const h of backendHistory) backMap[h.date] = h
        curveData.value = curveData.value.map(d => {
          const b = backMap[d.date]
          if (b) {
            return {
              ...d,
              totalProfit: b.totalProfit,
              totalCost:   b.totalCost,
              pnlPct:      b.cumPnlPct,
              marketPnlPct: b.marketPnlPct,  // 仅市场波动 (跳过买入日成本跳变)
            }
          }
          return d
        })
      }
    } catch (e) { console.warn('[MyReturns] portfolio history 校正失败', e) }

    // step 5: 用 Portfolio 接口（实时价）校正末点 P&L
    try {
      const pf = await getPortfolioHoldings()
      const last = curveData.value[curveData.value.length - 1]
      if (last && pf.data) {
        const realProfit = pf.data.total_profit || 0
        const realCost   = pf.data.total_cost   || last.totalCost
        const prevProfit = curveData.value.length > 1 ? curveData.value[curveData.value.length - 2].totalProfit : 0
        last.totalProfit = realProfit
        last.totalCost   = realCost
        last.pnlPct      = realCost > 0 ? (realProfit / realCost) * 100 : 0
        last.pnl         = realProfit - prevProfit
      }
    } catch (e) { console.warn('[MyReturns] portfolio 校正失败', e) }

    // step 6: 渲染
    await nextTick()
    renderCurve()

  } catch (e) {
    console.error('[MyReturns] loadData failed', e)
  } finally {
    loading.value = false
    await nextTick()
    scheduleResize()
  }
}

function buildCurveData(trades, histMap) {
  if (!trades.length) return []

  const sorted = [...trades].sort((a, b) => a.trade_date.localeCompare(b.trade_date))
  const firstDate = sorted[0].trade_date

  // FIFO 买入批次。 code -> [{ qty, price }]
  const lots = {}
  const points = []

  let realizedProfit = 0
  let cumulativeBuyAmount = 0

  const today = new Date().toISOString().slice(0, 10)
  let curDate = new Date(firstDate)

  while (curDate.toISOString().slice(0, 10) <= today) {
    const dateStr = curDate.toISOString().slice(0, 10)
    const dayTrades = sorted.filter(t => t.trade_date === dateStr)

    let dailyRealized = 0

    for (const t of dayTrades) {
      if (!lots[t.code]) lots[t.code] = []

      if (t.trade_type === 'buy') {
        lots[t.code].push({ qty: t.quantity, price: t.price })
        cumulativeBuyAmount += t.price * t.quantity
      } else {
        // FIFO 卖出
        const qtyToSell = Math.min(t.quantity, lots[t.code].reduce((s, l) => s + l.qty, 0))
        let soldCost = 0
        let remaining = qtyToSell
        while (remaining > 0 && lots[t.code].length) {
          const top = lots[t.code][0]
          const take = Math.min(remaining, top.qty)
          soldCost += take * top.price
          top.qty -= take
          remaining -= take
          if (top.qty <= 0) lots[t.code].shift()
        }
        const sellAmount = t.price * qtyToSell
        dailyRealized += sellAmount - soldCost
      }
    }
    realizedProfit += dailyRealized

    // 计算当前持仓市值（使用当天 close）
    let totalCost = 0
    let totalVal  = 0
    let totalQty  = 0
    for (const [code, ls] of Object.entries(lots)) {
      const qty = ls.reduce((s, l) => s + l.qty, 0)
      if (qty <= 0) continue
      const cost = ls.reduce((s, l) => s + l.qty * l.price, 0)
      totalCost += cost
      totalQty  += qty
      const close = histMap[code]?.[dateStr]?.close
      if (close && qty > 0) totalVal += close * qty
    }
    const floatingProfit = totalVal - totalCost
    const totalProfit = realizedProfit + floatingProfit

    // 当日 P&L（相对前一天 totalProfit）
    let dailyPnl = 0
    if (points.length > 0) {
      dailyPnl = totalProfit - points[points.length - 1].totalProfit
    } else {
      // 首点：当日开始持仓之前的 total = 0，所以 dailyPnl = totalProfit - 0
      dailyPnl = totalProfit - dailyRealized
    }

    points.push({
      date: dateStr,
      pnl: dailyPnl,
      totalProfit,
      totalCost: totalCost || 0,
      pnlPct: cumulativeBuyAmount > 0 ? (totalProfit / cumulativeBuyAmount) * 100 : 0,
      tradingPnl: dailyRealized,        // 今日已实现盈亏（卖出）
      tradedAmount: dayTrades.reduce((s, t) => s + (t.price || 0) * (t.quantity || 0), 0),
    })

    curDate.setDate(curDate.getDate() + 1)
  }

  return points
}

// === ECharts ===
function renderCurve() {
  if (!curveRef.value || !curveData.value.length) return
  if (curveChart.value) { curveChart.value.dispose(); curveChart.value = null }

  curveChart.value = echarts.init(curveRef.value)

  const isAmount = curveMode.value === 'amount'
  const xData = curveData.value.map(d => d.date)
  const yData = curveData.value.map(d =>
    isAmount ? d.totalProfit : (d.totalCost > 0 ? (d.totalProfit / d.totalCost) * 100 : 0)
  )
  const color = yData[yData.length - 1] >= 0 ? '#ef4444' : '#22c55e'

  curveChart.value.setOption({
    tooltip: {
      trigger: 'axis',
      formatter(params) {
        const p = params[0]
        const sign = isAmount ? (p.value >= 0 ? '+' : '') : (p.value >= 0 ? '+' : '')
        const suffix = isAmount ? '¥' : '%'
        return `${p.axisValue}<br/>${sign}${Math.abs(p.value).toFixed(2)}${suffix}`
      }
    },
    grid: { left: 50, right: 20, top: 10, bottom: 30 },
    xAxis: {
      type: 'category', data: xData,
      axisLabel: { fontSize: 10, color: '#999', rotate: 30 },
      axisLine: { lineStyle: { color: '#eee' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        fontSize: 10, color: '#999',
        formatter: v => isAmount ? (v >= 0 ? '+' : '') + (v/1000).toFixed(0) + 'k' : v.toFixed(1) + '%'
      },
      splitLine: { lineStyle: { color: '#f5f5f5' } },
    },
    series: [{
      type: 'line',
      data: yData,
      smooth: true,
      symbol: 'none',
      lineStyle: { color, width: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: color + '40' },
          { offset: 1, color: color + '05' }
        ])
      },
    }]
  }, true)
}

function scheduleResize() {
  nextTick(() => {
    setTimeout(() => {
      curveChart.value?.resize()
    }, 100)
    setTimeout(() => {
      curveChart.value?.resize()
    }, 350)
  })
}

// === 生命周期 ===
onMounted(() => {
  loadData()
  nextTick(() => {
    if (curveRef.value) {
      resizeObserver.value = new ResizeObserver(() => {
        const inst = curveChart.value
        if (inst && typeof inst.resize === 'function') inst.resize()
      })
      resizeObserver.value.observe(curveRef.value)
    }
  })
})

onUnmounted(() => {
  const ro = resizeObserver.value
  resizeObserver.value = null
  if (ro) ro.disconnect()
  const inst = curveChart.value
  curveChart.value = null
  if (inst && typeof inst.dispose === 'function') inst.dispose()
})

watch(curveMode, () => {
  nextTick(() => renderCurve())
})
</script>

<style scoped>
.my-returns { max-width: 1400px; margin: 0 auto; }

.page-header {
  display: flex; align-items: center; gap: 12px; margin-bottom: 16px;
}
.page-header h2 { font-size: 18px; font-weight: 600; margin: 0; }

.loading-wrap { display: flex; align-items: center; justify-content: center; }

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px; margin-bottom: 16px;
}
.stat-card {
  background: #fff; border-radius: 8px; padding: 14px 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.stat-label { font-size: 12px; color: #909399; margin-bottom: 6px; }
.stat-value { font-size: 20px; font-weight: 700; }
.stat-value.up   { color: #ef4444; }
.stat-value.down { color: #22c55e; }

.main-panels { display: grid; grid-template-columns: 1fr 380px; gap: 16px; }
@media (max-width: 900px) {
  .main-panels { grid-template-columns: 1fr; }
}

.panel {
  background: #fff; border-radius: 10px; padding: 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.panel-title {
  font-size: 14px; font-weight: 600; margin-bottom: 12px;
  display: flex; align-items: center; flex-wrap: wrap; gap: 8px;
}

.display-toggle {
  display: inline-flex; background: #f0f0f0; border-radius: 20px;
  padding: 2px; font-size: 12px;
}
.display-toggle button {
  padding: 3px 10px; border: none; background: transparent;
  border-radius: 20px; cursor: pointer; color: #666;
}
.display-toggle button.active {
  background: #fff; color: #333; font-weight: 500;
  box-shadow: 0 1px 3px rgba(0,0,0,.12);
}

.empty-panel, .empty-state {
  text-align: center; padding: 40px; color: #909399;
}
.chart-wrap { width: 100%; }
.chart-container { width: 100%; height: 300px; }

/* 日历 */
.cal-controls { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.cal-nav { display: flex; align-items: center; gap: 8px; font-size: 12px; margin-left: auto; }
.cal-nav button { border: 1px solid #ddd; background: #fff; border-radius: 4px; padding: 2px 8px; cursor: pointer; }
.cal-nav button:disabled { opacity: 0.4; cursor: default; }

.cal-weekdays { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 4px; }
.weekday { text-align: center; font-size: 11px; color: #909399; padding: 2px 0; }

.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
.cal-cell {
  border-radius: 4px; padding: 4px 2px; text-align: center;
  min-height: 44px; display: flex; flex-direction: column;
  justify-content: center; align-items: center;
  cursor: default; transition: transform .1s;
}
.cal-cell:hover { transform: scale(1.05); box-shadow: 0 2px 8px rgba(0,0,0,.15); }
.cal-cell.is-today { border: 2px solid #3b82f6; }
.cal-cell.is-future { background: #f9f9f9 !important; }
.cal-cell.is-empty { background: transparent; }
.cell-date { font-size: 11px; color: inherit; opacity: .7; }
.cell-pnl  { font-size: 11px; font-weight: 600; color: inherit; margin-top: 1px; }
.cell-mark { display: flex; gap: 2px; margin-top: 1px; font-size: 9px; font-weight: 600; }
.dot       { padding: 1px 3px; border-radius: 3px; line-height: 1; }
.dot-buy   { background: #fef2f2; color: #ef4444; }
.dot-sell  { background: #f0fdf4; color: #22c55e; }

/* 月周年视图 */
.cal-month-view { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.cal-week-view  { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.cal-year-view  { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }

.month-card, .week-card, .year-card {
  border-radius: 6px; padding: 10px 8px; text-align: center;
}
.mc-label { font-size: 11px; opacity: .7; margin-bottom: 4px; }
.mc-pnl   { font-size: 13px; font-weight: 700; }
</style>

