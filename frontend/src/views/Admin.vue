<template>
  <div class="admin-page">
    <!-- 头部 -->
    <el-card class="header-card" shadow="never">
      <div class="header-row">
        <div>
          <h2 style="margin: 0 0 4px 0;">👥 用户管理</h2>
          <div style="color: #909399; font-size: 13px;">
            后台管理控制台 · 仅管理员可访问
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <span v-if="me" style="color:#606266;font-size:13px;">
            当前：<strong>{{ me.username }}</strong>
            <el-tag size="small" :type="me.role==='admin'?'danger':'info'" style="margin-left:4px;">
              {{ me.role==='admin'?'管理员':'普通用户' }}
            </el-tag>
          </span>
          <el-button @click="openChangePwdDialog">🔑 修改密码</el-button>
          <el-button @click="loadUsers" :loading="loading">🔄 刷新</el-button>
          <el-button type="primary" @click="openCreateDialog">+ 新增用户</el-button>
          <el-button @click="onLogout">退出登录</el-button>
        </div>
      </div>
    </el-card>

    <!-- 筛选 -->
    <el-card class="filter-card" shadow="never">
      <el-form :inline="true" :model="filter" @submit.prevent>
        <el-form-item label="用户名">
          <el-input
            v-model="filter.q"
            placeholder="模糊搜索"
            clearable
            style="width: 200px;"
            @keyup.enter="loadUsers"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="filter.role" clearable placeholder="全部" style="width: 120px;">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filter.is_active" clearable placeholder="全部" style="width: 120px;">
            <el-option label="启用" :value="1" />
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadUsers">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表 -->
    <el-card shadow="never">
      <el-table
        :data="users"
        v-loading="loading"
        stripe
        style="width: 100%;"
        empty-text="暂无用户"
      >
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" min-width="160">
          <template #default="{ row }">
            <strong>{{ row.username }}</strong>
            <el-tag v-if="row.id === me?.id" size="small" type="success" style="margin-left: 8px;">我</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="110">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'warning'" size="small">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后登录" min-width="170">
          <template #default="{ row }">
            <span style="color: #606266; font-size: 13px;">
              {{ row.last_login_at ? formatDate(row.last_login_at) : '从未登录' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="170">
          <template #default="{ row }">
            <span style="color: #909399; font-size: 13px;">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button
              size="small"
              link
              :type="row.is_active ? 'warning' : 'success'"
              @click="toggleActive(row)"
            >
              {{ row.is_active ? '停用' : '启用' }}
            </el-button>
            <el-button
              size="small"
              link
              type="primary"
              @click="openResetPwdDialog(row)"
            >重置密码</el-button>
            <el-button
              size="small"
              link
              type="danger"
              :disabled="row.id === me?.id"
              @click="onDelete(row)"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增 / 编辑用户弹窗 -->
    <el-dialog
      v-model="formDialog.visible"
      :title="formDialog.isEdit ? `编辑用户：${formDialog.form.username}` : '新增用户'"
      width="480px"
      @closed="onFormClosed"
    >
      <el-form :model="formDialog.form" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="formDialog.form.username"
            placeholder="2-32 个字符"
            :disabled="formDialog.isEdit"
          />
        </el-form-item>
        <el-form-item v-if="!formDialog.isEdit" label="密码" prop="password">
          <el-input
            v-model="formDialog.form.password"
            type="password"
            show-password
            placeholder="至少 6 位"
          />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-radio-group v-model="formDialog.form.role">
            <el-radio value="user">普通用户</el-radio>
            <el-radio value="admin">管理员</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch
            v-model="formDialog.form.is_active"
            active-text="启用"
            inactive-text="停用"
            inline-prompt
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="formDialog.loading" @click="onSubmitForm">确定</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码弹窗 -->
    <el-dialog v-model="resetPwdDialog.visible" title="重置密码" width="420px">
      <el-form :model="resetPwdDialog" :rules="resetPwdRules" ref="resetPwdRef" label-width="100px">
        <el-form-item label="用户">
          <el-tag>{{ resetPwdDialog.username }}</el-tag>
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="resetPwdDialog.newPassword" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetPwdDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="resetPwdDialog.loading" @click="onResetPwd">确定</el-button>
      </template>
    </el-dialog>

    <!-- 改自己密码弹窗 -->
    <el-dialog v-model="changePwdDialog.visible" title="修改我的密码" width="420px">
      <el-form :model="changePwdDialog" :rules="changePwdRules" ref="changePwdRef" label-width="100px">
        <el-form-item label="原密码" prop="oldPassword">
          <el-input v-model="changePwdDialog.oldPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="changePwdDialog.newPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input v-model="changePwdDialog.confirmPassword" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="changePwdDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="changePwdDialog.loading" @click="onChangePwd">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listUsers, createUser, updateUser, deleteUser,
  getMe, changeMyPassword, logoutApi, setToken,
} from '../api'

const router = useRouter()
const me = ref(null)
const users = ref([])
const loading = ref(false)

async function onLogout() {
  try { await logoutApi() } catch {}
  setToken(null)
  router.replace('/anyuci/login')
}

const filter = reactive({ q: '', role: '', is_active: '' })

// ── 表单弹窗 ──
const formRef = ref()
const formDialog = reactive({
  visible: false,
  isEdit: false,
  loading: false,
  form: { id: null, username: '', password: '', role: 'user', is_active: true },
})
const formRules = {
  username: [{ required: true, min: 2, max: 32, message: '2-32 个字符', trigger: 'blur' }],
  password: [{ required: true, min: 6, max: 64, message: '至少 6 位', trigger: 'blur' }],
  role:     [{ required: true, message: '请选择角色', trigger: 'change' }],
}

// ── 重置密码弹窗 ──
const resetPwdRef = ref()
const resetPwdDialog = reactive({ visible: false, loading: false, userId: null, username: '', newPassword: '' })
const resetPwdRules = {
  newPassword: [{ required: true, min: 6, max: 64, message: '至少 6 位', trigger: 'blur' }],
}

// ── 改自己密码弹窗 ──
const changePwdRef = ref()
const changePwdDialog = reactive({ visible: false, loading: false, oldPassword: '', newPassword: '', confirmPassword: '' })
const changePwdRules = {
  oldPassword:     [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword:     [{ required: true, min: 6, message: '至少 6 位', trigger: 'blur' }],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: (rule, value, cb) => value === changePwdDialog.newPassword ? cb() : cb(new Error('两次密码不一致')), trigger: 'blur' },
  ],
}

// ── 加载用户列表 ──
async function loadUsers() {
  loading.value = true
  try {
    const params = {}
    if (filter.q) params.q = filter.q
    if (filter.role) params.role = filter.role
    if (filter.is_active !== '' && filter.is_active !== null) params.is_active = filter.is_active
    const resp = await listUsers(params)
    const list = Array.isArray(resp.data) ? resp.data : (resp.data?.users || resp.data?.value || [])
    users.value = list.filter(u => u.username !== '__dev_bootstrap__')
  } catch (e) {
    ElMessage.error(`加载失败：${e.response?.data?.detail || e.message}`)
  } finally {
    loading.value = false
  }
}

function resetFilter() {
  filter.q = ''
  filter.role = ''
  filter.is_active = ''
  loadUsers()
}

// ── 新增 ──
function openCreateDialog() {
  formDialog.isEdit = false
  formDialog.form = { id: null, username: '', password: '', role: 'user', is_active: true }
  formDialog.visible = true
}

// ── 编辑 ──
function openEditDialog(row) {
  formDialog.isEdit = true
  formDialog.form = { id: row.id, username: row.username, password: '', role: row.role, is_active: !!row.is_active }
  formDialog.visible = true
}

function onFormClosed() {
  formRef.value?.clearValidate()
}

async function onSubmitForm() {
  try { await formRef.value.validate() } catch { return }
  formDialog.loading = true
  try {
    if (formDialog.isEdit) {
      const payload = { role: formDialog.form.role, is_active: formDialog.form.is_active }
      await updateUser(formDialog.form.id, payload)
      ElMessage.success('已更新')
    } else {
      await createUser({
        username: formDialog.form.username,
        password: formDialog.form.password,
        role: formDialog.form.role,
        is_active: formDialog.form.is_active,
      })
      ElMessage.success('已创建')
    }
    formDialog.visible = false
    loadUsers()
  } catch (e) {
    ElMessage.error(`操作失败：${e.response?.data?.detail || e.message}`)
  } finally {
    formDialog.loading = false
  }
}

// ── 切换启用/停用 ──
async function toggleActive(row) {
  const action = row.is_active ? '停用' : '启用'
  try {
    await ElMessageBox.confirm(`确认${action}用户「${row.username}」？`, '提示', { type: 'warning' })
  } catch { return }
  try {
    await updateUser(row.id, { is_active: !row.is_active })
    ElMessage.success(`已${action}`)
    loadUsers()
  } catch (e) {
    ElMessage.error(`失败：${e.response?.data?.detail || e.message}`)
  }
}

// ── 重置密码 ──
function openResetPwdDialog(row) {
  resetPwdDialog.userId = row.id
  resetPwdDialog.username = row.username
  resetPwdDialog.newPassword = ''
  resetPwdDialog.visible = true
}
async function onResetPwd() {
  try { await resetPwdRef.value.validate() } catch { return }
  resetPwdDialog.loading = true
  try {
    await updateUser(resetPwdDialog.userId, { password: resetPwdDialog.newPassword })
    ElMessage.success(`已重置「${resetPwdDialog.username}」的密码`)
    resetPwdDialog.visible = false
  } catch (e) {
    ElMessage.error(`失败：${e.response?.data?.detail || e.message}`)
  } finally {
    resetPwdDialog.loading = false
  }
}

// ── 改自己密码 ──
function openChangePwdDialog() {
  changePwdDialog.oldPassword = ''
  changePwdDialog.newPassword = ''
  changePwdDialog.confirmPassword = ''
  changePwdDialog.visible = true
}
async function onChangePwd() {
  try { await changePwdRef.value.validate() } catch { return }
  changePwdDialog.loading = true
  try {
    await changeMyPassword(changePwdDialog.oldPassword, changePwdDialog.newPassword)
    ElMessage.success('密码已修改')
    changePwdDialog.visible = false
  } catch (e) {
    ElMessage.error(`失败：${e.response?.data?.detail || e.message}`)
  } finally {
    changePwdDialog.loading = false
  }
}

// ── 删除 ──
async function onDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除用户「${row.username}」？此操作不可恢复。`,
      '危险操作', { type: 'error', confirmButtonText: '确认删除', cancelButtonText: '取消' }
    )
  } catch { return }
  try {
    await deleteUser(row.id)
    ElMessage.success('已删除')
    loadUsers()
  } catch (e) {
    ElMessage.error(`失败：${e.response?.data?.detail || e.message}`)
  }
}

// ── 工具 ──
function formatDate(s) {
  if (!s) return '-'
  const d = new Date(s)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

onMounted(async () => {
  try {
    const r = await getMe()
    me.value = r.data
  } catch (e) {
    if (e.response?.status === 401) { router.replace('/anyuci/login'); return }
  }
  loadUsers()
})
</script>

<style scoped>
.admin-page { max-width: 1280px; margin: 0 auto; }
.header-card { margin-bottom: 16px; }
.header-row { display: flex; justify-content: space-between; align-items: center; }
.filter-card { margin-bottom: 16px; }
:deep(.el-card) { border-radius: 8px; }
:deep(.el-card__body) { padding: 16px 20px; }
</style>
