<template>
  <div class="login-wrap">
    <el-card class="login-card" shadow="always">
      <div class="brand">
        <div class="logo">📊</div>
        <h2>交易分析系统</h2>
        <p class="sub">登录以继续使用</p>
      </div>

      <el-form :model="form" :rules="rules" ref="formRef" @submit.prevent>
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            size="large"
            @keyup.enter="onLogin"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            show-password
            @keyup.enter="onLogin"
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          style="width: 100%;"
          :loading="loading"
          @click="onLogin"
        >登 录</el-button>
      </el-form>

      <div class="hint">账号 admin · 登录后请及时修改密码</div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, setToken, setUsername, setRole } from '../api'

const route = useRoute()
const router = useRouter()

const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function onLogin() {
  try { await formRef.value.validate() } catch { return }
  loading.value = true
  try {
    const resp = await login(form.username, form.password)
    const token = resp.data?.access_token
    if (!token) throw new Error('未返回 token')
    setToken(token)
    setUsername(resp.data?.user?.username || form.username)
    setRole(resp.data?.user?.role || '')
    ElMessage.success('登录成功')
    const redirect = route.query.redirect || '/'
    router.replace(redirect)
  } catch (e) {
    const detail = e.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : '登录失败，请检查用户名或密码')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}
.login-card {
  width: 380px;
  border-radius: 12px;
  padding: 12px 8px;
}
.brand { text-align: center; margin-bottom: 24px; }
.logo { font-size: 44px; }
.brand h2 { margin: 8px 0 4px; font-size: 22px; }
.sub { color: #909399; font-size: 13px; margin: 0; }
.hint { margin-top: 16px; text-align: center; color: #c0c4cc; font-size: 12px; }
</style>
