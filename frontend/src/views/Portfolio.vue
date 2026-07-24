<template>
  <div class="portfolio-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <h1 class="page-title">💼 我的持仓</h1>
        <p class="page-subtitle">移动止盈 + 硬止损 · 波段仓 · 纯回撤策略</p>
      </div>
      <div class="header-actions">
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
            <div class="overview-label">持仓浮盈</div>
          </div>
          <div class="overview-item">
            <div class="overview-value" :class="summary.total_return >= 0 ? 'up' : 'down'">
              {{ summary.total_return >= 0 ? '+' : '-' }}¥{{ formatMoney(summary.total_return) }}
            </div>
            <div class="overview-label">累计收益（含已清仓）</div>
          </div>
          <div class="overview-item">
            <div class="overview-value" :class="summary.total_return_pct >= 0 ? 'up' : 'down'">
              {{ summary.total_return_pct >= 0 ? '+' : '-' }}{{ Math.abs(summary.total_return_pct).toFixed(2) }}%
            </div>
            <div class="overview-label">累计收益率</div>
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
                  <el-dropdown-item command="A">A类 大盘宽基ETF</el-dropdown-item>
                  <el-dropdown-item command="B">B类 科创创业ETF</el-dropdown-item>
                  <el-dropdown-item command="C">C类 科技赛道ETF</el-dropdown-item>
                  <el-dropdown-item command="D">D类 恒生科技ETF</el-dropdown-item>
                  <el-dropdown-item command="E">E类 红利ETF</el-dropdown-item>
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
                <span class="metric-pct">({{ item.current_profit >= 0 ? '+' : '' }}{{ item.profit_pct.toFixed(2) }}%)</span>
              </div>
            </div>
          </div>

          <!-- 操作建议 -->
          <div class="action-box" :class="getActionClass(item.action)">
            <div class="action-title">
              {{ getActionIcon(item.action) }} {{ item.action }}
              <span v-if="item.action_ratio && item.action_ratio > 1" class="action-ratio">
                ×{{ item.action_ratio }}
              </span>
              <span v-if="item.action_ratio && item.action_ratio < 1 && item.action_ratio > 0" class="action-ratio">
                ×{{ (item.action_ratio * 1).toFixed(1) }}
              </span>
            </div>
            <div class="action-desc">{{ item.action_desc }}</div>
          </div>

          <!-- 预警提醒 -->
          <div v-if="item.warnings && item.warnings.length > 0" class="warnings-box">
            <div
              v-for="(w, wi) in item.warnings"
              :key="wi"
              class="warning-item"
            >{{ w }}</div>
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

      <!-- 规则说明（5档） -->
      <div class="rules-section">
        <div class="rules-title">📖 规则速查</div>
        <div class="rules-grid">
          <div class="rule-card">
            <div class="rule-type type-a">A类 大盘宽基ETF</div>
            <div class="rule-content">
              <div class="rule-sub-title">止盈（三重模式，满足任一即执行）</div>
              <div>1️⃣ 目标：回撤<strong>12%</strong>→减40% / <strong>18%</strong>→全部清仓波段仓</div>
              <div>2️⃣ 均线：跌破MA20→全部清仓；破MA10观察3日</div>
              <div>3️⃣ 极端：跌幅≥5%+量放≥1.5倍→尾盘减50%</div>
              <div class="rule-sub-title">止损（三重模式）</div>
              <div>硬性止损：浮亏<strong>-8%</strong>→无条件清仓</div>
              <div class="rule-sub-title">买入</div>
              <div>回落6%~10%介入，长线定投≥14%回撤启动</div>
            </div>
          </div>
          <div class="rule-card">
            <div class="rule-type type-b">B类 科创50/创业板ETF</div>
            <div class="rule-content">
              <div class="rule-sub-title">止盈（三重模式，满足任一即执行）</div>
              <div>1️⃣ 目标：回撤<strong>13%</strong>→减40% / <strong>20%</strong>→全部清仓波段仓</div>
              <div>2️⃣ 均线：跌破MA20→全部清仓；破MA10观察3日</div>
              <div>3️⃣ 极端：跌幅≥6%+换手≥7%→尾盘减60%</div>
              <div class="rule-sub-title">止损（三重模式）</div>
              <div>硬性止损：浮亏<strong>-8%</strong>→无条件清仓</div>
              <div class="rule-sub-title">买入</div>
              <div>回落7%~11%介入，长线定投≥16%回撤启动</div>
            </div>
          </div>
          <div class="rule-card">
            <div class="rule-type type-c">C类 科技赛道ETF</div>
            <div class="rule-content">
              <div class="rule-sub-title">止盈（三重模式，满足任一即执行）</div>
              <div>1️⃣ 目标：回撤<strong>15%</strong>→减40% / <strong>25%</strong>→全部清仓波段仓</div>
              <div>2️⃣ 均线：跌破MA10→减半仓；跌破MA20→清仓</div>
              <div>3️⃣ 极端：跌幅≥7%+换手≥8%→尾盘减70%</div>
              <div class="rule-sub-title special-clear">🔥特殊清仓</div>
              <div>换手率≥7%+放量滞涨→跳过止盈，直接全部清仓</div>
              <div class="rule-sub-title">止损（三重模式）</div>
              <div>硬性止损：浮亏<strong>-9%</strong>→无条件清仓</div>
              <div class="rule-sub-title">买入</div>
              <div>回落8%~12%介入，长线定投≥18%回撤启动</div>
            </div>
          </div>
          <div class="rule-card">
            <div class="rule-type type-d">D类 恒生科技ETF</div>
            <div class="rule-content">
              <div class="rule-sub-title">止盈（三重模式，满足任一即执行）</div>
              <div>1️⃣ 目标：回撤<strong>15%</strong>→减40% / <strong>25%</strong>→全部清仓波段仓</div>
              <div>2️⃣ 均线：跌破MA10→减半仓(3日未收清)；破MA20→全部清仓</div>
              <div>3️⃣ 极端：跌幅≥6%+量放→减50%</div>
              <div class="rule-sub-title">止损（三重模式）</div>
              <div>硬性止损：浮亏<strong>-9%</strong>→无条件清仓</div>
              <div class="rule-sub-title">买入</div>
              <div>回落8%~13%介入，长线定投≥20%回撤启动</div>
            </div>
          </div>
          <div class="rule-card">
            <div class="rule-type type-e">E类 红利ETF</div>
            <div class="rule-content">
              <div class="rule-sub-title">止盈（三重模式，满足任一即执行）</div>
              <div>1️⃣ 目标：回撤<strong>20%</strong>→减40% / <strong>30%</strong>→全部清仓波段仓</div>
              <div>2️⃣ 均线：跌破MA20→全部清仓；破MA10观察5日</div>
              <div>3️⃣ 极端：跌幅≥4%+量放≥1.4倍→尾盘减50%</div>
              <div class="rule-sub-title">止损（三重模式）</div>
              <div>硬性止损：浮亏<strong>-6%</strong>→无条件清仓</div>
              <div class="rule-sub-title">买入</div>
              <div>回落5%~8%介入，低估值+分红率≥3%时定投</div>
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
  total_return: 0,
  total_return_pct: 0,
  need_action_count: 0
})

const refreshIcon = '🔄'

async function loadData() {
  loading.value = true
  try {
    const [holdingsRes, advicesRes] = await Promise.all([
      getPortfolioHoldings(),
      getPortfolioAdvices(manualTypes.value)
    ])

    holdings.value = holdingsRes.data.holdings || []
    summary.total_cost = holdingsRes.data.total_cost || 0
    summary.total_market_value = holdingsRes.data.total_market_value || 0
    summary.total_profit = holdingsRes.data.total_profit || 0
    summary.total_profit_pct = holdingsRes.data.total_profit_pct || 0
    summary.total_return = holdingsRes.data.total_return || 0
    summary.total_return_pct = holdingsRes.data.total_return_pct || 0

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
  const map = {}
  for (const item of advices.value) {
    const t = item.index_type || 'A'
    map[t] = (map[t] || 0) + (item.market_value || 0)
  }
  const order = ['A', 'B', 'C', 'D', 'E']
  const fullName = {
    A: 'A类 大盘宽基ETF',
    B: 'B类 科创创业ETF',
    C: 'C类 科技赛道ETF',
    D: 'D类 恒生科技ETF',
    E: 'E类 红利ETF',
  }
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
  return `type-${(type || 'A').toLowerCase()}`
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
  ElMessage.success(type ? `已设为 ${getTypeFullName(type)}` : '已恢复自动判定')
  loadData()
}

function getTypeName(type) {
  const map = { A: '宽基', B: '科创', C: '赛道', D: '恒科', E: '红利' }
  return map[type] || '宽基'
}

function getTypeFullName(type) {
  const map = {
    A: 'A类 大盘宽基ETF',
    B: 'B类 科创创业ETF',
    C: 'C类 科技赛道ETF',
    D: 'D类 恒生科技ETF',
    E: 'E类 红利ETF',
  }
  return map[type] || map['A']
}

function getActionIcon(action) {
  const map = {
    '持有': '📊',
    '减仓': '📤',
    '清仓': '🧹',
    '止损清仓': '🛑',
    '观察': '👁',
  }
  return map[action] || '📊'
}

function getActionClass(action) {
  if (action.includes('清仓')) return 'action-sell-all'
  if (action.includes('减仓')) return 'action-sell'
  if (action === '观察') return 'action-watch'
  return 'action-hold'
}

function isNeedAction(action) {
  return ['减仓', '清仓', '止损清仓', '观察'].includes(action)
}

function getDrawdownClass(pct) {
  if (pct <= 10) return 'green'
  if (pct <= 20) return 'yellow'
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
.type-bar-segment.type-d { background: #f59e0b; }
.type-bar-segment.type-e { background: #06b6d4; }

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
.type-dot.type-d { background: #f59e0b; }
.type-dot.type-e { background: #06b6d4; }

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
.stock-avatar.type-d { background: linear-gradient(135deg, #fbbf24, #f59e0b); }
.stock-avatar.type-e { background: linear-gradient(135deg, #22d3ee, #06b6d4); }

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
.stock-type.type-d { background: #fef3c7; color: #92400e; }
.stock-type.type-e { background: #ecfeff; color: #0e7490; }

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

.metric-pct {
  font-size: 12px;
  font-weight: 500;
  opacity: 0.7;
  margin-left: 4px;
}

/* 操作建议 */
.action-box {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 12px;
}

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

/* 预警提醒 */
.warnings-box {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 12px;
}

.warning-item {
  font-size: 12px;
  color: #92400e;
  line-height: 1.6;
  padding: 2px 0;
}

.warning-item:not(:last-child) {
  border-bottom: 1px dashed #fde68a;
  margin-bottom: 4px;
  padding-bottom: 6px;
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
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.rule-card {
  padding: 14px;
  background: #f9fafb;
  border-radius: 8px;
}

.rule-type {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
}

.rule-type.type-a { color: #166534; }
.rule-type.type-b { color: #1e40af; }
.rule-type.type-c { color: #9d174d; }
.rule-type.type-d { color: #92400e; }
.rule-type.type-e { color: #0e7490; }

.rule-content {
  font-size: 11px;
  color: #555;
  line-height: 1.7;
}

.rule-content div {
  margin-bottom: 3px;
}

.rule-content strong {
  color: #1a1a2e;
  font-weight: 600;
}

.rule-sub-title {
  font-size: 11px;
  font-weight: 700;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: 6px !important;
  margin-bottom: 2px !important;
}

.rule-content .special-clear {
  color: #dc2626;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
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
