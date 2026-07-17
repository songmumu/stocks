<template>
  <div id="app-root">
    <el-container style="min-height: 100vh">
      <el-header style="background: #1a1a2e; color: #fff; display: flex; align-items: center; padding: 0 24px; height: 56px; gap: 12px;">
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
          <el-menu-item index="/signals">📡 信号</el-menu-item>
          <el-menu-item index="/index-valuation">📊 指数估值</el-menu-item>
        </el-menu>
      </el-header>
      <el-main style="background: #f5f6fa; padding: 20px;">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

function onMenuSelect(index) {
  router.push(index)
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
.el-menu--horizontal .el-menu-item { color: rgba(255,255,255,.75) !important; }
.el-menu--horizontal .el-menu-item.is-active { color: #fff !important; border-bottom-color: #409eff !important; }
.el-menu--horizontal .el-menu-item:hover { color: #fff !important; background: rgba(255,255,255,.08) !important; }
</style>
