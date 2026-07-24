import { createRouter, createWebHistory } from 'vue-router'
import { getToken, isAdmin } from '../api'

// 路由懒加载：每个页面独立 chunk，访问时才加载
const Dashboard    = () => import(/* webpackChunkName: "dashboard" */ '../views/Dashboard.vue')
const StockPool   = () => import(/* webpackChunkName: "stock-pool" */ '../views/StockPool.vue')
const StockDetail = () => import(/* webpackChunkName: "stock-detail" */ '../views/StockDetail.vue')
const TradeRecords= () => import(/* webpackChunkName: "trade-records" */ '../views/TradeRecords.vue')
const Portfolio   = () => import(/* webpackChunkName: "portfolio" */ '../views/Portfolio.vue')
const MyReturns  = () => import(/* webpackChunkName: "my-returns" */ '../views/MyReturns.vue')
const Admin      = () => import(/* webpackChunkName: "admin" */ '../views/Admin.vue')
const Login      = () => import(/* webpackChunkName: "login" */ '../views/Login.vue')
const AdminLogin = () => import(/* webpackChunkName: "admin-login" */ '../views/AdminLogin.vue')

const routes = [
  { path: '/login',           name: 'login',           component: Login,           meta: { title: '登录', public: true } },
  { path: '/anyuci/login',    name: 'admin-login',     component: AdminLogin,      meta: { title: '后台登录', public: true, hidden: true } },
  { path: '/',                name: 'dashboard',       component: Dashboard,       meta: { title: '大盘行情' } },
  { path: '/stocks',          name: 'stocks',          component: StockPool,       meta: { title: '自选', requiresAuth: true } },
  { path: '/stocks/:id',      name: 'stock-detail',    component: StockDetail,     meta: { title: '股票详情', requiresAuth: true } },
  { path: '/trades',          name: 'trades',          component: TradeRecords,    meta: { title: '交易记录', requiresAuth: true } },
  { path: '/portfolio',       name: 'portfolio',       component: Portfolio,       meta: { title: '我的持仓', requiresAuth: true } },
  { path: '/my-returns',     name: 'my-returns',     component: MyReturns,     meta: { title: '我的收益', requiresAuth: true } },
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
