<template>
  <div class="stock-detail">
    <!-- 返回按钮 -->
    <div class="back-bar">
      <el-button link @click="$router.back()">
        <span class="back-icon">←</span> 返回自选
      </el-button>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="page-loading">
      <div class="spinner"></div>
      <div>加载中...</div>
    </div>

    <template v-else-if="stock">
      <!-- 头部信息 -->
      <div class="detail-header">
        <div class="header-left">
          <h1 class="stock-title">{{ stock.name }}</h1>
          <div class="stock-subtitle">
            {{ stock.code }}
            <span class="dot">·</span>
            {{ stock.stock_type === 'fund' ? '基金' : '股票' }}
            <span v-if="stock.notes" class="stock-notes">📝 {{ stock.notes }}</span>
          </div>
        </div>
        <div v-if="quote && !quote.no_intraday" class="header-right">
          <div class="big-price" :class="quote.change >= 0 ? 'up' : 'down'">
            {{ fmtPrice(quote.price) }}
          </div>
          <div class="big-change" :class="quote.change >= 0 ? 'up' : 'down'">
            {{ quote.change >= 0 ? '+' : '' }}{{ quote.change_amount?.toFixed(2) }}
            ({{ quote.change >= 0 ? '+' : '' }}{{ quote.change?.toFixed(2) }}%)
          </div>
        </div>
        <div v-else-if="quote && quote.is_nav" class="header-right">
          <div class="big-price" :class="quote.change >= 0 ? 'up' : 'down'">
            {{ fmtPrice(quote.price) }}
          </div>
          <div class="big-change" :class="quote.change >= 0 ? 'up' : 'down'">
            {{ quote.change >= 0 ? '+' : '' }}{{ quote.change_amount?.toFixed(4) }}
            ({{ quote.change >= 0 ? '+' : '' }}{{ quote.change?.toFixed(2) }}%)
          </div>
          <div class="nav-date">净值日期: {{ quote.date }}</div>
        </div>
        <div v-else-if="quote && quote.no_intraday" class="header-right no-intraday">
          <div class="no-intra-badge">⏸️ 场外基金</div>
          <div class="no-intra-hint">暂无净值数据</div>
        </div>
      </div>

      <!-- K线图 -->
      <div class="kline-section">
        <div class="section-header">
          <h3>📈 K线走势</h3>
          <el-radio-group v-model="klineDays" size="small" @change="loadKline">
            <el-radio-button :value="30">30日</el-radio-button>
            <el-radio-button :value="60">60日</el-radio-button>
            <el-radio-button :value="120">120日</el-radio-button>
            <el-radio-button :value="250">250日</el-radio-button>
          </el-radio-group>
        </div>
        <div ref="klineRef" class="kline-chart" v-loading="klineLoading"></div>
      </div>

      <!-- 信息网格 -->
      <div class="info-grid">
        <!-- 实时行情卡片 -->
        <div v-if="quote && !quote.no_intraday" class="info-card">
          <h4>📊 实时行情</h4>
          <div class="info-table">
            <div class="info-row">
              <span class="label">今开</span>
              <span class="value">{{ fmtPrice(quote.open) }}</span>
            </div>
            <div class="info-row">
              <span class="label">最高</span>
              <span class="value up">{{ fmtPrice(quote.high) }}</span>
            </div>
            <div class="info-row">
              <span class="label">最低</span>
              <span class="value down">{{ fmtPrice(quote.low) }}</span>
            </div>
            <div class="info-row">
              <span class="label">昨收</span>
              <span class="value">{{ fmtPrice(quote.pre_close) }}</span>
            </div>
            <div class="info-row">
              <span class="label">成交量</span>
              <span class="value">{{ fmtVolume(quote.volume) }}</span>
            </div>
            <div class="info-row">
              <span class="label">成交额</span>
              <span class="value">{{ fmtAmount(quote.amount) }}</span>
            </div>
            <div class="info-row">
              <span class="label">换手率</span>
              <span class="value">{{ quote.turnover_rate?.toFixed(2) }}%</span>
            </div>
            <div class="info-row">
              <span class="label">市盈率</span>
              <span class="value">{{ quote.pe?.toFixed(2) || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="label">总市值</span>
              <span class="value">{{ fmtMarketCap(quote.market_cap) }}</span>
            </div>
          </div>
        </div>

        <!-- 场外基金信息 -->
        <div v-else-if="quote && quote.no_intraday" class="info-card">
          <h4>📊 基金信息</h4>
          <div class="info-table">
            <div class="info-row">
              <span class="label">基金代码</span>
              <span class="value">{{ stock.code }}</span>
            </div>
            <div class="info-row">
              <span class="label">基金类型</span>
              <span class="value">场外开放式基金</span>
            </div>
            <div v-if="quote.is_nav" class="info-row">
              <span class="label">最新净值</span>
              <span class="value" :class="quote.change >= 0 ? 'up' : 'down'">
                {{ fmtPrice(quote.price) }}
              </span>
            </div>
            <div v-if="quote.is_nav" class="info-row">
              <span class="label">净值日期</span>
              <span class="value">{{ quote.date }}</span>
            </div>
            <div v-if="quote.is_nav" class="info-row">
              <span class="label">日涨跌幅</span>
              <span class="value" :class="quote.change >= 0 ? 'up' : 'down'">
                {{ quote.change >= 0 ? '+' : '' }}{{ quote.change?.toFixed(2) }}%
              </span>
            </div>
            <div class="info-row">
              <span class="label">净值更新</span>
              <span class="value">每日收盘后</span>
            </div>
            <div v-if="stock.notes" class="info-row">
              <span class="label">备注</span>
              <span class="value">{{ stock.notes }}</span>
            </div>
          </div>
        </div>

        <!-- 交易记录 -->
        <div class="info-card trades-card">
          <h4>📝 交易记录</h4>
          <div v-if="trades.length === 0" class="empty-trades">
            暂无交易记录
            <el-button type="primary" link @click="$router.push('/trades')">去添加 →</el-button>
          </div>
          <div v-else class="trade-list">
            <div v-for="trade in trades" :key="trade.id" class="trade-item" :class="trade.side">
              <div class="trade-main">
                <span class="trade-side">{{ trade.side === 'buy' ? '买入' : '卖出' }}</span>
                <span class="trade-date">{{ trade.date }}</span>
              </div>
              <div class="trade-detail">
                {{ trade.volume }}股 × {{ trade.price.toFixed(3) }}
                <span class="trade-amount">= {{ (trade.volume * trade.price).toFixed(2) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 持仓汇总 -->
        <div v-if="position" class="info-card position-card">
          <h4>💼 持仓汇总</h4>
          <div class="position-summary">
            <div class="pos-row">
              <span class="label">持仓数量</span>
              <span class="value">{{ position.total_volume }} 股</span>
            </div>
            <div class="pos-row">
              <span class="label">持仓成本</span>
              <span class="value">{{ position.avg_cost?.toFixed(3) }}</span>
            </div>
            <div class="pos-row">
              <span class="label">当前市值</span>
              <span class="value">{{ fmtAmount(position.market_value) }}</span>
            </div>
            <div class="pos-row">
              <span class="label">浮动盈亏</span>
              <span class="value" :class="position.unrealized_pnl >= 0 ? 'up' : 'down'">
                {{ position.unrealized_pnl >= 0 ? '+' : '' }}{{ position.unrealized_pnl?.toFixed(2) }}
                ({{ position.unrealized_pnl_pct?.toFixed(2) }}%)
              </span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="empty-state">
      <div class="empty-icon">😕</div>
      <div class="empty-title">未找到该自选</div>
      <el-button type="primary" @click="$router.push('/stocks')">返回自选列表</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import echarts from '../utils/echarts'
import { getWatchlist, getRealtimeQuote, getStockHistory, getTrades } from '../api/index.js'

const route = useRoute()
const router = useRouter()
const stockId = computed(() => route.params.id)

const loading = ref(true)
const stock = ref(null)
const quote = ref(null)
const trades = ref([])
const position = ref(null)

const klineRef = ref(null)
const klineChart = ref(null)
const klineDays = ref(60)
const klineLoading = ref(false)

// 加载股票基本信息
async function loadStock() {
  try {
    const res = await getWatchlist()
    const list = res.data || []
    stock.value = list.find(s => String(s.id) === String(stockId.value))
    if (!stock.value) {
      loading.value = false
      return
    }
    // 重要：先关掉 loading，让 v-else-if 详情区域渲染，
    // klineRef 才能绑定到容器，才能让 ECharts init 拿到正确尺寸。
    loading.value = false
    await nextTick()
    await loadQuote()
    await loadKline()
    await loadTrades()
  } catch (e) {
    console.error('loadStock error:', e)
    loading.value = false
  }
}

// 加载实时行情
async function loadQuote() {
  try {
    const res = await getRealtimeQuote(stock.value.code)
    quote.value = res.data
  } catch (e) {
    console.error('loadQuote error:', e)
    quote.value = null
  }
}

// 加载K线
async function loadKline() {
  if (!stock.value) return
  klineLoading.value = true
  try {
    const res = await getStockHistory(stock.value.code, klineDays.value)
    const bars = res.data?.bars || []

    // 场外基金：用K线最后一条的收盘价作为最新净值
    if (stock.value.stock_type === 'fund') {
      if (bars.length >= 1) {
        const latest = bars[bars.length - 1]
        const prev = bars[bars.length - 2]
        quote.value = {
          no_intraday: true,
          is_nav: true,
          price: latest.close,
          pre_close: prev ? prev.close : latest.close,
          date: latest.date,
          open: latest.open,
          high: latest.high,
          low: latest.low,
          change: prev ? ((latest.close - prev.close) / prev.close * 100) : 0,
          change_amount: prev ? (latest.close - prev.close) : 0,
        }
      }
    }

    // 重要：loadKline 可能是首次进入页面调用，此时 v-if=loading/v-else-if=stock 刚切换，
    // klineRef 容器还没有渲染。先等 DOM 更新后再 init ECharts，避免 0×0 初始化。
    await nextTick()
    // 再一次保险：v-loading 蒙层可能影响宽度，等一帧
    requestAnimationFrame(() => renderKline(bars))
  } catch (e) {
    console.error('loadKline error:', e)
  } finally {
    klineLoading.value = false
  }
}

// 加载交易记录
async function loadTrades() {
  try {
    const res = await getTrades()
    const allTrades = res.data || []
    trades.value = allTrades.filter(t => t.code === stock.value.code).slice(0, 10)
    calcPosition()
  } catch (e) {
    console.error('loadTrades error:', e)
  }
}

// 计算持仓
function calcPosition() {
  const buys = trades.value.filter(t => t.side === 'buy')
  const sells = trades.value.filter(t => t.side === 'sell')
  
  const totalBuyVolume = buys.reduce((sum, t) => sum + t.volume, 0)
  const totalSellVolume = sells.reduce((sum, t) => sum + t.volume, 0)
  const totalVolume = totalBuyVolume - totalSellVolume
  
  if (totalVolume <= 0) {
    position.value = null
    return
  }
  
  const totalBuyCost = buys.reduce((sum, t) => sum + t.volume * t.price, 0)
  const totalSellCost = sells.reduce((sum, t) => sum + t.volume * t.price, 0)
  const avgCost = (totalBuyCost - totalSellCost) / totalVolume
  
  const currentPrice = quote.value?.price || avgCost
  const marketValue = totalVolume * currentPrice
  const unrealizedPnl = totalVolume * (currentPrice - avgCost)
  const unrealizedPnlPct = (currentPrice / avgCost - 1) * 100
  
  position.value = {
    total_volume: totalVolume,
    avg_cost: avgCost,
    market_value: marketValue,
    unrealized_pnl: unrealizedPnl,
    unrealized_pnl_pct: unrealizedPnlPct,
  }
}

// 渲染K线图
function renderKline(bars) {
  if (!klineRef.value) return

  // 每次重建实例，避免旧状态干扰
  if (klineChart.value) {
    klineChart.value.dispose()
    klineChart.value = null
  }

  // 设置容器尺寸后再 init
  klineRef.value.style.height = '400px'
  klineRef.value.style.width = '100%'

  const chart = echarts.init(klineRef.value)
  klineChart.value = chart
  window.addEventListener('resize', () => chart.resize())

  if (!bars || bars.length === 0) {
    chart.setOption({
      title: { text: '暂无K线数据', left: 'center', top: 'center', textStyle: { color: '#999', fontSize: 14 } }
    }, true)
    return
  }

  // 整理数据
  const dates = bars.map(b => b.date)
  const ohlcData = bars.map(b => [b.open, b.close, b.low, b.high]) // [开,收,低,高]

  // 计算MA
  const calcMA = (n) => {
    const result = []
    for (let i = 0; i < ohlcData.length; i++) {
      if (i < n - 1) { result.push('-') }
      else {
        let sum = 0
        for (let j = 0; j < n; j++) sum += ohlcData[i - j][1]
        result.push(+(sum / n).toFixed(3))
      }
    }
    return result
  }
  const ma5 = calcMA(5), ma10 = calcMA(10), ma20 = calcMA(20)

  const upColor = '#ef232a', downColor = '#14b143'

  const option = {
    animation: false,
    backgroundColor: '#fff',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params) => {
        const p = params.find(x => x.seriesType === 'candlestick')
        if (!p) return ''
        const v = p.value
        return `${p.axisValue}<br/>开:${v[0]} 收:${v[1]}<br/>低:${v[2]} 高:${v[3]}`
      }
    },
    grid: { left: 50, right: 60, bottom: 60, top: 30 },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#ddd' } },
      axisLabel: { color: '#666', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      position: 'right',
      axisLine: { lineStyle: { color: '#ddd' } },
      axisLabel: { color: '#666', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
      scale: true
    },
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: ohlcData,
        itemStyle: {
          color: upColor,
          color0: downColor,
          borderColor: upColor,
          borderColor0: downColor,
        }
      },
      { name: 'MA5', type: 'line', data: ma5, smooth: true, lineStyle: { width: 1 }, symbol: 'none', color: '#f59e0b' },
      { name: 'MA10', type: 'line', data: ma10, smooth: true, lineStyle: { width: 1 }, symbol: 'none', color: '#3b82f6' },
      { name: 'MA20', type: 'line', data: ma20, smooth: true, lineStyle: { width: 1 }, symbol: 'none', color: '#8b5cf6' },
    ],
    legend: { data: ['MA5', 'MA10', 'MA20'], top: 0, right: 10, textStyle: { fontSize: 11 } },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0, start: 0, end: 100 },
      { type: 'slider', xAxisIndex: 0, start: 0, end: 100, height: 20, bottom: 5 }
    ]
  }

  chart.setOption(option)
  chart.resize()
}

// 格式化函数
function fmtPrice(price) {
  if (price === undefined || price === null) return '-'
  const decimals = stock.value?.stock_type === 'fund' ? 4 : 2
  return price.toFixed(decimals)
}

function fmtVolume(vol) {
  if (!vol) return '-'
  if (vol >= 1e8) return (vol / 1e8).toFixed(2) + '亿'
  if (vol >= 1e4) return (vol / 1e4).toFixed(2) + '万'
  return vol.toString()
}

function fmtAmount(amt) {
  if (!amt) return '-'
  if (amt >= 1e8) return (amt / 1e8).toFixed(2) + '亿'
  if (amt >= 1e4) return (amt / 1e4).toFixed(2) + '万'
  return amt.toFixed(2)
}

function fmtMarketCap(cap) {
  if (!cap) return '-'
  if (cap >= 1e12) return (cap / 1e12).toFixed(2) + '万亿'
  if (cap >= 1e8) return (cap / 1e8).toFixed(2) + '亿'
  return cap.toFixed(2)
}

onMounted(() => {
  loadStock()
})
</script>

<style scoped>
.stock-detail {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px;
}

.back-bar {
  margin-bottom: 16px;
}
.back-icon {
  font-size: 18px;
  margin-right: 4px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  background: #fff;
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.stock-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #1a1a2e;
}

.stock-subtitle {
  color: #666;
  font-size: 14px;
}

.stock-notes {
  margin-left: 12px;
  color: #999;
}

.dot {
  margin: 0 6px;
  color: #ccc;
}

.header-right {
  text-align: right;
}

.big-price {
  font-size: 32px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.big-change {
  font-size: 14px;
  margin-top: 4px;
  font-variant-numeric: tabular-nums;
}

.no-intraday {
  text-align: right;
}

.no-intra-badge {
  font-size: 16px;
  color: #999;
}

.no-intra-hint {
  font-size: 12px;
  color: #bbb;
  margin-top: 4px;
}
.nav-date {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}

.up { color: #ef232a; }
.down { color: #14b143; }

.kline-section {
  background: #fff;
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header h3 {
  margin: 0;
  font-size: 16px;
  color: #1a1a2e;
}

.kline-chart {
  width: 100%;
  height: 400px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}

.info-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.info-card h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.info-table {
  display: grid;
  gap: 10px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}

.info-row .label {
  color: #999;
}

.info-row .value {
  color: #1a1a2e;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.trades-card, .position-card {
  grid-row: span 2;
}

.empty-trades {
  text-align: center;
  padding: 40px 0;
  color: #999;
}

.trade-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.trade-item {
  padding: 12px;
  border-radius: 8px;
  background: #f8f9fa;
  font-size: 13px;
}

.trade-item.buy {
  border-left: 3px solid #ef232a;
}

.trade-item.sell {
  border-left: 3px solid #14b143;
}

.trade-main {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.trade-side {
  font-weight: 600;
}

.trade-item.buy .trade-side { color: #ef232a; }
.trade-item.sell .trade-side { color: #14b143; }

.trade-date {
  color: #999;
  font-size: 12px;
}

.trade-detail {
  color: #666;
}

.trade-amount {
  color: #1a1a2e;
  font-weight: 500;
}

.position-summary {
  display: grid;
  gap: 14px;
}

.pos-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}

.pos-row .label {
  color: #999;
}

.pos-row .value {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.page-loading {
  text-align: center;
  padding: 80px 0;
  color: #999;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f0f0f0;
  border-top-color: #409eff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: 80px 0;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 16px;
  color: #666;
  margin-bottom: 20px;
}
</style>
