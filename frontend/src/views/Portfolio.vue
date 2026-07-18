<template>
  <div class="portfolio-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <h1 class="page-title">📊 我的持仓</h1>
        <p class="page-subtitle">基于 PE 分位 + 动态回撤的智能决策系统</p>
      </div>
      <div class="header-actions">
        <el-button plain size="small">
          ⚙️ 设置
        </el-button>
        <el-button type="primary" size="small">
          📋 编辑规则
        </el-button>
        <el-button @click="loadData" :loading="loading" circle>
          <span v-html="refreshIcon"></span>
        </el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载持仓数据中...</p>
    </div>

    <template v-else>
      <!-- 仓位概览 -->
      <div class="position-overview">
        <div class="overview-header">
          <span class="overview-title">📈 仓位概览</span>
          <span class="overview-total">总市值 ¥{{ formatMoney(summary.total_market_value) }}</span>
        </div>
        <div class="overview-grid">
          <div class="overview-item">
            <div class="overview-value">{{ holdings.length }}</div>
            <div class="overview-label">持仓标的</div>
          </div>
          <div class="overview-item">
            <div class="overview-value" :class="summary.total_profit >= 0 ? 'up' : 'down'">
              {{ summary.total_profit >= 0 ? '+' : '-' }}¥{{ formatMoney(summary.total_profit) }}
            </div>
            <div class="overview-label">累计浮盈</div>
          </div>
          <div class="overview-item">
            <div class="overview-value" :class="summary.total_profit_pct >= 0 ? 'up' : 'down'">
              {{ summary.total_profit_pct >= 0 ? '+' : '-' }}{{ Math.abs(summary.total_profit_pct).toFixed(2) }}%
            </div>
            <div class="overview-label">整体收益率</div>
          </div>
          <div class="overview-item">
            <div class="overview-value warning">{{ summary.need_action_count || 0 }}</div>
            <div class="overview-label">待操作</div>
          </div>
        </div>

        <!-- 类型占比条 -->
        <div class="type-distribution" v-if="typeDistribution.length">
          <div class="type-bar">
            <div
              v-for="t in typeDistribution"
              :key="t.type"
              class="type-bar-segment"
              :class="`type-${t.type.toLowerCase()}`"
              :style="{ width: t.pct + '%' }"
              :title="`${t.fullName} ${t.pct}% / ¥${formatMoney(t.amount)}`"
            ></div>
          </div>
          <div class="type-legend">
            <div
              v-for="t in typeDistribution"
              :key="t.type"
              class="type-legend-item"
            >
              <span class="type-dot" :class="`type-${t.type.toLowerCase()}`"></span>
              <span class="type-name">{{ t.fullName }} {{ t.pct }}%</span>
              <span class="type-amount">¥{{ formatMoney(t.amount) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 操作建议 -->
      <div class="section-title">🎯 操作建议</div>

      <!-- 无持仓 -->
      <div v-if="advices.length === 0" class="empty-state">
        <div class="empty-icon">📋</div>
        <div class="empty-title">暂无持仓</div>
        <div class="empty-desc">在交易记录中添加买入记录后，这里将展示操作建议</div>
      </div>

      <!-- 持仓卡片 -->
      <div v-else class="stock-grid">
        <div
          v-for="item in advices"
          :key="item.code"
          class="stock-card"
          :class="{ 'need-action': isNeedAction(item.action) }"
        >
          <!-- 卡片头部 -->
          <div class="card-header">
            <div class="stock-info">
              <div class="stock-avatar" :class="getTypeClass(item.index_type)">
                {{ getTypeName(item.index_type) }}
              </div>
              <div>
                <div class="stock-name">{{ item.name }}</div>
                <div class="stock-code">{{ item.code }}</div>
              </div>
            </div>
            <el-dropdown
              trigger="click"
              @command="(t) => setManualType(item.code, t)"
            >
              <span
                class="stock-type clickable"
                :class="[getTypeClass(item.index_type), { 'manual': hasManualType(item.code) }]"
                :title="hasManualType(item.code) ? '手动设置（点击修改）' : '自动判定（点击手动修改）'"
              >
                {{ getTypeFullName(item.index_type) }}
                <span v-if="hasManualType(item.code)" class="manual-dot" title="手动设置">●</span>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="A">A类 宽基</el-dropdown-item>
                  <el-dropdown-item command="B">B类 成长</el-dropdown-item>
                  <el-dropdown-item command="C">C类 窄基</el-dropdown-item>
                  <el-dropdown-item v-if="hasManualType(item.code)" command="" divided>
                    恢复自动判定
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>

          <!-- 持仓指标 -->
          <div class="metrics-row">
            <div class="metric-item">
              <div class="metric-label">持仓市值</div>
              <div class="metric-value">¥{{ formatMoney(getHoldingValue(item.code)) }}</div>
            </div>
            <div class="metric-item">
              <div class="metric-label">浮盈</div>
              <div class="metric-value" :class="item.current_profit >= 0 ? 'up' : 'down'">
                {{ item.current_profit >= 0 ? '+' : '-' }}¥{{ formatMoney(item.current_profit) }}
              </div>
            </div>
          </div>

          <!-- PE 分位条 -->
          <div class="pe-bar" v-if="item.pe_pct !== null">
            <div class="pe-bar-header">
              <span>PE分位：<strong>{{ item.pe_pct.toFixed(1) }}%</strong></span>
              <span :class="getBandClass(item.pe_band)">{{ getBandName(item.pe_band) }}</span>
            </div>
            <div class="pe-track">
              <div class="pe-fill" :class="getBandClass(item.pe_band)" :style="{ width: item.pe_pct + '%' }"></div>
            </div>
            <div class="pe-markers">
              <span>0%</span><span>30%</span><span>70%</span><span>100%</span>
            </div>
          </div>
          <div v-else class="pe-bar">
            <div class="pe-bar-header">
              <span class="no-pe">暂无 PE 分位数据</span>
            </div>
          </div>

          <!-- 操作建议 -->
          <div class="action-box" :class="getActionClass(item.action)">
            <div class="action-title">
              {{ getActionIcon(item.action) }} {{ item.action }}
              <span v-if="item.action_ratio && item.action_ratio > 1" class="action-ratio">
                ×{{ item.action_ratio }}
              </span>
              <span v-if="item.action_ratio && item.action_ratio < 1" class="action-ratio">
                -{{ (item.action_ratio * 100).toFixed(0) }}%
              </span>
            </div>
            <div class="action-desc">{{ item.action_desc }}</div>
          </div>

          <!-- 回撤状态 -->
          <div class="drawdown-info">
            <div class="drawdown-status">
              <span class="status-dot" :class="getDrawdownClass(item.drawdown_pct)"></span>
              <span>回撤状态</span>
            </div>
            <div class="drawdown-detail">
              <span>最高 ¥{{ formatMoney(item.peak_profit) }}</span>
              <span class="drawdown-value" :class="getDrawdownClass(item.drawdown_pct)">
                {{ item.drawdown_pct > 0 ? '-' : '' }}{{ item.drawdown_pct.toFixed(1) }}%
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 规则说明 -->
      <div class="rules-section">
        <div class="rules-title">📖 规则速查</div>
        <div class="rules-grid">
          <div class="rule-card">
            <div class="rule-type type-a">A类 宽基规则</div>
            <div class="rule-content">
              <div>加仓：≤20% ×2.0 / 20-30% ×1.5 / 30-70% ×1.0</div>
              <div>止盈：70-80% 卖1/3 / 80-90% 卖1/3 / >90% 清仓</div>
              <div>重启：PE ≤ 30%</div>
            </div>
          </div>
          <div class="rule-card">
            <div class="rule-type type-b">B类 成长规则</div>
            <div class="rule-content">
              <div>加仓：同A类</div>
              <div>止盈：75-85% 卖1/3 / 85-90% 卖1/3 / >90% 清仓</div>
              <div>重启：PE ≤ 30%</div>
            </div>
          </div>
          <div class="rule-card">
            <div class="rule-type type-c">C类 窄基规则</div>
            <div class="rule-content">
              <div>加仓：≤25% ×1.5 / 25-40% ×1.0 / 40-70% ×0.5</div>
              <div>止盈：70-80% 卖1/2 / >80% 清仓</div>
              <div>重启：PE ≤ 25%</div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { getPortfolioHoldings, getPortfolioAdvices } from '../api/index.js'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const holdings = ref([])
const advices = ref([])
const summary = reactive({
  total_cost: 0,
  total_market_value: 0,
  total_profit: 0,
  total_profit_pct: 0,
  need_action_count: 0
})

const refreshIcon = '🔄'

async function loadData() {
  loading.value = true
  try {
    // 并行请求
    const [holdingsRes, advicesRes] = await Promise.all([
      getPortfolioHoldings(),
      getPortfolioAdvices(manualTypes.value)
    ])

    holdings.value = holdingsRes.data.holdings || []
    summary.total_cost = holdingsRes.data.total_cost || 0
    summary.total_market_value = holdingsRes.data.total_market_value || 0
    summary.total_profit = holdingsRes.data.total_profit || 0
    summary.total_profit_pct = holdingsRes.data.total_profit_pct || 0

    advices.value = advicesRes.data.holdings || []
    summary.need_action_count = advicesRes.data.summary?.need_action_count || 0
  } catch (err) {
    console.error('加载持仓数据失败', err)
    ElMessage.error('加载持仓数据失败')
  } finally {
    loading.value = false
  }
}

function formatMoney(val) {
  if (!val) return '0.00'
  return Math.abs(val).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function getHoldingValue(code) {
  const h = holdings.value.find(item => item.code === code)
  return h ? h.market_value : 0
}

const typeDistribution = computed(() => {
  const total = summary.total_market_value || 0
  if (!total || !advices.value.length) return []
  // 按类型汇总市值
  const map = {}
  for (const item of advices.value) {
    const t = item.index_type || 'A'
    map[t] = (map[t] || 0) + (item.market_value || 0)
  }
  // 产出顺序 A → B → C
  const order = ['A', 'B', 'C']
  const fullName = { A: 'A类 宽基', B: 'B类 成长', C: 'C类 窄基' }
  return order
    .filter(t => map[t])
    .map(t => ({
      type: t,
      fullName: fullName[t],
      amount: map[t],
      pct: Math.round((map[t] / total) * 100),
    }))
})

function getTypeClass(type) {
  return `type-${type.toLowerCase()}`
}

// ── 手动类型覆盖（localStorage 持久化）──
const TYPE_OVERRIDE_KEY = 'portfolio_type_overrides'

function loadTypeOverrides() {
  try {
    return JSON.parse(localStorage.getItem(TYPE_OVERRIDE_KEY) || '{}')
  } catch {
    return {}
  }
}

const manualTypes = ref(loadTypeOverrides())

function saveTypeOverrides() {
  localStorage.setItem(TYPE_OVERRIDE_KEY, JSON.stringify(manualTypes.value))
}

function getEffectiveType(item) {
  return manualTypes.value[item.code] || item.index_type
}

function hasManualType(code) {
  return Object.prototype.hasOwnProperty.call(manualTypes.value, code)
}

function setManualType(code, type) {
  if (!type) {
    delete manualTypes.value[code]
  } else {
    manualTypes.value[code] = type
  }
  saveTypeOverrides()
  ElMessage.success(type ? `已手动设为 ${getTypeFullName(type)}` : '已恢复自动判定')
  // 重新拉取建议以应用新类型
  loadData()
}

function getTypeName(type) {
  const map = { A: '宽基', B: '成长', C: '窄基' }
  return map[type] || type
}

function getTypeFullName(type) {
  const map = { A: 'A类 宽基', B: 'B类 成长', C: 'C类 窄基' }
  return map[type] || type
}

function getBandClass(band) {
  const map = {
    'extreme_low': 'low',
    'low': 'low',
    'normal': 'normal',
    'high': 'high',
    'extreme_high': 'extreme',
    'unknown': 'normal'
  }
  return map[band] || 'normal'
}

function getBandName(band) {
  const map = {
    'extreme_low': '极度低估',
    'low': '低估',
    'normal': '合理',
    'high': '高估',
    'extreme_high': '极度高估',
    'unknown': '未知'
  }
  return map[band] || '未知'
}

function getActionIcon(action) {
  const map = {
    '加倍买入': '✅',
    '加半买入': '✅',
    '正常持有': '📊',
    '减半持有': '📉',
    '持仓观望': '👀',
    '减仓': '📤',
    '大幅减仓': '📤',
    '清仓': '🧹'
  }
  return map[action] || '📊'
}

function getActionClass(action) {
  if (action.includes('买入')) return 'action-buy'
  if (action.includes('清仓')) return 'action-sell-all'
  if (action.includes('减仓') || action.includes('大幅')) return 'action-sell'
  if (action.includes('观望')) return 'action-watch'
  return 'action-hold'
}

function isNeedAction(action) {
  return ['加倍买入', '加半买入', '减仓', '大幅减仓', '清仓'].includes(action)
}

function getDrawdownClass(pct) {
  if (pct <= 15) return 'green'
  if (pct <= 25) return 'yellow'
  if (pct <= 40) return 'orange'
  return 'red'
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.portfolio-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: #666;
  margin-top: 4px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* 加载状态 */
.loading-state {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e8e8ee;
  border-top-color: #4a6cf7;
  border-radius: 50%;
  margin: 0 auto 16px;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 仓位概览 */
.position-overview {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 24px;
  color: #fff;
  margin-bottom: 24px;
}

.overview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.overview-title {
  font-size: 14px;
  opacity: 0.9;
}

.overview-total {
  font-size: 16px;
  font-weight: 600;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.overview-item {
  text-align: center;
}

/* 类型占比条 */
.type-distribution {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid rgba(255,255,255,0.2);
}

.type-bar {
  display: flex;
  height: 8px;
  border-radius: 4px;
  overflow: hidden;
  background: rgba(255,255,255,0.15);
  gap: 2px;
}

.type-bar-segment {
  height: 100%;
  transition: width 0.4s ease;
  cursor: pointer;
}

.type-bar-segment.type-a { background: #22c55e; }
.type-bar-segment.type-b { background: #3b82f6; }
.type-bar-segment.type-c { background: #ec4899; }

.type-legend {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 10px;
  font-size: 12px;
  color: rgba(255,255,255,0.95);
}

.type-legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 1;
}

.type-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.type-dot.type-a { background: #22c55e; }
.type-dot.type-b { background: #3b82f6; }
.type-dot.type-c { background: #ec4899; }

.type-name {
  font-weight: 500;
}

.type-amount {
  color: rgba(255,255,255,0.7);
  font-size: 11px;
  margin-left: auto;
}

.overview-value {
  font-size: 28px;
  font-weight: 600;
}

.overview-value.up {
  color: #fde68a;
}

.overview-value.down {
  color: #fca5a5;
}

.overview-value.warning {
  color: #fde047;
}

.overview-label {
  font-size: 12px;
  opacity: 0.8;
  margin-top: 4px;
}

/* 无持仓 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  background: #fff;
  border-radius: 12px;
  border: 2px dashed #e8e8ee;
  margin-bottom: 24px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: #666;
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
  color: #999;
}

/* 区块标题 */
.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 标的卡片 */
.stock-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stock-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  border: 2px solid #e8e8ee;
  transition: all 0.2s;
}

.stock-card.need-action {
  border-color: #fde047;
  background: #fffef0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.stock-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stock-avatar {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.stock-avatar.type-a { background: linear-gradient(135deg, #4ade80, #22c55e); }
.stock-avatar.type-b { background: linear-gradient(135deg, #60a5fa, #3b82f6); }
.stock-avatar.type-c { background: linear-gradient(135deg, #f472b6, #ec4899); }

.stock-name {
  font-size: 16px;
  font-weight: 600;
}

.stock-code {
  font-size: 12px;
  color: #999;
}

.stock-type {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.15s;
}

.stock-type.clickable {
  cursor: pointer;
  user-select: none;
  border: 1px solid transparent;
}

.stock-type.clickable:hover {
  filter: brightness(0.95);
  border-color: currentColor;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0,0,0,0.08);
}

.stock-type.manual {
  outline: 2px dashed currentColor;
  outline-offset: 1px;
}

.manual-dot {
  font-size: 8px;
  opacity: 0.7;
}

.stock-type.type-a { background: #dcfce7; color: #166534; }
.stock-type.type-b { background: #dbeafe; color: #1e40af; }
.stock-type.type-c { background: #fce7f3; color: #9d174d; }

/* 指标行 */
.metrics-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.metric-item {
  background: #f9fafb;
  padding: 12px;
  border-radius: 8px;
}

.metric-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 18px;
  font-weight: 600;
}

.metric-value.up { color: #ef4444; }
.metric-value.down { color: #22c55e; }

/* PE 条 */
.pe-bar {
  margin-bottom: 16px;
}

.pe-bar-header {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #666;
  margin-bottom: 6px;
}

.pe-bar-header strong {
  color: #1a1a2e;
}

.pe-bar-header .no-pe {
  color: #999;
}

.pe-track {
  height: 8px;
  background: #e8e8ee;
  border-radius: 4px;
  overflow: hidden;
}

.pe-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

.pe-fill.low { background: linear-gradient(90deg, #22c55e, #4ade80); }
.pe-fill.normal { background: linear-gradient(90deg, #facc15, #fde047); }
.pe-fill.high { background: linear-gradient(90deg, #f97316, #fb923c); }
.pe-fill.extreme { background: linear-gradient(90deg, #ef4444, #f87171); }

.pe-markers {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #999;
  margin-top: 4px;
}

/* 操作建议 */
.action-box {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 12px;
}

.action-box.action-buy { background: #f0fdf4; border-color: #bbf7d0; }
.action-box.action-hold { background: #f0f9ff; border-color: #bae6fd; }
.action-box.action-watch { background: #fef9c3; border-color: #fde047; }
.action-box.action-sell { background: #fff7ed; border-color: #fed7aa; }
.action-box.action-sell-all { background: #fef2f2; border-color: #fecaca; }

.action-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.action-ratio {
  font-size: 12px;
  background: rgba(0,0,0,0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.action-desc {
  font-size: 12px;
  color: #666;
  line-height: 1.5;
}

/* 回撤状态 */
.drawdown-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
  font-size: 13px;
}

.drawdown-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.green { background: #22c55e; }
.status-dot.yellow { background: #facc15; }
.status-dot.orange { background: #f97316; }
.status-dot.red { background: #ef4444; }

.drawdown-detail {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #666;
}

.drawdown-value {
  font-weight: 600;
}

.drawdown-value.green { color: #22c55e; }
.drawdown-value.yellow { color: #facc15; }
.drawdown-value.orange { color: #f97316; }
.drawdown-value.red { color: #ef4444; }

/* 规则说明 */
.rules-section {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  border: 1px solid #e8e8ee;
}

.rules-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
}

.rules-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.rule-card {
  padding: 16px;
  background: #f9fafb;
  border-radius: 8px;
}

.rule-type {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
}

.rule-type.type-a { color: #166534; }
.rule-type.type-b { color: #1e40af; }
.rule-type.type-c { color: #9d174d; }

.rule-content {
  font-size: 12px;
  color: #666;
  line-height: 1.6;
}

.rule-content div {
  margin-bottom: 4px;
}

/* 响应式 */
@media (max-width: 768px) {
  .overview-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .stock-grid {
    grid-template-columns: 1fr;
  }

  .rules-grid {
    grid-template-columns: 1fr;
  }
}
</style>
