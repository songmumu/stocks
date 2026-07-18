<template>
  <div id="app-root">
    <el-container style="min-height: 100vh">
      <el-header v-if="route.path !== '/login'" style="background: #1a1a2e; color: #fff; display: flex; align-items: center; padding: 0 24px; height: 56px; gap: 12px;">
        <div style="font-size: 18px; font-weight: 700; letter-spacing: 1px;">📊 交易分析</div>
        <el-menu
          :default-active="route.path"
          mode="horizontal"
          :ellipsis="false"
          style="flex: 1; background: transparent; border: none; margin-left: 24px;"
          @select="onMenuSelect"
        >
          <el-menu-item index="/">📈 大盘</el-menu-item>
          <el-menu-item index="/stocks">自选</el-menu-item>
          <el-menu-item index="/trades">交易记录</el-menu-item>
          <el-menu-item index="/portfolio">💼 我的持仓</el-menu-item>
          <el-menu-item index="/index-valuation">📊 指数估值</el-menu-item>
        </el-menu>
        <div class="nav-right">
          <template v-if="loggedIn">
            <span class="nav-user">👤 {{ username }}</span>
            <el-button size="small" @click="onLogout">退出登录</el-button>
          </template>
          <el-button v-else size="small" type="primary" @click="goLogin">登录</el-button>
        </div>
      </el-header>
      <el-main :style="route.path === '/login' ? 'padding:0' : 'background:#f5f6fa;padding:20px'">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getToken, setToken, logoutApi, getUsername, setUsername, setRole, getMe } from './api'

const route = useRoute()
const router = useRouter()
const loggedIn = ref(!!getToken())
const username = ref(getUsername())

// 已登录但本地无用户名缓存时（如改动前已登录），调 /me 补全
async function syncUserFromMe() {
  if (loggedIn.value && !username.value) {
    try {
      const r = await getMe()
      username.value = r.data?.username || ''
      if (username.value) setUsername(username.value)
      if (r.data?.role) setRole(r.data.role)
    } catch {}
  }
}

onMounted(syncUserFromMe)
// 路由变化时同步登录态（登录/退出后导航栏即时更新）
watch(() => route.path, () => {
  loggedIn.value = !!getToken()
  username.value = getUsername()
})

function onMenuSelect(index) { router.push(index) }
function goLogin() { router.push('/login') }
async function onLogout() {
  try { await logoutApi() } catch {}
  setToken(null)
  router.replace('/login')
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
.el-menu--horizontal .el-menu-item { color: rgba(255,255,255,.75) !important; background: transparent !important; }
.el-menu--horizontal .el-menu-item.is-active { color: #fff !important; border-bottom-color: #409eff !important; background: transparent !important; }
.el-menu--horizontal .el-menu-item:hover { color: #fff !important; background: transparent !important; }
.nav-right { margin-left: auto; display: flex; align-items: center; gap: 12px; }
.nav-user { color: rgba(255,255,255,.85); font-size: 13px; }
</style>
