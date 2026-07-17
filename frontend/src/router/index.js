import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import StockPool from '../views/StockPool.vue'
import StockDetail from '../views/StockDetail.vue'
import TradeRecords from '../views/TradeRecords.vue'
import Signals from '../views/Signals.vue'
import IndexValuation from '../views/IndexValuation.vue'

const routes = [
  { path: '/', name: 'dashboard', component: Dashboard, meta: { title: '大盘行情' } },
  { path: '/stocks', name: 'stocks', component: StockPool, meta: { title: '自选' } },
  { path: '/stocks/:id', name: 'stock-detail', component: StockDetail, meta: { title: '股票详情' } },
  { path: '/trades', name: 'trades', component: TradeRecords, meta: { title: '交易记录' } },
  { path: '/signals', name: 'signals', component: Signals, meta: { title: '信号' } },
  { path: '/index-valuation', name: 'index-valuation', component: IndexValuation, meta: { title: '指数估值' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
