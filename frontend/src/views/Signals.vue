<template>
  <div class="signals-page">
    <h2 style="margin: 0 0 20px 0; font-size: 20px; color: #1a1a2e;">📡 信号中心</h2>

    <!-- ─── 我的持仓信号 ─── -->
    <section class="section">
      <div class="section-header">
        <span class="section-icon">🎯</span>
        <span class="section-title">我的持仓信号</span>
        <span class="section-sub">自选基金 ETF 估值 · 个股暂无</span>
        <el-button size="small" style="margin-left: auto;" :loading="valLoading" @click="loadValuation">
          <span style="font-size:13px;">🔄 刷新</span>
        </el-button>
      </div>

      <div v-if="valLoading" class="loading-row">
        <div class="spinner-sm"></div>
        <span>加载持仓信号...</span>
      </div>

      <!-- 无自选 -->
      <div v-else-if="!watchlistSignals.length" class="empty-state">
        <div class="empty-icon">📋</div>
        <div class="empty-title">自选为空</div>
        <div class="empty-sub">去「自选股」添加基金或 ETF 即可看到专属信号</div>
      </div>

      <!-- 有持仓信号 -->
      <div v-else class="watchlist-grid">
        <div
          v-for="s in watchlistSignals"
          :key="s.code"
          class="wl-card"
          :class="['band-' + s.band, s.data_source === 'manual' ? 'is-manual' : '']"
        >
          <!-- 关联指数顶部彩条：仅 ETF/基金显示 -->
          <div v-if="s.type !== 'stock' && s.data_source === 'linked'" class="manual-bar">
            <span class="manual-bar-tag">🔗 关联指数</span>
            <span class="manual-bar-date">{{ s.index_name }} {{ s.index_code }}</span>
            <el-button link size="small" style="margin-left:auto;font-size:11px;padding:0 6px;" @click="openLinkDialog(s)">换指数</el-button>
          </div>
          <!-- 卡片头部 -->
          <div class="wl-top">
            <div class="wl-title">
              <span class="wl-badge-type" :class="'type-' + s.type">{{ typeLabel(s.type) }}</span>
              <span class="wl-name">{{ s.name }}</span>
            </div>
            <span class="wl-badge-band" :class="'badge-' + s.band">{{ s.band_label }}</span>
          </div>

          <!-- 核心信号：ETF/基金显示分位，个股不显示 -->
          <div v-if="s.type !== 'stock'" class="wl-signal">
            <span class="wl-sig-label">历史分位</span>
            <span class="wl-sig-val" :class="pctClass(s.signal)">{{ s.signal_label }}</span>
          </div>

          <!-- 基金净值 / ETF 现价 -->
          <div v-if="s.nav" class="wl-nav">
            <span class="nav-lbl">基金净值</span>
            <span class="nav-val">{{ s.nav }}</span>
            <span class="nav-chg" :class="s.change_pct >= 0 ? 'up' : 'down'">
              {{ s.change_pct >= 0 ? '+' : '' }}{{ s.change_pct }}%
            </span>
          </div>
          <div v-else-if="s.price" class="wl-nav">
            <span class="nav-lbl">{{ s.type === 'etf' ? 'ETF现价' : '现价' }}</span>
            <span class="nav-val">{{ s.price }}</span>
            <span v-if="s.change_pct != null" class="nav-chg" :class="s.change_pct >= 0 ? 'up' : 'down'">
              {{ s.change_pct >= 0 ? '+' : '' }}{{ s.change_pct }}%
            </span>
          </div>

          <!-- PE/PB / 追踪指数 -->
          <div v-if="s.pe" class="wl-pe">
            PE={{ s.pe }}&nbsp;&nbsp;PB={{ s.pb }}
          </div>

          <!-- ETF/基金：关联指数按钮 & 操作建议 -->
          <template v-if="s.type !== 'stock'">
            <div v-if="s.data_source === 'none'" class="wl-fill-cta">
              <el-button type="primary" size="small" @click="openLinkDialog(s)">🔗 关联指数</el-button>
            </div>
            <div v-if="s.data_source === 'linked' && s.signal == null" class="wl-note">
              ⚠️ 关联的指数「{{ s.index_name }}」尚未填分位，请先去「指数估值」页填写
            </div>
            <div v-if="s.data_source === 'linked' && s.signal != null" class="wl-action" :class="'action-' + s.band">{{ s.action }}</div>
            <div v-if="s.data_source === 'linked' && s.signal == null" class="wl-action" style="background:#f5f5f5;color:#999;">{{ s.action }}</div>
          </template>
        </div>
      </div>

    </section>

    <!-- ─── 填分位弹窗（复用：自选 & 宽基指数） ─── -->
    <el-dialog v-model="editDialog.visible" :title="'填10年分位 · ' + editDialog.name" width="480px" :close-on-click-modal="false">
      <div style="font-size:12px;color:#888;margin-bottom:12px;">
        代码：{{ editDialog.code }}　|　类型：{{ typeLabel(editDialog.type) }}
      </div>
      <el-form label-width="90px" size="default">
        <el-form-item v-if="editDialog.type === 'fund'" label="NAV 分位">
          <el-input-number v-model="editDialog.nav_pct" :min="0" :max="100" :step="0.1" :precision="1" controls-position="right" style="width: 180px;" />
          <span style="margin-left:8px;color:#888;font-size:12px;">% (0=最低, 100=最高)</span>
        </el-form-item>
        <template v-else>
          <el-form-item label="PE 分位">
            <el-input-number v-model="editDialog.pe_pct" :min="0" :max="100" :step="0.1" :precision="1" controls-position="right" style="width: 180px;" />
            <span style="margin-left:8px;color:#888;font-size:12px;">% (推荐)</span>
          </el-form-item>
          <el-form-item label="PB 分位">
            <el-input-number v-model="editDialog.pb_pct" :min="0" :max="100" :step="0.1" :precision="1" controls-position="right" style="width: 180px;" />
            <span style="margin-left:8px;color:#888;font-size:12px;">% (备选)</span>
          </el-form-item>
        </template>
        <el-form-item label="备注">
          <el-input v-model="editDialog.note" placeholder="例如：韭圈儿 2025-07-01 / 估值表第 12 行" maxlength="100" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="saveEditDialog">保存</el-button>
      </template>
    </el-dialog>

    <!-- ─── 关联指数弹窗（自选品种用） ─── -->
    <el-dialog v-model="linkDialog.visible" :title="'🔗 关联指数 · ' + linkDialog.name" width="520px" :close-on-click-modal="false">
      <div class="link-tip">
        选择「{{ linkDialog.name }}」追踪的宽基/行业指数，系统将自动读取该指数的10年分位数据作为信号。
      </div>
      <div class="link-list" v-if="availableIndices.length">
        <div
          v-for="idx in availableIndices"
          :key="idx.code"
          class="link-item"
          :class="{ active: linkDialog.currentIndexCode === idx.code }"
          @click="doLink(idx)"
        >
          <div class="link-item-left">
            <span class="link-idx-name">{{ idx.name }}</span>
            <span class="link-idx-code">{{ idx.code }}</span>
            <span v-if="!idx.is_fixed" class="link-custom-tag">自选</span>
          </div>
          <div class="link-item-right">
            <span v-if="idx.has_pct" class="link-pct-ok">✅ 已填 PE={{ idx.pe_pct }}%</span>
            <span v-else class="link-pct-empty">❌ 未填分位</span>
          </div>
        </div>
      </div>
      <div v-else class="loading-row" style="padding: 20px;">
        <div class="spinner-sm"></div> 加载指数列表...
      </div>
      <template #footer>
        <el-button @click="linkDialog.visible = false">取消</el-button>
        <el-button type="danger" plain v-if="linkDialog.currentIndexCode" @click="doUnlink">取消关联</el-button>
      </template>
    </el-dialog>

    <!-- ─── 趋势信号 ─── -->
    <section class="section">
      <div class="section-header">
        <span class="section-icon">📈</span>
        <span class="section-title">趋势信号</span>
        <span class="section-sub">MA20 / MA60 / RSI(14)</span>
        <el-button size="small" style="margin-left: auto;" :loading="trendLoading" @click="loadAllTrends">
          <span style="font-size:13px;">🔄 刷新</span>
        </el-button>
      </div>

      <div v-if="trendLoading" class="loading-row">
        <div class="spinner-sm"></div>
        <span>计算趋势信号中...</span>
      </div>
      <div v-else class="trend-grid">
        <div
          v-for="t in trends"
          :key="t.code"
          class="trend-card"
          :class="'trend-' + t.status"
        >
          <div class="tc-name">{{ t.name }}</div>
          <div class="tc-price">
            <span>{{ fmt(t.price, 2) }}</span>
            <span class="tc-pct" :class="t.pct >= 0 ? 'up' : 'down'">
              {{ t.pct >= 0 ? '+' : '' }}{{ fmt(t.pct, 2) }}%
            </span>
          </div>
          <div class="tc-mas">
            <div class="tc-ma" :class="t.ma20 >= t.ma60 ? 'bullish' : 'bearish'">
              <span class="ma-lbl">MA20</span>
              <span class="ma-val">{{ fmt(t.ma20) }}</span>
            </div>
            <div class="tc-ma" :class="t.ma20 >= t.ma60 ? 'bullish' : 'bearish'">
              <span class="ma-lbl">MA60</span>
              <span class="ma-val">{{ fmt(t.ma60) }}</span>
            </div>
          </div>
          <div class="tc-rsi">
            <span class="ma-lbl">RSI(14)</span>
            <span class="rsi-val" :class="rsiClass(t.rsi)">{{ fmt(t.rsi, 1) }}</span>
          </div>
          <div class="tc-status" :class="'status-' + t.status">{{ trendLabel(t.status) }}</div>
        </div>
      </div>
    </section>

    <div class="last-update">
      最后更新：{{ lastUpdate }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { getAvailableIndices, linkIndex } from '../api/index.js'

// ─── 数据 ───
const watchlistSignals = ref([])
const indexSignals     = ref([])
const valLoading       = ref(false)
const availableIndices = ref([])

// 关联指数弹窗
const linkDialog = ref({
  visible: false,
  id: null, code: '', name: '',
  currentIndexCode: null,
})

const trends           = ref([])
const trendLoading     = ref(false)
const lastUpdate       = ref('')

// ─── 工具 ───
const fmt = (v, d = 2) => v != null ? v.toFixed(d) : '—'

const typeLabel = (t) => ({ fund: '基金', etf: 'ETF', stock: '个股' }[t] ?? t)

const BAND_LABELS = {
  extreme_low: '极度低估', low: '偏低',
  normal: '适中',         high: '偏高',
  extreme_high: '极度高估', unknown: '数据不足',
}

const pctClass = (v) => {
  if (v == null) return 'neutral'
  if (v < 30) return 'low'
  if (v > 70) return 'high'
  return 'mid'
}

const trendLabel = (s) => ({ bullish: '⬆ 强势', neutral: '➡ 中性', bearish: '⬇ 弱势' }[s] ?? s)

function formatUpdated(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  const now = new Date()
  const diffDays = Math.floor((now - d) / 86400000)
  if (diffDays === 0) return '今日'
  if (diffDays === 1) return '昨日'
  if (diffDays < 30) return `${diffDays}天前`
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

async function clearManual(s) {
  // 关联指数模式下不清理分位，由 doUnlink 取消关联即可
}

// ─── 关联指数 ───
async function loadAvailableIndices() {
  try {
    const { data } = await getAvailableIndices()
    availableIndices.value = data
  } catch { availableIndices.value = [] }
}

async function openLinkDialog(s) {
  linkDialog.value = {
    visible: true,
    id: s.id, code: s.code, name: s.name,
    currentIndexCode: s.index_code || null,
  }
  if (!availableIndices.value.length) await loadAvailableIndices()
}

async function doLink(idx) {
  try {
    await linkIndex(linkDialog.value.id, idx.code)
    ElMessage.success(`已关联「${idx.name}」`)
    linkDialog.value.visible = false
    loadValuation()
  } catch (e) {
    ElMessage.error('关联失败：' + (e.message || e))
  }
}

async function doUnlink() {
  if (!confirm(`取消「${linkDialog.value.name}」的指数关联？`)) return
  try {
    await linkIndex(linkDialog.value.id, null)
    ElMessage.success('已取消关联')
    linkDialog.value.visible = false
    loadValuation()
  } catch { ElMessage.error('操作失败') }
}

// ─── 填分位对话框（仅宽基指数用） ───
const editDialog = ref({
  visible: false,
  code: '', name: '', type: 'stock',
  pe_pct: null, pb_pct: null, note: '',
})

function openEditDialog(s) {
  editDialog.value = {
    visible: true,
    code: s.code,
    name: s.name,
    type: 'stock',
    pe_pct: s.pe_pct ?? null,
    pb_pct: s.pb_pct ?? null,
    note: s.note || '',
  }
}

async function saveEditDialog() {
  const d = editDialog.value
  const payload = {}
  if (d.pe_pct != null) payload.pe_pct = d.pe_pct
  if (d.pb_pct != null) payload.pb_pct = d.pb_pct
  if (d.note) payload.note = d.note
  try {
    await axios.put(`/api/valuation/holding-percentile/${d.code}`, payload)
    ElMessage.success('已保存')
    editDialog.value.visible = false
    loadValuation()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.message || e))
  }
}

const rsiClass = (rsi) => {
  if (rsi == null) return ''
  if (rsi >= 70) return 'overbought'
  if (rsi <= 30) return 'oversold'
  return ''
}

// ─── 加载 ───
async function loadValuation() {
  valLoading.value = true
  try {
    const { data } = await axios.get('/api/valuation/watchlist/signals')
    watchlistSignals.value = data.watchlist_signals || []
    indexSignals.value     = data.index_signals     || []
  } catch (e) {
    console.error('持仓信号加载失败', e)
  } finally {
    valLoading.value = false
  }
}

// ─── 趋势计算 ───
const TREND_INDICES = [
  { code: 'sh',    name: '上证指数',  secid: 'sh000001' },
  { code: 'hs300', name: '沪深300',  secid: 'sh000300' },
  { code: 'cy',    name: '创业板指',  secid: 'sz399006' },
  { code: 'sz',    name: '深证成指',  secid: 'sz399001' },
  { code: 'kc50',  name: '科创50',   secid: 'sh000688' },
]

function calcMA(closes, days) {
  return closes.map((_, i) => {
    if (i < days - 1) return null
    return closes.slice(i - days + 1, i + 1).reduce((a, b) => a + b, 0) / days
  })
}

function calcRSI(closes, period = 14) {
  if (closes.length < period + 1) return closes.map(() => null)
  const gains = [], losses = []
  for (let i = 1; i < closes.length; i++) {
    const diff = closes[i] - closes[i - 1]
    gains.push(Math.max(0, diff))
    losses.push(Math.max(0, -diff))
  }
  const rsi = []
  let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period
  let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period
  for (let i = 0; i < period; i++) rsi.push(null)
  for (let i = period; i < closes.length; i++) {
    if (i > period) {
      avgGain = (avgGain * (period - 1) + gains[i - 1]) / period
      avgLoss = (avgLoss * (period - 1) + losses[i - 1]) / period
    }
    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss
    rsi.push(100 - 100 / (1 + rs))
  }
  return rsi
}

async function loadAllTrends() {
  trendLoading.value = true
  trends.value = []
  try {
    const results = await Promise.all(
      TREND_INDICES.map(async (idx) => {
        try {
          const { data } = await axios.get(`/api/market/index-history/${idx.code}?days=90`)
          const bars = data.bars || []
          if (!bars.length) return null
          const closes = bars.map(b => b.close)
          const ma20 = calcMA(closes, 20)
          const ma60 = calcMA(closes, 60)
          const rsi  = calcRSI(closes, 14)
          const lastClose = closes[closes.length - 1]
          const prevClose = closes[closes.length - 2] || lastClose
          const pct = (lastClose - prevClose) / prevClose * 100
          let status = 'neutral'
          if (ma20[ma20.length - 1] && ma60[ma60.length - 1]) {
            if (ma20[ma20.length - 1] > ma60[ma60.length - 1] && rsi[rsi.length - 1] < 70)
              status = 'bullish'
            else if (ma20[ma20.length - 1] < ma60[ma60.length - 1] || rsi[rsi.length - 1] > 80)
              status = 'bearish'
          }
          return {
            name: idx.name, code: idx.code,
            price: lastClose, pct,
            ma20: ma20[ma20.length - 1],
            ma60: ma60[ma60.length - 1],
            rsi:  rsi[rsi.length - 1],
            status,
          }
        } catch { return null }
      })
    )
    trends.value = results.filter(Boolean)
  } finally {
    trendLoading.value = false
    lastUpdate.value = new Date().toLocaleString('zh-CN')
  }
}

onMounted(() => {
  loadValuation()
  loadAllTrends()
})
</script>

<style scoped>
.signals-page { max-width: 1100px; }

.section {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  border: 1px solid #eee;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}
.section-icon { font-size: 18px; }
.section-title { font-size: 16px; font-weight: 600; color: #1a1a2e; }
.section-sub   { font-size: 12px; color: #aaa; margin-left: 4px; }

.loading-row {
  display: flex; align-items: center; gap: 8px;
  color: #999; font-size: 13px; padding: 20px 0;
}
.spinner-sm {
  width: 18px; height: 18px;
  border: 2px solid #e8e8ee; border-top-color: #4a6cf7;
  border-radius: 50%; animation: spin .8s linear infinite;
  display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── 空状态 ── */
.empty-state {
  text-align: center; padding: 32px 0; color: #bbb;
}
.empty-icon { font-size: 36px; margin-bottom: 8px; }
.empty-title { font-size: 15px; font-weight: 500; color: #888; margin-bottom: 4px; }
.empty-sub   { font-size: 12px; }

/* ── 持仓卡片 ── */
.watchlist-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.wl-card {
  border-radius: 10px;
  padding: 14px 16px;
  border: 1.5px solid transparent;
  transition: box-shadow .15s, transform .15s;
}
/* 手动数据卡片加左侧色条 + 阴影 */
.wl-card.is-manual {
  box-shadow: inset 4px 0 0 0 #1976d2, 0 2px 8px rgba(25,118,210,0.10);
  border-color: #90caf9;
}
.manual-bar {
  display: flex; align-items: center; gap: 6px;
  background: linear-gradient(90deg, #e3f2fd 0%, #f5fbff 100%);
  color: #1565c0;
  font-size: 12px; font-weight: 600;
  padding: 6px 10px;
  margin: -14px -16px 10px -16px;
  border-radius: 10px 10px 0 0;
  border-bottom: 1px solid #bbdefb;
}
.manual-bar-tag { letter-spacing: 0.3px; }
.manual-bar-date { font-weight: 400; color: #1976d2; }
.wl-card:hover { transform: translateY(-2px); box-shadow: 0 4px 14px rgba(0,0,0,.08); }
.band-extreme_low  { border-color: #bbdefb; background: #fafcff; }
.band-low          { border-color: #c8e6c9; background: #fafffe; }
.band-normal       { border-color: #fff9c4; background: #fffefa; }
.band-high         { border-color: #ffe0b2; background: #fffbf5; }
.band-extreme_high { border-color: #fce4ec; background: #fff8fb; }
.band-unknown      { border-color: #eee;    background: #fafafa; }

.wl-top {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px; gap: 6px;
}
.wl-title { display: flex; align-items: center; gap: 6px; flex: 1; min-width: 0; }
.wl-badge-type {
  font-size: 10px; font-weight: 600; padding: 1px 5px;
  border-radius: 4px; flex-shrink: 0;
}
.type-fund  { background: #e8f5e9; color: #2e7d32; }
.type-etf   { background: #e3f2fd; color: #1565c0; }
.type-stock { background: #f5f5f5; color: #888; }

.wl-name { font-size: 13px; font-weight: 600; color: #1a1a2e; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.wl-badge-band {
  font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 20px; flex-shrink: 0;
}
.badge-extreme_low  { background: #e3f2fd; color: #1565c0; }
.badge-low          { background: #e8f5e9; color: #2e7d32; }
.badge-normal       { background: #fff8e1; color: #f57f17; }
.badge-high         { background: #fff3e0; color: #e65100; }
.badge-extreme_high { background: #fce4ec; color: #c62828; }
.badge-unknown      { background: #f5f5f5; color: #9e9e9e; }

.wl-signal {
  display: flex; align-items: baseline; gap: 8px; margin-bottom: 6px;
}
.wl-sig-label { font-size: 11px; color: #aaa; }
.wl-sig-val { font-size: 18px; font-weight: 700; }
.wl-sig-val.low    { color: #1565c0; }
.wl-sig-val.mid    { color: #f57f17; }
.wl-sig-val.high   { color: #c62828; }
.wl-sig-val.neutral { color: #bbb; }

.wl-nav {
  display: flex; align-items: baseline; gap: 8px;
  font-size: 12px; color: #888; margin-bottom: 4px;
}
.nav-lbl { color: #bbb; font-size: 11px; }
.nav-val { font-weight: 600; color: #555; }
.nav-chg { font-weight: 600; }
.nav-chg.up   { color: #ef232a; }
.nav-chg.down { color: #14b143; }

.wl-pe { font-size: 11px; color: #bbb; margin-bottom: 4px; }
.wl-note { font-size: 11px; color: #bbb; margin-bottom: 4px; }

.wl-fill-cta {
  margin-top: 8px;
  text-align: center;
}

.ref-chip.clickable { cursor: pointer; }
.ref-chip.clickable:hover { opacity: 0.85; box-shadow: 0 2px 8px rgba(0,0,0,.12); }

.wl-action {
  font-size: 12px; font-weight: 600; padding: 4px 10px;
  border-radius: 6px; text-align: center; margin-top: 6px;
}
.action-extreme_low  { background: #e3f2fd; color: #1565c0; }
.action-low          { background: #e8f5e9; color: #2e7d32; }
.action-normal       { background: #fff8e1; color: #f57f17; }
.action-high         { background: #fff3e0; color: #e65100; }
.action-extreme_high { background: #fce4ec; color: #c62828; }
.action-unknown      { background: #f5f5f5; color: #9e9e9e; }

/* ── 指数参考 ── */
.index-ref {
  border-top: 1px solid #f0f0f0;
  padding-top: 14px;
}
.ref-title { font-size: 12px; color: #bbb; margin-bottom: 10px; }
.ref-scroll { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px; }
.ref-scroll::-webkit-scrollbar { height: 3px; }
.ref-scroll::-webkit-scrollbar-thumb { background: #ddd; border-radius: 2px; }

.ref-chip {
  display: flex; align-items: center; gap: 6px;
  padding: 5px 10px; border-radius: 20px;
  border: 1px solid transparent; flex-shrink: 0;
  font-size: 12px;
}
.ref-chip.band-extreme_low  { background: #e3f2fd; border-color: #bbdefb; }
.ref-chip.band-low          { background: #e8f5e9; border-color: #c8e6c9; }
.ref-chip.band-normal       { background: #fff8e1; border-color: #fff9c4; }
.ref-chip.band-high         { background: #fff3e0; border-color: #ffe0b2; }
.ref-chip.band-extreme_high { background: #fce4ec; border-color: #fce4ec; }
.ref-chip.band-unknown      { background: #f5f5f5; border-color: #eee; }

.ref-name { color: #555; font-weight: 500; }
.ref-pct  { font-weight: 700; }
.ref-pct.low    { color: #1565c0; }
.ref-pct.mid    { color: #f57f17; }
.ref-pct.high   { color: #c62828; }
.ref-pct.neutral { color: #bbb; }

.ref-band { font-size: 11px; color: #999; }

/* ── 趋势卡片 ── */
.trend-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }

.trend-card {
  border-radius: 10px; padding: 14px 16px;
  border: 1.5px solid transparent;
  transition: box-shadow .15s, transform .15s;
}
.trend-card:hover { transform: translateY(-2px); box-shadow: 0 4px 14px rgba(0,0,0,.08); }
.trend-bullish { border-color: #c8e6c9; background: #fafffe; }
.trend-neutral { border-color: #e0e0e0; background: #fafafa; }
.trend-bearish { border-color: #ffcdd2; background: #fff8f8; }

.tc-name { font-size: 14px; font-weight: 600; color: #1a1a2e; margin-bottom: 6px; }
.tc-price { display: flex; align-items: baseline; gap: 6px; font-size: 12px; color: #888; margin-bottom: 10px; }
.tc-pct { font-weight: 600; }
.tc-pct.up   { color: #ef232a; }
.tc-pct.down { color: #14b143; }

.tc-mas { display: flex; gap: 16px; margin-bottom: 8px; }
.tc-ma { display: flex; align-items: baseline; gap: 4px; }
.ma-lbl { font-size: 11px; color: #999; }
.ma-val { font-size: 13px; font-weight: 600; }
.bullish .ma-val { color: #2e7d32; }
.bearish .ma-val { color: #c62828; }

.tc-rsi { display: flex; align-items: baseline; gap: 6px; margin-bottom: 10px; }
.rsi-val { font-size: 15px; font-weight: 700; color: #555; }
.rsi-val.overbought { color: #c62828; }
.rsi-val.oversold   { color: #1565c0; }

.tc-status {
  font-size: 13px; font-weight: 600; padding: 4px 10px;
  border-radius: 6px; text-align: center;
}
.status-bullish { background: #e8f5e9; color: #2e7d32; }
.status-neutral { background: #f5f5f5; color: #666; }
.status-bearish { background: #fce4ec; color: #c62828; }

.last-update { font-size: 12px; color: #ccc; text-align: right; margin-top: 4px; }

/* 手动数据标识 */
.wl-manual-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #1565c0;
  background: #e3f2fd;
  border-radius: 4px;
  padding: 3px 8px;
  margin-top: 4px;
}
.wl-manual-tag.muted { color: #999; background: #f5f5f5; }
.manual-dot {
  display: inline-block;
  font-size: 9px;
  font-weight: 700;
  font-family: monospace;
  color: #1565c0;
  background: #bbdefb;
  border-radius: 3px;
  padding: 0 3px;
  line-height: 14px;
}
.manual-dot.muted { color: #999; background: #e0e0e0; }
.manual-date { color: #888; margin-left: 2px; }

/* ── 关联指数弹窗 ── */
.link-tip {
  font-size: 13px;
  color: #555;
  background: #f0f7ff;
  border: 1px solid #bbdefb;
  border-radius: 6px;
  padding: 10px 14px;
  margin-bottom: 16px;
  line-height: 1.6;
}
.link-list {
  max-height: 400px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.link-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border: 1.5px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
}
.link-item:hover { border-color: #1976d2; background: #f5f9ff; }
.link-item.active { border-color: #1976d2; background: #e3f2fd; }
.link-item-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.link-idx-name { font-size: 14px; font-weight: 600; color: #1a1a2e; }
.link-idx-code { font-size: 11px; color: #999; font-family: monospace; }
.link-custom-tag {
  font-size: 10px;
  background: #fff3e0;
  color: #e65100;
  border-radius: 3px;
  padding: 0 5px;
}
.link-item-right { font-size: 12px; }
.link-pct-ok    { color: #2e7d32; }
.link-pct-empty { color: #999; }
</style>
