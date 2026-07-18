# 个人交易分析系统

一个基于 Vue3 + FastAPI + SQLite 的股票/基金个人交易分析系统，支持用户认证与后台管理。

## 功能特性

### 交易分析
- 📊 **持仓汇总**：实时展示当前持仓的市值、成本、盈亏等信息
- 💼 **我的持仓**：仓位概览、标的卡片、类型（A/B/C）覆盖、占比可视化
- 💰 **清仓汇总**：记录已清仓品种的收益、持有天数、收益率等
- 📝 **交易记录**：支持单笔/批量新增交易（≤500 笔），CSV/TSV 快速导入，FIFO 成本计算
- 📈 **收益曲线**：可视化展示资产历史波动，含成本线对比
- 💵 **分红管理**：独立记录分红历史（与交易记录完全分离），支持分红曲线查看
- 📅 **月度交易图**：年度交易分布点状图

### 行情与估值
- 📉 **大盘行情**：大盘 K 线图（30/60/120/250 日切换、dataZoom）
- 🎯 **信号中心**：指数估值参考、持仓信号、趋势信号（已集成至自选页「关联指数」tab）
- 📊 **指数估值**：中证指数官方 PE/PB 历史分位（6 指数覆盖）

### 用户与权限
- 🔐 **用户认证**：JWT + PBKDF2 密码哈希，全站登录鉴权（大盘公开，其余需登录）
- 👥 **后台管理**：独立管理员后台（`/anyuci`），用户增删改查、改密、启停用
- 🛡️ **权限隔离**：普通账户无法访问后台；前端路由守卫 + 后端 `require_admin` 双层防护
- ⚙️ **独立后台登录页**：`/anyuci/login`，深色管理控制台主题，登录时校验管理员角色

## 技术栈

### 后端
- Python 3.11+
- FastAPI
- SQLAlchemy
- SQLite
- Uvicorn
- python-jose / passlib（JWT + 密码哈希）

### 前端
- Vue 3
- Element Plus
- ECharts
- Vue Router（含路由守卫）
- Vite

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/songmumu/stocks.git
cd stocks/trading-system
```

### 2. 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务（端口 8001）
uvicorn app.main:app --reload --port 8001
```

首次启动会自动创建默认管理员账户：**admin / admin123**（请登录后立即修改密码）。

### 3. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 4. 访问应用

- 前台：`http://localhost:5173`
- 前台登录：`http://localhost:5173/login`
- 后台管理登录：`http://localhost:5173/anyuci/login`（仅管理员）

## 项目结构

```
trading-system/
├── backend/                      # 后端代码
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── models.py           # 数据库模型（含 User 表）
│   │   ├── schemas.py          # Pydantic 模型
│   │   ├── auth.py             # JWT + 密码哈希 + 鉴权依赖
│   │   ├── routers/           # API 路由
│   │   │   ├── auth.py        # 登录/登出/改密/me
│   │   │   ├── users.py       # 用户管理（admin only）
│   │   │   ├── portfolio.py   # 我的持仓
│   │   │   ├── market.py      # 行情
│   │   │   ├── watchlist_signals.py  # 信号
│   │   │   └── ...
│   │   └── services/          # 业务逻辑（行情/净值/中证指数）
│   └── requirements.txt
├── frontend/                     # 前端代码
│   ├── src/
│   │   ├── views/              # 页面组件
│   │   │   ├── Dashboard.vue       # 大盘（公开）
│   │   │   ├── StockPool.vue       # 自选（基金/ETF/关联指数）
│   │   │   ├── TradeRecords.vue    # 交易记录
│   │   │   ├── Portfolio.vue       # 我的持仓
│   │   │   ├── IndexValuation.vue  # 指数估值
│   │   │   ├── Login.vue           # 前台登录
│   │   │   ├── AdminLogin.vue      # 后台管理登录
│   │   │   └── Admin.vue           # 后台用户管理
│   │   ├── api/               # API 接口 + token/role 存取
│   │   ├── router/            # 路由 + 守卫
│   │   └── App.vue
│   └── package.json
├── docs/
│   └── data-sources.md         # 数据源说明
└── README.md
```

## 权限与路由说明

| 路由 | 访问权限 | 说明 |
|------|---------|------|
| `/` | 公开 | 大盘行情 |
| `/login` | 公开 | 前台用户登录 |
| `/anyuci/login` | 公开 | 后台管理登录（校验 admin 角色） |
| `/stocks` `/trades` `/portfolio` `/index-valuation` | 需登录 | 未登录点击跳前台登录页 |
| `/anyuci` | 仅管理员 | 未登录跳后台登录页；已登录非 admin 踢回首页 |

**双层权限防护**：
- 前端：路由守卫（`requiresAuth` / `requiresAdmin` + `isAdmin`）+ 后台登录页角色校验
- 后端：用户管理接口 `/api/users` 全部 `Depends(require_admin)`，非 admin 返回 403

## 数据源

- 实时行情：腾讯股票 API（qt.gtimg.cn）
- 基金净值：天天基金 API（fundmobapi.eastmoney.com）
- 指数估值：中证指数官方 API（www.csindex.com.cn，提供 10 年历史 PE/PB）

详见 [`docs/data-sources.md`](docs/data-sources.md)。

## 注意事项

1. 本项目为个人投资辅助工具，不构成投资建议
2. 后端默认端口 **8001**，前端 Vite 代理已指向该端口
3. 首次使用前请确保后端服务已启动
4. 数据库文件 `trading.db` 不会被提交到 Git，请自行备份
5. 生产部署请务必修改 `auth.py` 中的 `SECRET_KEY` 及默认管理员密码

## License

MIT
