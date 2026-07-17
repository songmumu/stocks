# 个人交易分析系统

一个基于 Vue3 + FastAPI + SQLite 的股票/基金个人交易分析系统。

## 功能特性

- 📊 **持仓汇总**：实时展示当前持仓的市值、成本、盈亏等信息
- 💰 **清仓汇总**：记录已清仓品种的收益、持有天数、收益率等
- 📝 **交易记录**：支持单笔/批量新增交易，CSV/TSV 快速导入
- 📈 **收益曲线**：可视化展示资产历史波动，含成本线对比
- 🎯 **信号中心**：指数估值参考、持仓信号、趋势信号
- 💵 **分红管理**：独立记录分红历史，支持分红曲线查看
- 📅 **月度交易图**：年度交易分布点状图

## 技术栈

### 后端
- Python 3.11+
- FastAPI
- SQLAlchemy
- SQLite
- Uvicorn

### 前端
- Vue 3
- Element Plus
- ECharts
- Vite

## 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd trading-system
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

# 启动服务
uvicorn app.main:app --reload --port 8001
```

### 3. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 4. 访问应用

打开浏览器访问：`http://localhost:5173`

## 项目结构

```
trading-system/
├── backend/                 # 后端代码
│   ├── app/
│   │   ├── main.py         # FastAPI 入口
│   │   ├── models.py       # 数据库模型
│   │   ├── schemas.py      # Pydantic 模型
│   │   ├── routers/        # API 路由
│   │   └── services/       # 业务逻辑
│   └── requirements.txt
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── views/          # 页面组件
│   │   ├── components/     # 公共组件
│   │   ├── api/            # API 接口
│   │   └── App.vue
│   └── package.json
└── README.md
```

## 数据源

- 实时行情：腾讯股票 API
- 基金净值：天天基金 API
- 指数估值：中证指数官方 API

## 注意事项

1. 本项目为个人投资辅助工具，不构成投资建议
2. 首次使用前请确保后端服务已启动
3. 数据库文件 `trading.db` 不会被提交到 Git，请自行备份

## License

MIT
