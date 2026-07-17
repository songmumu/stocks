<template>
  <div class="page">
    <!-- 页面头部 -->
    <div class="page-head">
      <div class="head-left">
        <h2>📊 指数估值</h2>
        <span class="head-sub">宽基/行业指数 · 10年分位 · PE / PB</span>
      </div>
      <div class="head-right">
        <span class="last-sync">
          <span class="sync-dot"></span>
          实时数据
        </span>
        <el-button type="primary" size="small" @click="addDialog.visible = true">
          ➕ 添加指数
        </el-button>
        <el-button size="small" @click="loadData" :loading="loading">
          🔄 刷新
        </el-button>
      </div>
    </div>

    <!-- 说明条 -->
    <div class="info-bar">
      <span>💡 宽基指数由腾讯提供实时 PE/PB，<b style="color:#6a1b9a;">紫色 M=C</b> 表示中证指数 10 年历史分位，<b style="color:#1976d2;">蓝色 M=M</b> 表示手动填入，<b style="color:#2e7d32;">绿色 M=S</b> 表示本地快照。</span>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <span>加载指数数据中...</span>
    </div>

    <!-- 指数卡片网格 -->
    <div v-else class="index-grid">
      <div
        v-for="idx in indices"
        :key="idx.code"
        class="idx-card"
        :class="['band-' + idx.band, { 'is-custom': idx.is_custom }]"
      >
        <!-- 卡片顶部：名称 + 代码 + 删除（自定义） -->
        <div class="idx-top">
          <div class="idx-name">{{ idx.name }}</div>
          <div class="idx-top-right">
            <span v-if="idx.is_custom" class="idx-custom-tag">自选</span>
            <span class="idx-code">{{ idx.code }}</span>
          </div>
        </div>

        <!-- 点位 & 涨跌幅 -->
        <div class="idx-price-row">
          <span class="idx-price">{{ fmt(idx.price, 1) }}</span>
          <span class="idx-pct" :class="idx.pct >= 0 ? 'up' : 'down'">
            {{ idx.pct >= 0 ? '+' : '' }}{{ fmt(idx.pct, 2) }}%
          </span>
        </div>

        <!-- PE / PB -->
        <div class="idx-pepb">
          <div class="pepb-item">
            <span class="pepb-lbl">PE</span>
            <span class="pepb-val">{{ idx.pe ? fmt(idx.pe, 2) : '—' }}</span>
          </div>
          <div class="pepb-divider"></div>
          <div class="pepb-item">
            <span class="pepb-lbl">PB</span>
            <span class="pepb-val">{{ idx.pb ? fmt(idx.pb, 2) : '—' }}</span>
          </div>
        </div>

        <!-- 分位 & 档位 -->
        <div class="idx-signal">
          <!-- 已有分位：手动、CSI、0本地快照 都显示 -->
          <div v-if="hasPct(idx)" class="sig-block filled">
            <div class="sig-pct-row">
              <span class="sig-pct-label">{{ historyLabel(idx) }}</span>
              <span class="sig-pct-val" :class="pctClass(idx.pe_pct ?? idx.pb_pct)">
                {{ idx.pe_pct != null ? idx.pe_pct + '%' : (idx.pb_pct != null ? idx.pb_pct + '%' : '—') }}
              </span>
              <span class="sig-dot" :class="'dot-' + idx.data_source">{{ sourceTag(idx) }}</span>
            </div>
            <div class="sig-band-row">
              <span class="band-badge" :class="'badge-' + idx.band">{{ idx.band_label }}</span>
              <span class="sig-action" :class="'action-' + idx.band">{{ actionLabel(idx.band) }}</span>
            </div>
            <div class="sig-date">
              {{ idx.data_source === 'manual' ? '更新于 ' + formatUpdated(idx.updated_at) : sourceLabel(idx) }}
            </div>
          </div>
          <div v-else class="sig-block empty">
            <div class="sig-unknown">
              <span class="sig-q">?</span>
              <span class="sig-q-lbl">暂无分位数据</span>
            </div>
          </div>
        </div>

        <!-- 卡片底部：操作行 -->
        <div class="idx-footer">
          <el-button
            type="danger" plain size="small"
            @click="doDelete(idx)"
            :loading="deleting === idx.code"
          >
            🗑 删除
          </el-button>
          <el-button
            v-if="hasPct(idx) && idx.data_source === 'manual'"
            type="primary" plain size="small"
            @click="openEdit(idx)"
          >
            📝 修改分位
          </el-button>
          <el-button
            v-else-if="hasPct(idx) && (idx.data_source === 'csi_10y' || idx.data_source === 'local_snapshot')"
            type="primary" plain size="small"
            @click="openEdit(idx)"
          >
            ✏️ 覆盖为手动
          </el-button>
          <el-button
            v-else
            type="primary" size="small"
            @click="openEdit(idx)"
          >
            📊 填分位
          </el-button>
        </div>
      </div>
    </div>

    <!-- 添加指数弹窗 -->
    <el-dialog
      v-model="addDialog.visible"
      title="添加指数"
      width="440px"
      :close-on-click-modal="false"
    >
      <el-form label-width="80px" size="default">
        <el-form-item label="指数代码">
          <el-input
            v-model="addDialog.code"
            placeholder="例如：399006（创业板指）/ 000922（中证红利）"
            @keyup.enter="verifyName"
            maxlength="10"
            style="width: 100%;"
          />
        </el-form-item>
        <el-form-item label="指数名称">
          <el-input
            v-model="addDialog.name"
            placeholder="输入名称，验证代码后可自动填入"
            maxlength="32"
            style="width: 100%;"
          />
        </el-form-item>
        <div v-if="addDialog.hint" class="add-hint" :class="addDialog.hintType">
          {{ addDialog.hint }}
        </div>
      </el-form>
      <template #footer>
        <el-button @click="addDialog.visible = false">取消</el-button>
        <el-button @click="verifyName" :loading="addDialog.verifying">🔍 验证代码</el-button>
        <el-button type="primary" @click="doAdd" :loading="addDialog.saving" :disabled="!addDialog.code || !addDialog.name">
          确认添加
        </el-button>
      </template>
    </el-dialog>

    <!-- 编辑弹窗 -->
    <el-dialog
      v-model="editDialog.visible"
      :title="'填10年分位 · ' + editDialog.name"
      width="500px"
      :close-on-click-modal="false"
    >
      <div class="edit-tip">
        <span class="tip-code">{{ editDialog.code }}</span>
        <span class="tip-pepb">
          当前 PE={{ editDialog.pe }}&nbsp;&nbsp;PB={{ editDialog.pb }}
        </span>
      </div>

      <el-form label-width="90px" size="default" style="margin-top:12px;">
        <el-form-item label="PE 分位">
          <el-input-number
            v-model="editDialog.pe_pct"
            :min="0" :max="100" :step="0.1" :precision="1"
            controls-position="right"
            style="width: 180px;"
          />
          <span class="form-hint">% (推荐填此项)</span>
        </el-form-item>
        <el-form-item label="PB 分位">
          <el-input-number
            v-model="editDialog.pb_pct"
            :min="0" :max="100" :step="0.1" :precision="1"
            controls-position="right"
            style="width: 180px;"
          />
          <span class="form-hint">% (PE 无效时填此项)</span>
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="editDialog.note"
            placeholder="例如：韭圈儿 2025-07-01 / 乌龟量化第 8 页"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>
      </el-form>

      <!-- 档位预览 -->
      <div class="band-preview" v-if="previewBand">
        <span class="preview-label">预计档位：</span>
        <span class="band-badge" :class="'badge-' + previewBand">{{ BAND_LABELS[previewBand] }}</span>
        <span class="preview-action" :class="'action-' + previewBand">{{ actionLabel(previewBand) }}</span>
      </div>

      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button type="danger" plain @click="doClear" v-if="editDialog.data_source === 'manual'">
          清除分位
        </el-button>
        <el-button type="primary" @click="doSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 最后更新时间 -->
    <div class="page-footer">
      数据来源：腾讯证券（实时） + 中证指数 10年历史（行业） + 用户手动（10年分位）
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { updateHoldingPercentile, deleteHoldingPercentile, getHoldingPercentile, getWatchlist } from '../api/index.js'

// ─── 数据 ───
const indices  = ref([])
const loading  = ref(false)
const deleting = ref(null)

// ─── 添加弹窗 ───
const addDialog = ref({
  visible: false,
  code: '',
  name: '',
  verifying: false,
  saving: false,
  hint: '',
  hintType: '',
})

const editDialog = ref({
  visible: false,
  code: '', name: '', pe: null, pb: null,
  pe_pct: null, pb_pct: null, note: '',
  data_source: 'none',
})

// ─── 常量 ───
const BAND_LABELS = {
  extreme_low: '极度低估', low: '偏低',
  normal: '适中',         high: '偏高',
  extreme_high: '极度高估', unknown: '未填分位',
}

const ACTIONS = {
  extreme_low: '强烈买入',  low: '适当买入',
  normal: '持有',           high: '减少买入',
  extreme_high: '考虑减仓', unknown: '待填分位',
}

// 数据来源标签
const SOURCE_TAGS = {
  manual:          'M',
  csi_10y:         'C',
  local_snapshot:  'S',
  tencent:         'T',
  none:            '',
}
const SOURCE_LABELS = {
  manual:          '手动填入',
  csi_10y:         '中证指数 10年历史',
  local_snapshot:  '本地快照',
  tencent:         '实时',
  none:            '',
}

const hasPct = (idx) => {
  return idx.pe_pct != null || idx.pb_pct != null
}
const sourceTag = (idx) => SOURCE_TAGS[idx.data_source] ?? ''
const sourceLabel = (idx) => SOURCE_LABELS[idx.data_source] ?? ''
const historyLabel = (idx) => {
  if (idx.data_source === 'csi_10y') return '10年分位'
  if (idx.data_source === 'local_snapshot') {
    const d = idx.history_days || 0
    return d >= 2000 ? '10年分位' : d >= 30 ? `历史${d}天` : `收集中${d}天`
  }
  return '10年分位'
}

// ─── 工具函数 ───
const fmt = (v, d = 2) => v != null ? v.toFixed(d) : '—'

const pctClass = (v) => {
  if (v == null) return 'neutral'
  if (v < 30) return 'low'
  if (v > 70) return 'high'
  return 'mid'
}

const actionLabel = (band) => ACTIONS[band] || ACTIONS.unknown

function formatUpdated(dt) {
  if (!dt) return '—'
  const d = new Date(dt)
  const now = new Date()
  const diffDays = Math.floor((now - d) / 86400000)
  if (diffDays === 0) return '今日'
  if (diffDays === 1) return '昨日'
  if (diffDays < 30) return diffDays + '天前'
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

// ─── 档位预览 ───
const previewBand = computed(() => {
  const pct = editDialog.value.pe_pct ?? editDialog.value.pb_pct
  if (pct == null) return null
  if (pct < 15) return 'extreme_low'
  if (pct < 35) return 'low'
  if (pct <= 65) return 'normal'
  if (pct <= 85) return 'high'
  return 'extreme_high'
})

// ─── 数据加载 ───
async function loadData() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/valuation/indices')
    indices.value = data
  } catch (e) {
    ElMessage.error('加载失败：' + (e.message || e))
  } finally {
    loading.value = false
  }
}

// ─── 添加指数 ───
async function verifyName() {
  const code = addDialog.value.code.trim()
  if (!code) { addDialog.value.hint = '请先输入指数代码'; addDialog.value.hintType = 'error'; return }
  addDialog.value.verifying = true
  addDialog.value.hint = ''
  try {
    // 先检查是否已存在于自定义指数列表
    const { data } = await axios.get('/api/indices/custom')
    const exists = data.find(r => r.code === code)
    if (exists) {
      addDialog.value.hint = `⚠️  ${code} 已存在（${exists.name}）`
      addDialog.value.hintType = 'error'
      return
    }
    // 用东方财富搜索 API 验证代码并自动填充名称
    const r = await axios.get(`/api/indices/verify/${code}`, { timeout: 8000 })
    if (r.data && r.data.name) {
      addDialog.value.name = r.data.name
      addDialog.value.hint = `✅ 验证成功：${r.data.name}`
      addDialog.value.hintType = 'success'
    } else {
      addDialog.value.hint = '⚠️ 未找到该指数，请检查代码或手动填写名称'
      addDialog.value.hintType = 'warn'
    }
  } catch {
    addDialog.value.hint = '⚠️ 未找到该指数，请检查代码或手动填写名称'
    addDialog.value.hintType = 'warn'
  } finally {
    addDialog.value.verifying = false
  }
}

async function doAdd() {
  const code = addDialog.value.code.trim()
  const name = addDialog.value.name.trim()
  if (!code || !name) { ElMessage.warning('代码和名称均不能为空'); return }
  addDialog.value.saving = true
  try {
    await axios.post('/api/indices/custom', { code, name })
    ElMessage.success(`已添加 ${name}`)
    addDialog.value.visible = false
    addDialog.value.code = ''
    addDialog.value.name = ''
    addDialog.value.hint = ''
    loadData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  } finally {
    addDialog.value.saving = false
  }
}

async function doDelete(idx) {
  // 第 1 步：查询该指数是否被任何自选股票/ETF 关联
  let linkedStocks = []
  try {
    const { data: list } = await getWatchlist()
    linkedStocks = (list || []).filter(s => s.index_code === idx.code)
  } catch (e) {
    ElMessage.error('检查关联失败：' + (e.message || e))
    return
  }

  // 第 2 步：有关联 → 警告弹窗（带关联列表）
  if (linkedStocks.length > 0) {
    const listHtml = linkedStocks.slice(0, 10).map(s => {
      const safeName = String(s.name || s.code).replace(/[<>&"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]))
      return `<li><b>${s.code}</b> ${safeName}</li>`
    }).join('')
    const more = linkedStocks.length > 10 ? `<li><i>…还有 ${linkedStocks.length - 10} 只</i></li>` : ''

    try {
      await ElMessageBox({
        title: '⚠️ 该指数已被关联',
        message: `
          <div style="line-height:1.7;">
            <p>「<b>${idx.name}</b>」（${idx.code}）被以下 <b style="color:#ef232a;">${linkedStocks.length}</b> 只自选品种关联，删除后这些品种的估值信号将失效。</p>
            <ul style="margin: 8px 0 12px 18px; padding:0; color:#444;">${listHtml}${more}</ul>
            <p style="color:#999; font-size:12px; margin:0;">建议：先到「自选区」取消关联，再删除指数。</p>
          </div>
        `,
        dangerouslyUseHTMLString: true,
        showCancelButton: true,
        showConfirmButton: true,
        confirmButtonText: '我已知晓，强制删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
        type: 'warning',
      })
    } catch {
      return  // 用户点取消
    }
  } else {
    // 第 2 步（无关联）：普通确认
    try {
      await ElMessageBox.confirm(
        `确认删除「${idx.name}」（${idx.code}）？删除后无法恢复。`,
        '删除确认',
        { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' }
      )
    } catch {
      return
    }
  }

  // 第 3 步：执行删除
  deleting.value = idx.code
  try {
    await axios.delete(`/api/indices/custom/${idx.code}`, { params: { name: idx.name } })
    ElMessage.success(`已删除 ${idx.name}`)
    loadData()
  } catch (e) {
    ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message || e))
  } finally {
    deleting.value = null
  }
}

function openEdit(idx) {
  editDialog.value = {
    visible: true,
    code: idx.code,
    name: idx.name,
    pe: idx.pe,
    pb: idx.pb,
    pe_pct: idx.pe_pct ?? null,
    pb_pct: idx.pb_pct ?? null,
    note: idx.note || '',
    data_source: idx.data_source,
  }
  // 再次查询确保最新
  getHoldingPercentile(idx.code).then(({ data }) => {
    if (data) {
      editDialog.value.pe_pct = data.pe_pct ?? null
      editDialog.value.pb_pct = data.pb_pct ?? null
      editDialog.value.note = data.note || ''
      editDialog.value.data_source = 'manual'
    }
  }).catch(() => {})
}

async function doSave() {
  const d = editDialog.value
  const payload = {}
  if (d.pe_pct != null) payload.pe_pct = d.pe_pct
  if (d.pb_pct != null) payload.pb_pct = d.pb_pct
  if (d.note) payload.note = d.note
  if (Object.keys(payload).length === 0) {
    ElMessage.warning('请至少填写一项分位')
    return
  }
  try {
    await updateHoldingPercentile(d.code, payload)
    ElMessage.success('保存成功')
    editDialog.value.visible = false
    loadData()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.message || e))
  }
}

async function doClear() {
  if (!confirm('确认清除此指数的分位数据？')) return
  try {
    await deleteHoldingPercentile(editDialog.value.code)
    ElMessage.success('已清除')
    editDialog.value.visible = false
    loadData()
  } catch {
    ElMessage.error('清除失败')
  }
}

// ─── 启动 ───
onMounted(loadData)
</script>

<style scoped>
.page {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px 16px 40px;
}

/* ─── 头部 ─── */
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.head-left { display: flex; align-items: baseline; gap: 12px; }
.head-left h2 { margin: 0; font-size: 20px; font-weight: 700; }
.head-sub { font-size: 13px; color: #888; }
.head-right { display: flex; align-items: center; gap: 12px; }
.last-sync { display: flex; align-items: center; gap: 5px; font-size: 12px; color: #888; }
.sync-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #4caf50; display: inline-block;
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%,100% { opacity: 1; } 50% { opacity: 0.4; }
}

/* ─── 说明条 ─── */
.info-bar {
  background: #f0f7ff;
  border: 1px solid #cce0ff;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 12px;
  color: #555;
  margin-bottom: 18px;
}

/* ─── 加载 ─── */
.loading-state {
  display: flex; align-items: center; gap: 12px;
  padding: 60px 0; color: #888; justify-content: center;
}
.spinner {
  width: 24px; height: 24px; border: 3px solid #e0e0e0;
  border-top-color: #1976d2; border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ─── 网格 ─── */
.index-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

/* ─── 指数卡片 ─── */
.idx-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
  border-top: 4px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: box-shadow .2s, transform .2s;
}
.idx-card:hover { box-shadow: 0 4px 14px rgba(0,0,0,.13); transform: translateY(-1px); }

/* 卡片顶部色条（按档位） */
.band-extreme_low { border-top-color: #1565c0; }
.band-low         { border-top-color: #388e3c; }
.band-normal      { border-top-color: #f9a825; }
.band-high        { border-top-color: #e64a19; }
.band-extreme_high{ border-top-color: #b71c1c; }
.band-unknown     { border-top-color: #bdbdbd; }

/* 自定义指数：左侧紫色条 */
.idx-card.is-custom {
  border-left: 4px solid #7b1fa2;
}
.idx-card.is-custom:hover { border-left-color: #6a1b9a; }

/* 自定义标签 */
.idx-top-right { display: flex; align-items: center; gap: 5px; }
.idx-custom-tag {
  font-size: 10px; color: #fff; background: #7b1fa2;
  border-radius: 3px; padding: 1px 5px; font-weight: 700;
}

/* 卡片基础色（无分位） */
.idx-top { display: flex; align-items: baseline; justify-content: space-between; }
.idx-name { font-size: 15px; font-weight: 700; color: #222; }
.idx-code { font-size: 11px; color: #aaa; font-family: monospace; }
.idx-custom-tag { font-size: 10px; color: #fff; background: #7b1fa2; border-radius: 3px; padding: 1px 5px; font-weight: 700; }

/* 点位行 */
.idx-price-row { display: flex; align-items: baseline; gap: 8px; }
.idx-price { font-size: 22px; font-weight: 700; color: #222; }
.idx-pct   { font-size: 13px; font-weight: 600; }
.idx-pct.up   { color: #e53935; }
.idx-pct.down { color: #43a047; }

/* PE/PB 行 */
.idx-pepb {
  display: flex; align-items: center; gap: 10px;
  background: #fafafa; border-radius: 6px; padding: 6px 10px;
}
.pepb-item { display: flex; align-items: baseline; gap: 5px; }
.pepb-lbl  { font-size: 11px; color: #888; }
.pepb-val  { font-size: 14px; font-weight: 600; color: #444; }
.pepb-divider { flex: 1; }

/* 信号区 */
.idx-signal { flex: 1; }

/* 已填分位 */
.sig-block.filled { display: flex; flex-direction: column; gap: 6px; }
.sig-pct-row { display: flex; align-items: center; gap: 6px; }
.sig-pct-label { font-size: 11px; color: #888; }
.sig-pct-val   { font-size: 18px; font-weight: 800; }
.sig-pct-val.low   { color: #1565c0; }
.sig-pct-val.mid   { color: #666; }
.sig-pct-val.high  { color: #e53935; }
.sig-dot  { font-size: 10px; color: #fff; border-radius: 3px; padding: 1px 4px; font-weight: 700; }
.sig-dot.dot-manual          { background: #1976d2; }   /* 蓝 = 手动 */
.sig-dot.dot-csi_10y         { background: #6a1b9a; }   /* 紫 = 中证 */
.sig-dot.dot-local_snapshot  { background: #2e7d32; }   /* 绿 = 本地快照 */

.sig-band-row { display: flex; align-items: center; gap: 8px; }
.sig-action { font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
.sig-date { font-size: 11px; color: #aaa; }

/* 未填分位 */
.sig-block.empty { display: flex; align-items: center; justify-content: center; padding: 10px 0; }
.sig-unknown { display: flex; align-items: center; gap: 6px; color: #bbb; }
.sig-q { font-size: 20px; font-weight: 700; color: #ccc; }
.sig-q-lbl { font-size: 12px; }

/* 档位徽章 */
.band-badge { font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 4px; }
.badge-extreme_low { background: #e3f2fd; color: #1565c0; }
.badge-low         { background: #e8f5e9; color: #2e7d32; }
.badge-normal      { background: #fff8e1; color: #f57f17; }
.badge-high        { background: #fbe9e7; color: #bf360c; }
.badge-extreme_high{ background: #ffebee; color: #b71c1c; }
.badge-unknown     { background: #f5f5f5; color: #9e9e9e; }

/* 操作建议 */
.action-extreme_low  { background: #e3f2fd; color: #1565c0; }
.action-low          { background: #e8f5e9; color: #2e7d32; }
.action-normal       { background: #fff8e1; color: #f57f17; }
.action-high         { background: #fbe9e7; color: #bf360c; }
.action-extreme_high { background: #ffebee; color: #b71c1c; }
.action-unknown      { background: #f5f5f5; color: #9e9e9e; }

/* 卡片底部 */
.idx-footer { display: flex; justify-content: flex-end; margin-top: 2px; }

/* ─── 添加弹窗 ─── */
.add-hint {
  margin: 4px 0 0 80px;
  font-size: 12px; padding: 6px 10px; border-radius: 4px;
}
.add-hint.success { background: #e8f5e9; color: #2e7d32; }
.add-hint.error   { background: #ffebee; color: #c62828; }
.add-hint.warn    { background: #fff8e1; color: #f57f17; }

/* ─── 编辑弹窗 ─── */
.edit-tip {
  background: #f5f5f5; border-radius: 6px; padding: 8px 12px;
  font-size: 12px; color: #666; display: flex; align-items: center; gap: 12px;
}
.tip-code { font-family: monospace; font-weight: 700; color: #333; }
.tip-pepb { color: #888; }
.form-hint { margin-left: 8px; font-size: 11px; color: #aaa; }

.band-preview {
  background: #fafafa; border-radius: 6px; padding: 8px 12px;
  font-size: 13px; display: flex; align-items: center; gap: 8px; margin-top: 4px;
}
.preview-label { color: #888; font-size: 12px; }
.preview-action { font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 4px; }

/* ─── 页脚 ─── */
.page-footer {
  text-align: center; font-size: 11px; color: #ccc;
  margin-top: 30px; padding-top: 12px; border-top: 1px solid #f0f0f0;
}
</style>
