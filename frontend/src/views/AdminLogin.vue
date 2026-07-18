<template>
  <div class="admin-login-wrap">
    <div class="admin-login-card">
      <div class="brand">
        <div class="logo">⚙️</div>
        <h2>后台管理控制台</h2>
        <p class="sub">Administration Console</p>
      </div>

      <div class="warn-banner">
        🔒 本页仅限<strong>管理员</strong>登录 · 普通账户无权访问
      </div>

      <el-form :model="form" :rules="rules" ref="formRef" @submit.prevent>
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="管理员账号"
            size="large"
            @keyup.enter="onLogin"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="管理员密码"
            size="large"
            show-password
            @keyup.enter="onLogin"
          />
        </el-form-item>
        <el-button
          class="login-btn"
          size="large"
          style="width: 100%;"
          :loading="loading"
          @click="onLogin"
        >进入后台</el-button>
      </el-form>

      <div class="hint">
        ⚠️ 此为受限区域，所有操作均被记录
        <router-link to="/" class="back-link">← 返回前台</router-link>
      </div>
    </div>
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
  username: [{ required: true, message: '请输入管理员账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入管理员密码', trigger: 'blur' }],
}

async function onLogin() {
  try { await formRef.value.validate() } catch { return }
  loading.value = true
  try {
    const resp = await login(form.username, form.password)
    const token = resp.data?.access_token
    const role  = resp.data?.user?.role || ''
    if (!token) throw new Error('未返回 token')
    // 仅管理员可登录后台
    if (role !== 'admin') {
      ElMessage.error('该账户非管理员，无权登录后台')
      return
    }
    setToken(token)
    setUsername(resp.data?.user?.username || form.username)
    setRole(role)
    ElMessage.success('管理员登录成功')
    const redirect = route.query.redirect || '/anyuci'
    router.replace(redirect)
  } catch (e) {
    const detail = e.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : '登录失败，请检查账号或密码')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.admin-login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at 30% 20%, #3a1414 0%, #1a0d0d 45%, #0d0d12 100%);
}
.admin-login-card {
  width: 400px;
  border-radius: 14px;
  padding: 36px 32px 28px;
  background: #1c1c24;
  border: 1px solid #4a2b2b;
  box-shadow: 0 20px 60px rgba(0,0,0,.5), 0 0 0 1px rgba(212,175,55,.08);
}
.brand { text-align: center; margin-bottom: 20px; }
.logo { font-size: 46px; filter: drop-shadow(0 0 12px rgba(212,175,55,.4)); }
.brand h2 { margin: 10px 0 2px; font-size: 22px; color: #f0d98c; letter-spacing: 1px; }
.sub { color: #8a7a5a; font-size: 12px; margin: 0; letter-spacing: 2px; text-transform: uppercase; }
.warn-banner {
  background: rgba(220, 80, 80, .12);
  border: 1px solid rgba(220, 80, 80, .3);
  color: #e79a9a;
  font-size: 13px;
  text-align: center;
  padding: 8px 10px;
  border-radius: 8px;
  margin-bottom: 20px;
}
.warn-banner strong { color: #ffb4b4; }
.login-btn {
  background: linear-gradient(135deg, #c0392b 0%, #a01e14 100%);
  border: none;
  color: #fff;
  font-weight: 600;
  letter-spacing: 2px;
}
.login-btn:hover { background: linear-gradient(135deg, #d0432f 0%, #b02419 100%); }
.hint {
  margin-top: 18px;
  text-align: center;
  color: #6a6a72;
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.back-link { color: #8a7a5a; text-decoration: none; }
.back-link:hover { color: #f0d98c; }
/* 覆盖 element 深色输入框 */
.admin-login-card :deep(.el-input__wrapper) {
  background: #26262f;
  box-shadow: 0 0 0 1px #3a3a44 inset;
}
.admin-login-card :deep(.el-input__inner) { color: #e8e8ec; }
.admin-login-card :deep(.el-input__inner::placeholder) { color: #6a6a72; }
</style>
