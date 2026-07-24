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
          <div v-if="curveData.length === 0" class="empty-panel">
            <p>暂无收益数据</p>
          </div>
          <div v-else class="chart-wrap">
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
                :class="[getCellClass(cell), { 'is-today': cell.isToday, 'is-future': cell.isFuture }]"
                :style="getPnlStyle(cell.pnlPct, cell.isEmpty, cell.isFuture)"
              >
                <span class="cell-date">{{ cell.day }}</span>
                <span class="cell-pnl" v-if="!cell.isEmpty && !cell.isFuture">{{ getPnlText(cell) }}</span>
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
  const first = curveData.value[0]
  if (!first || first.totalCost === 0) return 0
  return (first.totalProfit / first.totalCost) * 100
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
  let peak = -Infinity, maxDD = 0
  for (const d of curveData.value) {
    if (d.totalProfit > peak) peak = d.totalProfit
    const dd = peak > 0 ? ((d.totalProfit - peak) / peak) * 100 : 0
    if (dd < maxDD) maxDD = dd
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

// 每天 P&L map
const dailyPnlMap = computed(() => {
  const map = {}
  for (const d of curveData.value) {
    if (d.date) map[d.date] = { pnl: d.pnl || 0, pnlPct: d.pnlPct || 0 }
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
    cells.push({
      day: d,
      date: dateStr,
      pnl:    pnlData?.pnl    || 0,
      pnlPct: pnlData?.pnlPct || 0,
      isEmpty: !pnlData,
      isToday,
      isFuture,
    })
  }
  return cells
})

// 月视图
const monthCards = computed(() => {
  const year = currentYear.value
  const cards = []
  for (let m = 1; m <= 12; m++) {
    const label    = `${m}月`
    const key      = `${year}-${String(m).padStart(2,'0')}`
    const monthMap = {}
    for (const d of curveData.value) {
      if (d.date && d.date.startsWith(key)) {
        monthMap[d.date] = d
      }
    }
    const entries = Object.values(monthMap)
    const hasData = entries.length > 0
    const pnl   = hasData ? entries.reduce((s, e) => s + (e.pnl || 0), 0) : 0
    const pnlPct = hasData
      ? entries.reduce((s, e) => s + (e.pnlPct || 0), 0) / entries.length
      : 0
    cards.push({ label, key, pnl, pnlPct, hasData })
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
  const abs = Math.abs(pnlPct)
  let bg
  if (abs < 0.3)      bg = 'rgba(200,200,200,0.2)'
  else if (abs < 1.5) bg = pnlPct > 0 ? 'rgba(239,68,68,0.25)' : 'rgba(34,197,94,0.25)'
  else if (abs < 3)   bg = pnlPct > 0 ? 'rgba(239,68,68,0.45)' : 'rgba(34,197,94,0.45)'
  else                bg = pnlPct > 0 ? 'rgba(239,68,68,0.7)'   : 'rgba(34,197,94,0.7)'
  const color = abs > 1 ? (pnlPct > 0 ? '#ef4444' : '#22c55e') : '#666'
  return { background: bg, color }
}

function getPnlText(cell) {
  if (displayMode.value === 'amount')
    return (cell.pnl >= 0 ? '+' : '') + '¥' + (cell.pnl / 1000).toFixed(1) + 'k'
  return (cell.pnlPct >= 0 ? '+' : '') + cell.pnlPct.toFixed(2) + '%'
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
        const r = await axios.get(`/api/stocks/history/${code}`, { params: { days: 730 } })
        const bars = r.data?.bars || []
        histResults[code] = {}
        for (const b of bars) histResults[code][b.date] = b
      } catch { histResults[code] = {} }
    }))
    histMap.value = histResults

    // step 4: 构建曲线
    curveData.value = buildCurveData(tradeList.value, histResults)

    // step 5: 渲染
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

  // 各标的每日持仓
  const holdings = {}   // code -> { quantity, cost }
  const points   = []

  // 遍历从首笔交易到今天的每一天
  const today = new Date().toISOString().slice(0, 10)
  let curDate = new Date(firstDate)
  let prevTotalProfit = 0

  while (curDate.toISOString().slice(0, 10) <= today) {
    const dateStr = curDate.toISOString().slice(0, 10)
    const dayTrades = sorted.filter(t => t.trade_date === dateStr)

    // 更新持仓
    for (const t of dayTrades) {
      if (!holdings[t.code]) holdings[t.code] = { quantity: 0, cost: 0 }
      if (t.trade_type === 'buy') {
        holdings[t.code].cost     += t.price * t.quantity
        holdings[t.code].quantity += t.quantity
      } else {
        const avgCost = holdings[t.code].quantity > 0
          ? holdings[t.code].cost / holdings[t.code].quantity : 0
        holdings[t.code].cost     -= avgCost * Math.min(t.quantity, holdings[t.code].quantity)
        holdings[t.code].quantity -= Math.min(t.quantity, holdings[t.code].quantity)
        if (holdings[t.code].quantity <= 0) delete holdings[t.code]
      }
    }

    // 当日盈亏 = 持仓市值变化
    let dayProfit = 0
    const dayClose = histMap[sorted[0]?.code]?.[dateStr]?.close || 0
    let totalCost = 0, totalVal = 0
    for (const [code, h] of Object.entries(holdings)) {
      totalCost += h.cost
      const close = histMap[code]?.[dateStr]?.close
      if (close && h.quantity > 0) totalVal += close * h.quantity
    }
    const dailyPnl = totalVal - totalCost
    const totalProfit = prevTotalProfit + dailyPnl

    points.push({
      date: dateStr,
      pnl: dailyPnl,
      totalProfit,
      totalCost: totalCost || 0,
      pnlPct: totalCost > 0 ? (dailyPnl / totalCost) * 100 : 0,
    })

    prevTotalProfit = totalProfit
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
  if (curveRef.value) {
    resizeObserver.value = new ResizeObserver(() => curveChart.value?.resize())
    resizeObserver.value.observe(curveRef.value)
  }
})

onUnmounted(() => {
  curveChart.value?.dispose()
  curveChart.value = null
  resizeObserver.value?.disconnect()
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

