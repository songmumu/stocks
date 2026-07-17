# 工作记录 2026-07-15 21:08

## 任务：修复 StockDetail.vue 进入页面 K线图不显示

### 现象
- 江波龙(301308) 个股详情页进入时 K线区空白
- 点击 30日/60日/120日/250日 切换后 K线立即显示

### 根因
`v-if="loading"` 与 `v-else-if="stock"` 互斥的时序问题：

```js
async function loadStock() {
  const list = await getWatchlist()
  stock.value = list.find(...)              // ← stock 已设
  // 此时 v-if=loading 还是 true，v-else-if 不渲染！
  await loadQuote()                          // 网络 100ms
  await loadKline() {                        // 网络 200ms
    renderKline(bars)                        // klineRef.value === null（容器未渲染）
    if (!klineRef.value) return              // ← 直接 return
  }
  await loadTrades()
  // finally 里 loading=false → 此时 v-else-if 才渲染，但 renderKline 已 return
  loading.value = false
}
```

切换日期时 `loadKline` 重跑，详情区早已存在 → klineRef 有值 → init 成功。

### 修复
**核心**：让 `loading=false` 在 `loadKline` 之前触发，并 await nextTick 等 DOM 渲染。

```js
async function loadStock() {
  ...
  stock.value = list.find(...)
  loading.value = false      // ← 提前关闭 loading，让 v-else-if 渲染
  await nextTick()           // ← 等 v-else-if 渲染完，klineRef 绑定
  await loadQuote()
  await loadKline()         // 此时 klineRef 已有值
  await loadTrades()
  // 移除原来的 finally { loading.value = false }
}
```

`loadKline` 内也加双保险（处理切日期时的边缘情况）：
```js
await nextTick()                                   // 等 DOM
requestAnimationFrame(() => renderKline(bars))     // 再等一帧（v-loading 蒙层布局）
```

### 验证
- Vite build 成功（22.86s, exit 0）
- Dev server HMR 自动热更新
- 用户刷新 http://localhost:5173/stock/{id} 即可看到 K线

### 教训
- **v-if / v-else-if 切换要等 nextTick** 才能拿到 ref
- **数据流要先关 loading 再 await 数据加载**，否则容器永远不会渲染
- `await nextTick()` 在 `loadKline` 内部不够，因为 nextTick 只等当前响应式更新完成，v-else-if 的渲染被 loading 阻塞
