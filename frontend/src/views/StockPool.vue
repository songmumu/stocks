<template>
  <div>
    <div class="page-header">
      <h2>自选管理</h2>
      <el-button type="primary" @click="openAddDialog">+ 添加{{ activeTab === 'fund' ? '基金' : '股票' }}</el-button>
    </div>

    <el-tabs v-model="activeTab" class="pool-tabs">
      <el-tab-pane label="股票" name="stock" />
      <el-tab-pane label="基金" name="fund" />
    </el-tabs>

    <!-- 添加对话框 -->
    <el-dialog v-model="showAddDialog" :title="`添加${addForm.stock_type === 'fund' ? '基金' : '股票'}`" width="500px">
      <el-form :model="addForm" label-width="80px">
        <el-form-item label="搜索">
          <el-input v-model="addForm.code" placeholder="输入代码或名称，如 600519 / 510300" @input="debounceSearch" clearable>
            <template #prefix>🔍</template>
          </el-input>
        </el-form-item>
        <div v-if="searchResults.length > 0" class="search-results">
          <div
            v-for="item in searchResults"
            :key="item.code"
            class="search-item"
            @click="selectSearchResult(item)"
          >
            <span class="si-code">{{ item.code }}</span>
            <span class="si-name">{{ item.name }}</span>
            <span class="si-type">{{ item.type_desc }}</span>
          </div>
        </div>
        <el-form-item label="名称">
          <el-input v-model="addForm.name" placeholder="搜索后自动填入" disabled />
        </el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="addForm.stock_type">
            <el-radio value="stock">股票</el-radio>
            <el-radio value="fund">基金</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="addForm.notes" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!addForm.name" @click="handleAdd">确认添加</el-button>
      </template>
    </el-dialog>

    <!-- 列表 -->
    <div v-if="loading" class="page-loading">
      <div class="spinner"></div>
      <div>加载自选{{ activeTab === 'fund' ? '基金' : '股票' }}中...</div>
    </div>

    <div v-else-if="displayList.length === 0" class="empty-state">
      <div class="empty-icon">📊</div>
      <div class="empty-title">还没有自选{{ activeTab === 'fund' ? '基金' : '股票' }}</div>
      <div class="empty-desc">点击右上角添加，开始构建你的{{ activeTab === 'fund' ? '基金' : '股票' }}池</div>
      <el-button type="primary" plain @click="openAddDialog">+ 添加第一只</el-button>
    </div>

    <div v-else class="stock-grid">
      <div v-for="stock in displayList" :key="stock.id" class="stock-card" @click="goDetail(stock.id)">
        <div class="card-header">
          <div>
            <div class="stock-name">{{ stock.name }}</div>
            <div class="stock-meta">
              {{ stock.code }}
              <span class="dot">·</span>
              {{ stock.stock_type === 'fund' ? '基金' : '股票' }}
            </div>
          </div>
          <el-popconfirm title="确定移除该自选？" @confirm.stop="handleRemove(stock.id)">
            <template #reference>
              <button class="btn-remove" @click.stop>移除</button>
            </template>
          </el-popconfirm>
        </div>

        <div class="card-body">
          <template v-if="quotes[stock.code]">
            <!-- 场外基金：净值显示 -->
            <div v-if="quotes[stock.code].is_nav" class="quote-nav">
              <div class="nav-row">
                <span class="nav-label">净值</span>
                <span class="nav-price" :class="quotes[stock.code].change >= 0 ? 'up' : 'down'">
                  {{ fmtPrice(stock, quotes[stock.code].price) }}
                </span>
              </div>
              <div class="nav-row">
                <span class="nav-label">涨跌</span>
                <span class="nav-change" :class="quotes[stock.code].change >= 0 ? 'up' : 'down'">
                  {{ quotes[stock.code].change >= 0 ? '+' : '' }}{{ quotes[stock.code].change?.toFixed(2) }}%
                </span>
              </div>
              <div class="nav-date">{{ quotes[stock.code].date }}</div>
            </div>
            <div v-else-if="quotes[stock.code].no_intraday" class="quote-no-intraday">
              <div class="no-intra-icon">⏸️</div>
              <div>场外基金，暂无实时行情</div>
              <div class="no-intra-hint">每日收盘后更新净值</div>
            </div>
            <!-- 正常行情 -->
            <template v-else>
              <div class="price-row">
                <span class="price" :class="quotes[stock.code].change >= 0 ? 'up' : 'down'">
                  {{ fmtPrice(stock, quotes[stock.code].price) }}
                </span>
                <span class="change-pct" :class="quotes[stock.code].change >= 0 ? 'up' : 'down'">
                  {{ quotes[stock.code].change >= 0 ? '▲' : '▼' }}
                  {{ Math.abs(quotes[stock.code].change).toFixed(2) }}%
                </span>
              </div>
              <!-- 股票 / ETF（场内）：开高低 + 换手率 -->
              <div v-if="!isFund(stock) || hasIntraday(quotes[stock.code])" class="info-row">
                <div class="info-item">
                  <span class="info-label">开</span>
                  <span>{{ fmtPrice(stock, quotes[stock.code].open) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">高</span>
                  <span class="up">{{ fmtPrice(stock, quotes[stock.code].high) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">低</span>
                  <span class="down">{{ fmtPrice(stock, quotes[stock.code].low) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">换手</span>
                  <span>{{ quotes[stock.code].turnover_rate?.toFixed(2) }}%</span>
                </div>
              </div>
              <!-- 场外开放式基金：净值 + 涨跌额 -->
              <div v-else class="info-row fund-row">
                <div class="info-item">
                  <span class="info-label">涨跌额</span>
                  <span :class="quotes[stock.code].change_amount >= 0 ? 'up' : 'down'">
                    {{ quotes[stock.code].change_amount >= 0 ? '+' : '' }}{{ quotes[stock.code].change_amount?.toFixed(4) }}
                  </span>
                </div>
                <div class="info-item">
                  <span class="info-label">昨净</span>
                  <span>{{ fmtPrice(stock, quotes[stock.code].pre_close) }}</span>
                </div>
              </div>
            </template>
          </template>
          <div v-else-if="quotes[stock.code] === null" class="quote-error">
            ⚠️ 获取行情失败
          </div>
          <div v-else class="quote-loading">
            <div class="mini-spinner"></div>
            加载行情中...
          </div>
        </div>

        <div v-if="stock.notes" class="card-notes">📝 {{ stock.notes }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getWatchlist, addWatchlist, removeWatchlist, searchStocks, getRealtimeQuote, getStockHistory } from '../api/index.js'

const router = useRouter()

const watchlist = ref([])
const loading = ref(false)
const activeTab = ref('stock')
const showAddDialog = ref(false)
const searchResults = ref([])
const addForm = ref({ code: '', name: '', stock_type: 'stock', notes: '' })
const quotes = ref({})

const displayList = computed(() => watchlist.value.filter(s => s.stock_type === activeTab.value))

let searchTimer = null

function isFund(stock) {
  return stock.stock_type === 'fund'
}
function hasIntraday(q) {
  return q && q.open && q.high && q.low
}
function fmtPrice(stock, p) {
  if (p === null || p === undefined) return '—'
  const decimals = stock.stock_type === 'fund' ? 4 : 2
  return Number(p).toFixed(decimals)
}

async function loadWatchlist() {
  loading.value = true
  try {
    const { data } = await getWatchlist()
    watchlist.value = data || []
    data?.forEach(s => loadQuote(s.code))
  } catch (e) {
    console.error('加载自选失败', e)
  } finally {
    loading.value = false
  }
}

async function loadQuote(code) {
  quotes.value[code] = undefined
  try {
    const { data } = await getRealtimeQuote(code)
    if (data && data.no_intraday) {
      // 场外基金：用K线数据回填净值
      try {
        const { data: hist } = await getStockHistory(code, 30)
        const bars = hist?.bars || []
        if (bars.length >= 1) {
          const latest = bars[bars.length - 1]
          const prev = bars[bars.length - 2]
          quotes.value[code] = {
            no_intraday: true,
            is_nav: true,
            price: latest.close,
            pre_close: prev ? prev.close : latest.close,
            date: latest.date,
            change: prev ? ((latest.close - prev.close) / prev.close * 100) : 0,
          }
        } else {
          quotes.value[code] = { no_intraday: true }
        }
      } catch {
        quotes.value[code] = { no_intraday: true }
      }
    } else {
      quotes.value[code] = data
    }
  } catch (e) {
    quotes.value[code] = null
  }
}

function openAddDialog() {
  showAddDialog.value = true
  searchResults.value = []
  addForm.value = { code: '', name: '', stock_type: activeTab.value, notes: '' }
}

function debounceSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(doSearch, 300)
}

async function doSearch() {
  const kw = addForm.value.code.trim()
  if (!kw) { searchResults.value = []; return }
  try {
    const { data } = await searchStocks(kw)
    const items = data.items || []
    searchResults.value = items
    // 只有一条结果时自动选中填入名称（避免用户多步点击）
    if (items.length === 1 && addForm.value.name !== items[0].name) {
      addForm.value.name = items[0].name
    }
  } catch (e) {
    searchResults.value = []
  }
}

function selectSearchResult(item) {
  addForm.value.code = item.code
  addForm.value.name = item.name
  searchResults.value = []
}

async function handleAdd() {
  if (!addForm.value.code || !addForm.value.name) return
  try {
    await addWatchlist(addForm.value)
    ElMessage.success('已添加')
    showAddDialog.value = false
    loadWatchlist()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  }
}

async function handleRemove(id) {
  try {
    await removeWatchlist(id)
    ElMessage.success('已移除')
    loadWatchlist()
  } catch (e) {
    ElMessage.error('移除失败')
  }
}

function goDetail(id) {
  router.push(`/stocks/${id}`)
}

onMounted(loadWatchlist)
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #1a1a2e;
}
.pool-tabs { margin-bottom: 4px; }

.search-results {
  margin: -8px 0 12px 80px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  max-height: 220px;
  overflow-y: auto;
  background: #fff;
}
.search-item {
  padding: 8px 12px;
  cursor: pointer;
  display: grid;
  grid-template-columns: 80px 1fr auto;
  gap: 12px;
  align-items: center;
  border-bottom: 1px solid #f5f5f5;
  font-size: 13px;
}
.search-item:last-child { border-bottom: none; }
.search-item:hover { background: #f5f7fa; }
.si-code { color: #999; font-variant-numeric: tabular-nums; }
.si-name { color: #1a1a2e; font-weight: 500; }
.si-type { color: #aaa; font-size: 12px; }

/* 列表 */
.stock-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}
.stock-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,.05);
  transition: all .15s;
  border: 1px solid #f0f0f0;
  cursor: pointer;
}
.stock-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,.08);
  transform: translateY(-1px);
  border-color: #c6e2ff;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}
.stock-name {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}
.stock-meta {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}
.stock-meta .dot { margin: 0 4px; }
.btn-remove {
  background: transparent;
  border: none;
  color: #f56c6c;
  font-size: 12px;
  cursor: pointer;
  padding: 2px 6px;
}
.btn-remove:hover { background: #fef0f0; border-radius: 4px; }

.card-body { min-height: 80px; }
.price-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 8px;
}
.price {
  font-size: 26px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.change-pct {
  font-size: 14px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.up { color: #ef232a; }
.down { color: #14b143; }

.info-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  font-size: 12px;
  color: #666;
  padding-top: 8px;
  border-top: 1px dashed #eee;
}
.fund-row { grid-template-columns: repeat(2, 1fr); }
.info-item { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.info-label { color: #aaa; font-size: 11px; }

.card-notes {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #eee;
  font-size: 12px;
  color: #888;
}

.quote-error {
  color: #e6a23c;
  font-size: 13px;
  text-align: center;
  padding: 16px 0;
}
.quote-no-intraday {
  text-align: center;
  padding: 20px 0;
  color: #999;
}
.no-intra-icon { font-size: 24px; margin-bottom: 6px; }
.no-intra-hint { font-size: 12px; color: #bbb; margin-top: 4px; }

.quote-nav {
  padding: 12px 0;
}
.nav-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 6px;
}
.nav-label {
  font-size: 12px;
  color: #999;
}
.nav-price {
  font-size: 24px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.nav-change {
  font-size: 14px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.nav-date {
  font-size: 11px;
  color: #bbb;
  text-align: right;
  margin-top: 4px;
}
.quote-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #999;
  font-size: 12px;
  padding: 16px 0;
  justify-content: center;
}
.mini-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid #e4e7ed;
  border-top-color: #409eff;
  border-radius: 50%;
  animation: spin .8s linear infinite;
}

.page-loading, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: #999;
  gap: 12px;
}
.empty-icon { font-size: 56px; opacity: .4; }
.empty-title { font-size: 16px; color: #666; font-weight: 500; }
.empty-desc { font-size: 13px; color: #aaa; margin: 4px 0 8px; }
.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e4e7ed;
  border-top-color: #409eff;
  border-radius: 50%;
  animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
