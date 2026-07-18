# 更新日志

## [0.3.0] - 2026-07-18

本次更新在 v0.2 交易分析核心功能之上，新增**用户认证体系**、**后台管理**、**我的持仓**模块，并完善了行情与信号能力。

### 🔐 新增：用户认证与权限体系

- **JWT 鉴权**：新增 `backend/app/auth.py`，实现 PBKDF2 密码哈希、JWT（HS256，24h 过期）创建/解码、`get_current_user` / `require_admin` 依赖。
- **认证接口** `backend/app/routers/auth.py`：登录、登出、获取当前用户（`/me`）、修改密码。
- **用户管理接口** `backend/app/routers/users.py`：管理员专用 CRUD（创建/列表/改密/启停用/删除），含「最后一个管理员保护」逻辑，全部接口 `Depends(require_admin)`。
- **User 数据表**：`models.py` 新增 `User`（id、username、password_hash、role、is_active 等），启动时自动创建默认管理员 **admin / admin123**。
- **全站登录鉴权**：大盘（`/`）公开，其余页面（自选/交易/持仓/估值/后台）需登录。
- **前端 token/role 存取**：`api/index.js` 新增 `getToken/setToken`、`getUsername/setUsername`、`getRole/setRole`、`isAdmin`。

### 👥 新增：后台管理

- **Admin.vue**：用户管理后台（列表 + 筛选 + 增删改查 + 改密 + 角色/状态标签）。
- **AdminLogin.vue**：**独立后台登录页**，深色红金「管理控制台」主题，与前台登录页视觉完全区分；登录时校验管理员角色，非 admin 直接拒绝并不写 token。
- **后台路由** `/anyuci`（隐藏，`requiresAdmin`），后台登录 `/anyuci/login`。
- **权限隔离**：
  - 未登录访问 `/anyuci` → 跳后台专属登录页 `/anyuci/login`
  - 已登录非 admin → 踢回前台首页
  - 前端路由守卫（`requiresAuth` / `requiresAdmin` + `isAdmin`）+ 后端 `require_admin` 双层防护

### 💼 新增：我的持仓（Portfolio）

- **Portfolio.vue** + `backend/app/routers/portfolio.py`：仓位概览、标的卡片、类型（A/B/C）覆盖（localStorage 持久化 + 后端 `index_type` 优先）、占比条可视化、浮盈符号修正。

### 📈 行情与信号增强

- **大盘 K 线图**：Dashboard 新增大盘 K 线（30/60/120/250 日切换、dataZoom、红绿柱）。
- **信号模块迁移**：删除独立 `Signals.vue`，「持仓信号」迁移至 `StockPool.vue` 第三个 tab（更名「关联指数」），减少页面跳转。
- **中证指数 PE 集成**：`watchlist_signals.py` 集成中证指数官方 API，6 指数 PE/PB 历史分位覆盖。
- **场外基金净值修复**：`eastmoney_service.py` 修复场外基金净值取值（K 线最后一条 close，前端 4 位小数）。

### 🐛 修复

- **导航栏登录态**：菜单栏改为始终全显示，未登录点击受保护菜单跳登录页（由路由守卫拦截），修正此前 `el-menu` + `<template v-if>` 导致的条件渲染失效问题。
- **watchlistSignals 赋值 bug**：后端返回 `{watchlist_signals, index_signals}` 对象，前端修正为 `data.watchlist_signals || []`，解决 `.filter is not a function`。
- **导航栏发白**：`.el-menu-item` 强制 `background: transparent !important`。
- **编码修复**：中文乱码 + URL 编码问题修复。

### 🧹 工程

- **.gitignore**：新增排除开发探针（`probe_*.py`）、迁移脚本（`_migrate_*.py`）、本地设计蓝图 HTML。
- **数据源文档**：新增 `docs/data-sources.md`。

### ⚠️ 已知限制

- 中证指数覆盖仅 6 个（93xxxx 系列 CSI 搜索 API 待探索）。
- 港股指数（HSTECH）无公开 PE/PB 数据源。
- 前端 build 有 chunk > 500kB 警告（来自 @vueuse/core，不影响运行）。

---

## [0.2.0] - 2026-07-16

- 交易分析核心：自选股/基金 CRUD、行情/K 线、交易记录（FIFO 成本）、清仓汇总、分红管理、月度交易图、收益曲线。
- 三层估值体系：腾讯实时 PE/PB + 天天基金 NAV + 中证指数历史分位。
- 数据源确定：腾讯股票 API / 天天基金 API / 中证指数官方 API。
- 后端端口迁移至 8001。
