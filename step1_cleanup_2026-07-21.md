# Step 1 完成：PE 体系删除 & 纯回撤策略上线

**时间**: 2026-07-21 19:50 ~ 20:30 GMT+8

## 执行结果

### ✅ 后端

| 操作 | 文件/内容 |
|------|---------|
| 删除 | `valuation.py` `watchlist_signals.py` `holding_percentiles.py` `csi_service.py` `valuation_service.py` |
| 重写 | `portfolio.py` — `calc_action()` 彻底重写为纯回撤策略，新增 5 档类型体系 |
| 清理 | `main.py` — 删除 3 个路由注册 |
| 清理 | `models.py` — 删除 `IndexValuationSnapshot` / `HoldingPercentile` 表 |
| 清理 | `schemas.py` — 删除 4 个 Pydantic 模型 |
| 修复 | `stocks.py` — 删除 valuation 残留导入，简化 `available-indices` |

### ✅ 前端

| 操作 | 文件/内容 |
|------|---------|
| 重写 | `Portfolio.vue` — 删除 PE 分位条，更新为 5 类（A大盘宽基/B科创创业/C科技赛道/D恒生科技/E红利），重写规则速查 5 卡片 |
| 重写 | `StockPool.vue` — 删除「关联指数」tab 及所有相关逻辑 |
| 清理 | `App.vue` — 删除「指数估值」导航菜单 |
| 清理 | `router/index.js` — 删除 `/index-valuation` 路由 |
| 清理 | `api/index.js` — 删除 5 个估值 API 函数 |

### 验证
- 后端 `from app.main import app` ✅
- 前端 `npm run build` → built in 36.59s ✅

---

## 新策略核心参数（后端 `portfolio.py` RULES 字典）

| 类型 | 名称 | 止盈回撤1 | 止盈回撤2 | 硬止损 | 波段买入回落 | 长线定投触发 |
|------|------|---------|---------|--------|-----------|-----------|
| A | 大盘宽基ETF | 6% → 减40% | 12% → 清仓 | -6% | 6%~10% | ≥14% |
| B | 科创50/创业板ETF | 6.5% → 减40% | 13% → 清仓 | -6% | 7%~11% | ≥16% |
| C | 科技赛道ETF | 7.5% → 减40% | 15% → 清仓 | -7% | 8%~12% | ≥18% |
| D | 恒生科技ETF | 7% → 减40% | 14% → 清仓 | -7% | 8%~13% | ≥20% |
| E | 红利ETF | 5% → 减40% | 10% → 清仓 | -5% | 5%~8% | — |

**前端卡片仅显示**：持有 / 减仓 / 清仓（3种）—— 无买入建议（买入靠人工判断）

## 保留的功能
- 历史最高浮盈追踪（`portfolio_peak_profits` 表）
- 手动类型覆盖（localStorage，A/B/C/D/E 5档）
- 仓位占比类型条（5色）
- 累计收益（含已清仓）双口径

## 待完成（Step 2 & 3）
1. 重启后端进程（8001端口）
2. 前端热更新（5173端口，HMR 应该已自动生效）
3. 验证 Portfolio 页面加载正常
4. 验证 calc_action 输出正确（无 PE 数据时正确触发持有/减仓）
