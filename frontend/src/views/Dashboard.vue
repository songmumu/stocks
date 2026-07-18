<template>
  <div>
    <h2 style="margin: 0 0 16px 0; font-size: 20px; color: #1a1a2e;">📈 大盘行情</h2>

    <!-- 指数概览卡片（价格+涨跌）-->
    <el-row :gutter="14" style="margin-bottom: 20px;">
      <el-col v-for="idx in indices" :key="idx.code" :span="6">
        <el-card shadow="hover" :body-style="{ padding: '14px 16px' }" class="index-card">
          <div class="index-name">{{ idx.name }}</div>
          <div class="index-price">{{ formatPrice(idx.price) }}</div>
          <div class="index-change" :class="idx.change_pct >= 0 ? 'up' : 'down'">
            <span class="arrow">{{ idx.change_pct >= 0 ? '▲' : '▼' }}</span>
            <span>{{ Math.abs(idx.change_pct).toFixed(2) }}%</span>
            <span class="amount">{{ formatChange(idx.change_amount) }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- K 线图 -->
    <el-card shadow="never">
      <div class="k-header">
        <div class="k-tabs">
          <div
            v-for="tab in indexTabs"
            :key="tab.value"
            :class="['k-tab-wrapper', { active: selectedIndex === tab.value }]"
          >
            <button
              :class="['k-tab', { active: selectedIndex === tab.value }]"
              @click="onTabChange(tab.value)"
            >
              {{ tab.label }}
            </button>
            <el-button
              v-if="!tab.isDefault"
              link
              size="small"
              type="danger"
              class="tab-delete"
              @click.stop="removeIndexTab(tab.value)"
              title="删除"
            >
              ×
            </el-button>
          </div>
          <el-button link size="small" type="primary" @click="showAddIndexDialog" class="add-tab-btn">
            + 添加
          </el-button>
        </div>
        <el-select v-model="kDays" size="small" style="width: 110px;" @change="loadIndexHistory">
          <el-option label="30日" :value="30" />
          <el-option label="60日" :value="60" />
          <el-option label="120日" :value="120" />
          <el-option label="250日" :value="250" />
        </el-select>
      </div>

      <div class="k-body">
        <div v-if="loading" class="k-state">
          <div class="spinner"></div>
          <div>加载行情数据中...</div>
        </div>
        <div v-else-if="!hasData" class="k-state">
          <div class="empty-icon">📊</div>
          <div class="empty-title">暂无 K 线数据</div>
          <div class="empty-desc">
            当前后端未返回数据。可能原因：<br>
            ① 系统时间在非交易时段范围<br>
            ② 数据源接口暂时不可用<br>
            ③ 该指数代码不存在
          </div>
          <el-button size="small" @click="loadIndexHistory" type="primary" plain>重新加载</el-button>
        </div>
        <div v-show="!loading && hasData" ref="klineRef" class="k-chart"></div>
      </div>
    </el-card>

    <div v-if="lastUpdate" class="update-time">
      最后更新：{{ lastUpdate }}
    </div>

    <!-- 添加指数弹窗 -->
    <el-dialog v-model="addIndexDialog.visible" title="添加指数" width="400px">
      <el-form label-width="80px">
        <el-form-item label="选择指数">
          <el-select v-model="selectedIndexToAdd" placeholder="请选择要添加的指数" style="width: 100%;">
            <el-option
              v-for="idx in AVAILABLE_INDICES.filter(i => !indexTabs.some(t => t.value === i.value))"
              :key="idx.value"
              :label="idx.label"
              :value="idx.value"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addIndexDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="confirmAddIndex">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { getCurrentIndices, getIndexHistory } from '../api/index.js'
import { ElMessage, ElMessageBox } from 'element-plus'

// 默认指数（不可删除）
const DEFAULT_INDEX_TABS = [
  { label: '上证指数', value: 'sh', isDefault: true },
  { label: '深证成指', value: 'sz', isDefault: true },
  { label: '创业板指', value: 'cy', isDefault: true },
  { label: '沪深300', value: 'hs300', isDefault: true },
]

// 可用指数列表（用于添加）
const AVAILABLE_INDICES = [
  { label: '上证指数', value: 'sh' },
  { label: '深证成指', value: 'sz' },
  { label: '创业板指', value: 'cy' },
  { label: '沪深300', value: 'hs300' },
  { label: '中证500', value: 'zz500' },
  { label: '科创50', value: 'kc50' },
  { label: '恒生指数', value: 'hsi' },
  { label: '恒生科技', value: 'hstech' },
  { label: '纳斯达克', value: 'nasdaq' },
  { label: '标普500', value: 'sp500' },
  { label: '道琼斯', value: 'dow' },
]

// 从 localStorage 加载自定义指数
function loadCustomIndices() {
  try {
    const saved = localStorage.getItem('dashboard_custom_indices')
    if (saved) {
      return JSON.parse(saved)
    }
  } catch (e) {
    console.error('加载自定义指数失败', e)
  }
  return []
}

// 保存自定义指数到 localStorage
function saveCustomIndices(customTabs) {
  try {
    localStorage.setItem('dashboard_custom_indices', JSON.stringify(customTabs))
  } catch (e) {
    console.error('保存自定义指数失败', e)
  }
}

const customIndices = ref(loadCustomIndices())
const addIndexDialog = ref({ visible: false })
const selectedIndexToAdd = ref('')

const indexTabs = computed(() => {
  const customs = customIndices.value.map(c => ({ ...c, isDefault: false }))
  return [...DEFAULT_INDEX_TABS, ...customs]
})

const indices = ref([])
const selectedIndex = ref('sh')
const kDays = ref(120)
const loading = ref(false)
const hasData = ref(false)
const lastUpdate = ref('')
const klineRef = ref(null)
let chartInstance = null

function formatPrice(p) {
  if (p === null || p === undefined) return '—'
  return Number(p).toFixed(2)
}

function formatChange(c) {
  if (c === null || c === undefined) return ''
  return (c >= 0 ? '+' : '') + Number(c).toFixed(2)
}

async function loadIndices() {
  try {
    const { data } = await getCurrentIndices()
    indices.value = data.items || []
  } catch (e) {
    console.error('加载指数失败', e)
    indices.value = []
  }
}

function calcMA(bars, days) {
  const result = []
  for (let i = 0; i < bars.length; i++) {
    if (i < days - 1) { result.push(null); continue }
    let sum = 0
    for (let j = i - days + 1; j <= i; j++) sum += bars[j].close
    result.push(+(sum / days).toFixed(2))
  }
  return result
}

async function loadIndexHistory() {
  loading.value = true
  hasData.value = false
  try {
    const { data } = await getIndexHistory(selectedIndex.value, kDays.value)
    const bars = data.bars || []
    console.log(`[Dashboard] ${selectedIndex.value} got ${bars.length} bars, first: ${bars[0]?.date}, last: ${bars[bars.length - 1]?.date}`)

    if (bars.length === 0) {
      hasData.value = false
      loading.value = false
      return
    }

    // 关键修复：先把 loading 置 false，让图表容器从 display:none 变为可见，
    // 否则 echarts.init 时容器是 0x0，K 线会被挤压到角落
    hasData.value = true
    loading.value = false
    await nextTick()

    if (!klineRef.value) {
      console.error('[Dashboard] klineRef is null, skip render')
      return
    }

    if (!chartInstance) {
      chartInstance = echarts.init(klineRef.value, null, { width: 'auto', height: 460 })
      window.addEventListener('resize', () => chartInstance?.resize())
    } else {
      chartInstance.resize()
    }

    const dates = bars.map(b => b.date)
    const vols = bars.map(b => +(b.volume / 1e8).toFixed(2))
    const ma5 = calcMA(bars, 5)
    const ma20 = calcMA(bars, 20)
    const ma60 = calcMA(bars, 60)
    const candleData = bars.map(b => [b.open, b.close, b.low, b.high])

    console.log('[Dashboard] chart container:', klineRef.value?.offsetWidth, 'x', klineRef.value?.offsetHeight)

    // 用 notMerge:true 完全替换旧配置
    chartInstance.setOption(
      buildChartOption(bars, dates, candleData, vols, ma5, ma20, ma60),
      true
    )
    // 容器刚从 display:none 切回可见，强制 resize 一次确保尺寸正确
    chartInstance.resize()

    lastUpdate.value = new Date().toLocaleString('zh-CN')
  } catch (e) {
    console.error('加载指数K线失败', e)
    hasData.value = false
  } finally {
    loading.value = false
  }
}

function buildChartOption(bars, dates, candleData, vols, ma5, ma20, ma60) {
  const n = dates.length
  // 显式设置 xAxis min/max，保证数据覆盖全区域
  return {
    animation: false,
    // 两个独立 grid：K线主图(上) + 成交量副图(下)
    grid: [
      { left: 58, right: 55, top: 40, bottom: 215 },
      { left: 58, right: 55, top: 290, bottom: 62 },
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        boundaryGap: false,
        min: 0,
        max: n - 1,
        axisLine: { onZero: false, lineStyle: { color: '#ccc' } },
        axisLabel: { show: false },
        splitLine: { show: false },
        gridIndex: 0,
      },
      {
        type: 'category',
        data: dates,
        boundaryGap: false,
        min: 0,
        max: n - 1,
        axisLine: { lineStyle: { color: '#ccc' } },
        axisLabel: {
          fontSize: 11, color: '#999',
          formatter: (v) => String(v).slice(5),
          interval: Math.max(0, Math.floor(n / 8) - 1),
        },
        gridIndex: 1,
      },
    ],
    yAxis: [
      {
        scale: true,
        gridIndex: 0,
        splitLine: { lineStyle: { type: 'dashed', color: '#eee' } },
        axisLabel: {
          color: '#999', fontSize: 11,
          formatter: (v) => v >= 1000 ? (v / 1000).toFixed(1) + 'k' : v.toFixed(0)
        },
        position: 'right',
      },
      {
        scale: true,
        gridIndex: 1,
        splitNumber: 2,
        splitLine: { show: false },
        axisLabel: {
          color: '#999', fontSize: 10,
          formatter: (v) => v >= 1 ? v.toFixed(1) + '亿' : (v * 10000).toFixed(0)
        },
        position: 'right',
      },
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(30,30,40,0.95)',
      borderColor: '#333',
      textStyle: { color: '#fff', fontSize: 12 },
      formatter: function (params) {
        if (!params || !params.length) return ''
        const p = params.find(x => x.seriesName === 'K线') || params[0]
        const idx = p.dataIndex
        const bar = bars[idx]
        if (!bar) return ''
        let html = `<div style="font-weight:600;margin-bottom:6px;">${bar.date}</div>`
        html += `<div>开 ${bar.open.toFixed(2)} 收 ${bar.close.toFixed(2)}</div>`
        html += `<div>高 ${bar.high.toFixed(2)} 低 ${bar.low.toFixed(2)}</div>`
        html += `<div>涨跌 ${bar.change_pct >= 0 ? '+' : ''}${bar.change_pct.toFixed(2)}%</div>`
        html += `<div>成交量 ${(vols[idx] || 0).toFixed(2)} 亿</div>`
        return html
      },
    },
    legend: {
      data: ['MA5', 'MA20', 'MA60'],
      top: 4,
      textStyle: { color: '#666', fontSize: 12 },
      itemGap: 20,
    },
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: candleData,
        itemStyle: {
          color: '#ef232a',
          color0: '#14b143',
          borderColor: '#ef232a',
          borderColor0: '#14b143',
        },
      },
      {
        name: 'MA5', type: 'line', xAxisIndex: 0, yAxisIndex: 0,
        data: ma5, smooth: true, symbol: 'none',
        lineStyle: { width: 1.5, color: '#ffa726' },
        connectNulls: true,
      },
      {
        name: 'MA20', type: 'line', xAxisIndex: 0, yAxisIndex: 0,
        data: ma20, smooth: true, symbol: 'none',
        lineStyle: { width: 1.5, color: '#ab47bc' },
        connectNulls: true,
      },
      {
        name: 'MA60', type: 'line', xAxisIndex: 0, yAxisIndex: 0,
        data: ma60, smooth: true, symbol: 'none',
        lineStyle: { width: 1.5, color: '#42a5f5' },
        connectNulls: true,
      },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: vols.map((v, i) => ({
          value: v,
          itemStyle: {
            color: bars[i].close >= bars[i].open ? 'rgba(239,35,42,.45)' : 'rgba(20,177,67,.45)'
          }
        })),
      },
    ],
    dataZoom: [
      {
        type: 'slider',
        xAxisIndex: [0, 1],
        start: 0,
        end: 100,
        bottom: 8,
        height: 26,
        borderColor: '#eee',
        fillerColor: 'rgba(100,100,200,0.08)',
        handleStyle: { color: '#999' },
        textStyle: { color: '#999', fontSize: 10 },
      },
      {
        type: 'inside',
        xAxisIndex: [0, 1],
        start: 0,
        end: 100,
      },
    ],
  }
}

function onTabChange(val) {
  if (val === selectedIndex.value) return
  selectedIndex.value = val
  loadIndexHistory()
}

function showAddIndexDialog() {
  selectedIndexToAdd.value = ''
  addIndexDialog.value.visible = true
}

function confirmAddIndex() {
  if (!selectedIndexToAdd.value) {
    ElMessage.warning('请选择一个指数')
    return
  }
  const idx = AVAILABLE_INDICES.find(i => i.value === selectedIndexToAdd.value)
  if (!idx) return
  
  // 检查是否已存在
  if (indexTabs.value.some(t => t.value === idx.value)) {
    ElMessage.warning('该指数已存在')
    return
  }
  
  customIndices.value.push({ label: idx.label, value: idx.value })
  saveCustomIndices(customIndices.value)
  addIndexDialog.value.visible = false
  ElMessage.success(`已添加 ${idx.label}`)
  
  // 自动切换到新添加的指数
  selectedIndex.value = idx.value
  loadIndexHistory()
}

async function removeIndexTab(value) {
  const tab = indexTabs.value.find(t => t.value === value)
  if (!tab) return
  
  try {
    await ElMessageBox.confirm(
      `确定删除 "${tab.label}" 吗？`,
      '删除指数',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  
  customIndices.value = customIndices.value.filter(i => i.value !== value)
  saveCustomIndices(customIndices.value)
  ElMessage.success('已删除')
  
  // 如果删除的是当前选中的，切换到第一个默认指数
  if (selectedIndex.value === value) {
    selectedIndex.value = 'sh'
    loadIndexHistory()
  }
}

onMounted(() => {
  loadIndices()
  loadIndexHistory()
})

onBeforeUnmount(() => {
  chartInstance?.dispose()
  chartInstance = null
})
</script>

<style scoped>
.index-card {
  border-radius: 8px;
  transition: transform .15s;
}
.index-card:hover { transform: translateY(-2px); }
.index-name {
  font-size: 13px;
  color: #888;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.index-price {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 4px;
}
.index-change {
  font-size: 13px;
  font-weight: 500;
}
.index-change.up { color: #ef232a; }
.index-change.down { color: #14b143; }
.arrow { margin-right: 2px; }
.amount { color: #888; margin-left: 4px; font-weight: 400; }
.k-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.k-tabs {
  display: flex;
  gap: 4px;
  flex: 1;
}
.k-tab {
  padding: 5px 14px;
  border: 1px solid #e8e8ee;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  color: #666;
  transition: all .15s;
}
.k-tab:hover { border-color: #4a6cf7; color: #4a6cf7; }
.k-tab.active {
  background: #4a6cf7;
  border-color: #4a6cf7;
  color: #fff;
}
.k-body { min-height: 460px; }
.k-chart { width: 100%; height: 460px; }
.k-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 460px;
  color: #999;
  font-size: 14px;
  gap: 12px;
}
.empty-icon { font-size: 42px; }
.empty-title { font-size: 15px; color: #555; font-weight: 500; }
.empty-desc {
  font-size: 12px;
  color: #999;
  text-align: center;
  line-height: 1.8;
  background: #f8f8fc;
  padding: 12px 20px;
  border-radius: 8px;
  max-width: 340px;
}
.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e8e8ee;
  border-top-color: #4a6cf7;
  border-radius: 50%;
  animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.spinner-sm {
  width: 18px;
  height: 18px;
  border: 2px solid #e8e8ee;
  border-top-color: #4a6cf7;
  border-radius: 50%;
  animation: spin .8s linear infinite;
  display: inline-block;
}
.update-time {
  font-size: 12px;
  color: #bbb;
  margin-top: 10px;
  text-align: right;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.k-tab-wrapper {
  display: flex;
  align-items: center;
  gap: 2px;
  position: relative;
}

.k-tab-wrapper .k-tab {
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.k-tab-wrapper .tab-delete {
  padding: 5px 6px;
  height: auto;
  font-size: 14px;
  line-height: 1;
  border: 1px solid #e8e8ee;
  border-left: none;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  background: #fff;
  color: #999;
  opacity: 0;
  transition: all 0.15s;
}

.k-tab-wrapper:hover .tab-delete {
  opacity: 1;
}

.k-tab-wrapper .tab-delete:hover {
  color: #f56c6c;
  background: #fef0f0;
}

.k-tab-wrapper.active .tab-delete {
  border-color: #4a6cf7;
  background: #4a6cf7;
  color: rgba(255,255,255,0.8);
}

.k-tab-wrapper.active .tab-delete:hover {
  color: #fff;
  background: #f56c6c;
}

.add-tab-btn {
  margin-left: 4px;
  padding: 5px 10px;
}
</style>
