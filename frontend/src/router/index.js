import { createRouter, createWebHistory } from 'vue-router'
import { getToken, isAdmin } from '../api'
import Dashboard from '../views/Dashboard.vue'
import StockPool from '../views/StockPool.vue'
import StockDetail from '../views/StockDetail.vue'
import TradeRecords from '../views/TradeRecords.vue'
import IndexValuation from '../views/IndexValuation.vue'
import Portfolio from '../views/Portfolio.vue'
import Admin from '../views/Admin.vue'
import Login from '../views/Login.vue'
import AdminLogin from '../views/AdminLogin.vue'

const routes = [
  { path: '/login',           name: 'login',           component: Login,           meta: { title: '登录', public: true } },
  { path: '/anyuci/login',    name: 'admin-login',     component: AdminLogin,      meta: { title: '后台登录', public: true, hidden: true } },
  { path: '/',                name: 'dashboard',       component: Dashboard,       meta: { title: '大盘行情' } },
  { path: '/stocks',          name: 'stocks',          component: StockPool,       meta: { title: '自选', requiresAuth: true } },
  { path: '/stocks/:id',      name: 'stock-detail',    component: StockDetail,     meta: { title: '股票详情', requiresAuth: true } },
  { path: '/trades',          name: 'trades',          component: TradeRecords,    meta: { title: '交易记录', requiresAuth: true } },
  { path: '/index-valuation', name: 'index-valuation', component: IndexValuation,  meta: { title: '指数估值', requiresAuth: true } },
  { path: '/portfolio',       name: 'portfolio',       component: Portfolio,       meta: { title: '我的持仓', requiresAuth: true } },
  { path: '/anyuci',          name: 'admin',           component: Admin,           meta: { title: '后台', requiresAuth: true, requiresAdmin: true, hidden: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 全局守卫：受保护路由必须先登录
router.beforeEach((to, from, next) => {
  const loggedIn = !!getToken()
  if (to.meta.public) {
    // 已登录再访问登录页：前台登录页→首页；后台登录页→后台（仅 admin）
    if (to.path === '/login' && loggedIn) return next('/')
    if (to.path === '/anyuci/login' && loggedIn && isAdmin()) return next('/anyuci')
    return next()
  }
  // 后台路由：未登录→后台专属登录页；已登录但非 admin→踢回前台
  if (to.meta.requiresAdmin) {
    if (!loggedIn) return next({ path: '/anyuci/login', query: { redirect: to.fullPath } })
    if (!isAdmin()) return next('/')
    return next()
  }
  if (to.meta.requiresAuth && !loggedIn) {
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }
  next()
})

export default router
