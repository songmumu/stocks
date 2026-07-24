<template>
  <div>
    <div class="page-head">
      <h2 style="margin: 0; font-size: 20px; color: #1a1a2e;">📝 交易记录</h2>
      <div style="display:flex;gap:10px;align-items:center;">
        <el-button type="danger" @click="openDivDialog">💰 分红记录</el-button>
        <el-button type="primary" @click="openAdd">+ 新增交易</el-button>
      </div>
    </div>

    <!-- 汇总卡片 -->
    <el-row :gutter="14" class="summary">
      <el-col :span="6">
        <el-card shadow="hover" :body-style="{ padding: '16px' }" class="clickable-card" @click="openMonthlyChart">
          <div class="sum-label">交易笔数</div>
          <div class="sum-value">{{ trades.length }} <span style="font-size:13px;font-weight:400;color:#bbb;">{{ monthlyDialog.visible ? '' : '▸ 查看' }}</span></div>
          <div class="sum-sub">买入 {{ buyCount }} · 卖出 {{ sellCount }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" :body-style="{ padding: '16px' }">
          <div class="sum-label">买入总额</div>
          <div class="sum-value up">¥{{ fmt(buyAmount) }}</div>
          <div class="sum-sub">含手续费</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" :body-style="{ padding: '16px' }" class="clickable-card" @click="openEquityDialog">
          <div class="sum-label">总收益金额 <span style="font-size:11px;color:#bbb;font-weight:400;">▸ 查看收益曲线</span></div>
          <div class="sum-value" :class="totalProfit >= 0 ? 'up' : 'down'">
            {{ totalProfit >= 0 ? '+' : '' }}¥{{ fmt(totalProfit) }}
          </div>
          <div class="sum-sub">卖出金额 · 当前市值</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" :body-style="{ padding: '16px' }" class="clickable-card" @click="openDividendChart">
          <div class="sum-label">分红金额 <span style="font-size:11px;color:#bbb;font-weight:400;">{{ dividendDialog.visible ? '▲ 收起' : '▸ 查看历史曲线' }}</span></div>
          <div class="sum-value" :class="totalDividend > 0 ? 'up' : 'down'">¥{{ fmt(totalDividend) }}</div>
          <div class="sum-sub">累计分红 · 全部品种</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 收益历史波动弹窗 -->
    <el-dialog v-model="equityDialog.visible" title="📈 收益历史波动" width="900px" @opened="onEquityDialogOpened" @closed="onEquityDialogClosed">
      <div v-if="equityLoading" style="height:260px;display:flex;align-items:center;justify-content:center;color:#bbb;">
        <div class="spinner-sm"></div> 计算收益曲线中…
      </div>
      <div v-else-if="equityData.length === 0" style="height:260px;display:flex;align-items:center;justify-content:center;color:#bbb;font-size:13px;">
        暂无收益历史（至少需要一笔交易记录）
      </div>
      <div v-else>
        <div style="margin-bottom:10px;font-size:13px;color:#666;">
          <span v-if="equityData.length > 0">
            最新 {{ equityData[equityData.length-1]?.date }} 市值 ¥{{ fmt(equityData[equityData.length-1]?.value || 0) }}
            <span :class="equityPct >= 0 ? 'up' : 'down'" style="font-weight:600;">
              ({{ equityPct >= 0 ? '+' : '' }}{{ equityPct.toFixed(2) }}%)
            </span>
          </span>
          <el-button size="small" link @click="loadEquityCurve" :loading="equityLoading" style="margin-left:10px;font-size:12px;color:#909399;">⟳ 刷新</el-button>
        </div>
        <div ref="equityChartRef" style="height:320px;width:100%;"></div>
      </div>
    </el-dialog>

    <!-- 分红历史曲线（点击「分红金额」卡片展开/收起） -->
    <el-row v-show="dividendDialog.visible" :gutter="14" style="margin-bottom: 16px;">
      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <span class="block-title">分红历史累计曲线</span>
            <span v-if="dividendSeries.length > 0" style="font-size:12px;color:#aaa;margin-left:10px;">
              累计 ¥{{ fmt(totalDividend) }} · {{ dividendEventCount }} 次分红事件
            </span>
          </template>
          <div v-if="dividendSeries.length === 0" style="height:200px;display:flex;align-items:center;justify-content:center;color:#bbb;font-size:13px;">
            暂无分红记录。点击「💰 分红记录」按钮记一笔。
          </div>
          <div v-else ref="dividendChartRef" style="height:240px;width:100%;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 持仓饼图 -->
    <el-row :gutter="14" style="margin-bottom: 16px;">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header><span class="block-title">股票持仓分布</span></template>
          <div v-if="stockPieData.length === 0" style="height:220px;display:flex;align-items:center;justify-content:center;color:#bbb;font-size:13px;">暂无股票持仓</div>
          <div v-else ref="stockPieRef" style="height:220px;width:100%;"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header><span class="block-title">基金持仓分布</span></template>
          <div v-if="fundPieData.length === 0" style="height:220px;display:flex;align-items:center;justify-content:center;color:#bbb;font-size:13px;">暂无基金持仓</div>
          <div v-else ref="fundPieRef" style="height:220px;width:100%;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 持仓汇总 -->
    <el-card class="block" shadow="never">
      <template #header>
        <span class="block-title">持仓汇总</span>
        <el-button size="small" link @click="loadQuotes" style="margin-left: 10px; font-size: 12px; color: #909399;">⟳ 刷新行情</el-button>
      </template>
      <el-table :data="holdings" stripe style="width: 100%" empty-text="暂无持仓">
        <el-table-column label="代码" width="95">
          <template #default="{ row }">
            <a class="link-name" @click="openHoldingChart(row)">{{ row.code }}</a>
          </template>
        </el-table-column>
        <el-table-column label="名称" min-width="110">
          <template #default="{ row }">
            <a class="link-name" @click="openHoldingChart(row)">{{ row.name }}</a>
          </template>
        </el-table-column>
        <el-table-column label="持仓数量" width="110" align="right">
          <template #default="{ row }">{{ fmtQty(row.netQty, row.isFund) }}</template>
        </el-table-column>
        <el-table-column label="持仓成本" width="110" align="right">
          <template #default="{ row }">¥{{ fmt(row.cost) }}</template>
        </el-table-column>
        <el-table-column label="成本单价" width="105" align="right">
          <template #default="{ row }">
            <span>{{ fmtPrice(row.costPerShare, row.isFund) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="现价" width="100" align="right">
          <template #default="{ row }">
            <span v-if="row.curPrice > 0" :class="fmtPctClass(row.changePct)">
              ¥{{ fmtPrice(row.curPrice, row.isFund) }}
            </span>
            <span v-else style="color:#bbb">—</span>
          </template>
        </el-table-column>
        <el-table-column label="日涨跌" width="90" align="right">
          <template #default="{ row }">
            <span v-if="row.changePct != null" :class="fmtPctClass(row.changePct)">
              {{ fmtPct(row.changePct) }}
            </span>
            <span v-else style="color:#bbb">—</span>
          </template>
        </el-table-column>
        <el-table-column label="市值" width="120" align="right">
          <template #default="{ row }">
            <span v-if="row.marketVal > 0">¥{{ fmt(row.marketVal) }}</span>
            <span v-else style="color:#bbb">—</span>
          </template>
        </el-table-column>
        <el-table-column label="浮盈亏" width="120" align="right">
          <template #default="{ row }">
            <span v-if="row.cost > 0" :class="fmtPctClass(row.unrealizedPct)">
              <span class="pl-amount">{{ row.unrealized >= 0 ? '+' : '' }}¥{{ fmt(Math.abs(row.unrealized)) }}</span>
              <span class="pl-pct" style="font-size:11px; margin-left:3px;">{{ fmtPct(row.unrealizedPct) }}</span>
            </span>
            <span v-else style="color:#bbb">—</span>
          </template>
        </el-table-column>
        <el-table-column label="交易记录" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link size="small" type="primary" @click="openTradeHistoryDialog(row)">
              {{ row.tradeCount || 0 }} 笔 ▸
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 清仓汇总 -->
    <el-card v-if="closedPositions.length > 0" class="block" shadow="never" style="margin-top: 16px;">
      <template #header>
        <span class="block-title">清仓汇总</span>
        <span style="margin-left: 10px; font-size: 12px; color: #909399;">共 {{ closedPositions.length }} 只</span>
      </template>
      <el-table :data="closedPositions" stripe style="width: 100%" empty-text="暂无清仓记录">
        <el-table-column label="代码" width="95">
          <template #default="{ row }">
            <span :class="row.isFund ? 'fund-tag' : ''">{{ row.code }}</span>
          </template>
        </el-table-column>
        <el-table-column label="名称" min-width="120">
          <template #default="{ row }">{{ row.name }}</template>
        </el-table-column>
        <el-table-column label="类型" width="70" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.isFund ? 'warning' : 'primary'" effect="light">
              {{ row.isFund ? '基金' : '股票' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="持有天数" width="90" align="right">
          <template #default="{ row }">
            <span style="color: #666;">{{ row.holdDays }} 天</span>
          </template>
        </el-table-column>
        <el-table-column label="总投入" width="110" align="right">
          <template #default="{ row }">¥{{ fmt(row.buyAmt) }}</template>
        </el-table-column>
        <el-table-column label="总卖出" width="110" align="right">
          <template #default="{ row }">¥{{ fmt(row.sellAmt) }}</template>
        </el-table-column>
        <el-table-column label="手续费" width="90" align="right">
          <template #default="{ row }">
            <span style="color: #999; font-size: 12px;">¥{{ fmt(row.totalFee) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="收益金额" width="120" align="right">
          <template #default="{ row }">
            <span :class="row.profit >= 0 ? 'up' : 'down'">
              {{ row.profit >= 0 ? '+' : '' }}¥{{ fmt(Math.abs(row.profit)) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="收益率" width="100" align="right">
          <template #default="{ row }">
            <span :class="row.profitPct >= 0 ? 'up' : 'down'">
              {{ row.profitPct >= 0 ? '+' : '' }}{{ row.profitPct.toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="交易记录" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link size="small" type="primary" @click="openClosedTradeHistory(row)">
              {{ row.tradeCount }} 笔 ▸
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="清仓日期" width="110" align="center">
          <template #default="{ row }">
            <span style="color: #999; font-size: 12px;">{{ row.lastDate }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 交易明细 → 年度月度交易点状图（弹窗） -->
    <el-dialog v-model="monthlyDialog.visible" title="📊 本年度月度交易点状图" width="780px" :close-on-click-modal="true" align-center>
      <div class="monthly-head" style="margin-bottom:10px;">
        <span style="font-size:13px;color:#666;">{{ currentYear }} 年 · 共 <b>{{ trades.length }}</b> 笔（买入 <span style="color:#ef232a;font-weight:600;">{{ buyCount }}</span> · 卖出 <span style="color:#14b143;font-weight:600;">{{ sellCount }}</span>）</span>
        <div class="monthly-legend">
          <span class="ml-dot ml-dot-buy"></span><span style="margin-right:14px;">买入</span>
          <span class="ml-dot ml-dot-sell"></span><span>卖出</span>
        </div>
      </div>
      <div v-if="monthlyBuy.length === 0 && monthlySell.length === 0" style="height:240px;display:flex;align-items:center;justify-content:center;color:#bbb;">本年度暂无交易</div>
      <div v-else ref="monthlyChartRef" style="height:280px;width:100%;"></div>
    </el-dialog>

    <!-- 新增弹窗 -->
    <el-dialog v-model="dialogVisible" :title="batchMode ? '批量新增交易' : '新增交易'" :width="batchMode ? '900px' : '440px'" @closed="resetForm">
      <!-- 单/批量模式切换 -->
      <div class="mode-toggle-bar" v-if="!batchMode">
        <el-button size="small" type="primary" plain @click="startBatchMode">📋 切换到批量添加</el-button>
        <span class="mode-hint">同一只股票多笔操作？点此一次录入多行</span>
      </div>
      <div class="mode-toggle-bar" v-else>
        <el-button size="small" type="warning" plain @click="exitBatchMode">↩ 返回单笔添加</el-button>
        <span class="mode-hint">代码/名称在顶部统一填写；下方一次性录入多行或从 Excel 粘贴</span>
      </div>

      <!-- 代码/名称（两种模式共享） -->
      <el-form :model="form" label-width="80px">
        <el-form-item label="从自选股">
          <el-select v-model="pickFromWatch" placeholder="可快速带入代码/名称" clearable filterable style="width: 100%;" @change="onPickWatch">
            <el-option v-for="w in watchlist" :key="w.code" :label="`${w.name} (${w.code})`" :value="w.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="代码" required>
          <el-input v-model="form.code" placeholder="如 600519" maxlength="12" />
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如 贵州茅台" maxlength="32" />
        </el-form-item>
      </el-form>

      <!-- 单笔模式（默认） -->
      <el-form v-if="!batchMode" :model="form" label-width="80px">
        <el-form-item label="方向" required>
          <el-radio-group v-model="form.trade_type">
            <el-radio value="buy">买入</el-radio>
            <el-radio value="sell">卖出</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="日期" required>
          <el-date-picker v-model="form.trade_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="价格" required>
          <el-input-number
            v-model="form.price"
            :min="isFund ? 0.0001 : 0.01"
            :step="isFund ? 0.0001 : 0.01"
            :precision="isFund ? 4 : 2"
            style="width: 100%;"
          />
          <div v-if="priceHint" class="price-hint">{{ priceHint }}</div>
        </el-form-item>

        <!-- 数量/金额切换 -->
        <el-form-item label="交易方式">
          <el-radio-group v-model="qtyMode" style="width: 100%;">
            <el-radio value="qty">按数量</el-radio>
            <el-radio value="amt">按金额</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 按数量 -->
        <el-form-item v-if="qtyMode === 'qty'" label="数量" required>
          <el-input-number
            v-model="form.quantity"
            :min="1"
            :step="100"
            style="width: 100%;"
          />
          <div class="calc-hint">金额 ≈ ¥{{ fmt(calcAmount) }}</div>
        </el-form-item>

        <!-- 按金额 -->
        <el-form-item v-else label="金额" required>
          <el-input-number
            v-model="form.amountInput"
            :min="1"
            :step="1000"
            :precision="2"
            style="width: 100%;"
          />
          <div class="calc-hint">数量 ≈ {{ calcQty }} {{ isFund ? '份' : '股' }}</div>
        </el-form-item>
        <el-form-item label="手续费">
          <el-input-number v-model="form.fee" :min="0" :step="1" :precision="2" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>

      <!-- 批量模式 -->
      <div v-else class="batch-mode">
        <!-- CSV / TSV 快速导入 -->
        <div class="batch-csv">
          <div class="batch-csv-head">
            <span style="font-weight:600;">📋 从 Excel / 同花顺 / 表格粘贴：</span>
            <span style="color:#999;font-size:12px;">支持表头：方向 / 日期 / 价格 / 数量 / 金额 / 手续费 / 备注（制表符或逗号分隔）</span>
          </div>
          <el-input v-model="batchCsvText" type="textarea" :rows="4" placeholder="例：&#10;方向&#9;日期&#9;价格&#9;数量&#9;手续费&#9;备注&#10;买入&#9;2026-01-15&#9;12.50&#9;1000&#9;5&#10;卖出&#9;2026-02-20&#9;13.80&#9;500&#9;5" />
          <div style="margin-top:8px;display:flex;gap:8px;">
            <el-button size="small" type="primary" plain @click="parseBatchText">⚡ 解析并填充到下方</el-button>
            <el-button size="small" @click="batchCsvText = ''">清空文本</el-button>
            <el-button size="small" type="danger" plain @click="clearBatchRows">清空所有行</el-button>
          </div>
        </div>

        <el-divider style="margin: 14px 0 10px;"><span style="color:#999;font-size:12px;">或手动逐行填写（代码/名称取顶部）</span></el-divider>

        <div class="batch-rows">
          <div class="batch-row batch-head">
            <span class="c-num">#</span>
            <span class="c-type">方向</span>
            <span class="c-date">日期</span>
            <span class="c-price">价格</span>
            <span class="c-qty">数量</span>
            <span class="c-fee">手续费</span>
            <span class="c-div">分红</span>
            <span class="c-note">备注</span>
            <span class="c-act">操作</span>
          </div>
          <div v-for="(r, idx) in batchRows" :key="idx" class="batch-row" :class="{ 'is-invalid': !r.trade_type || !r.trade_date || !r.price || !r.quantity }">
            <span class="c-num">{{ idx + 1 }}</span>
            <el-select v-model="r.trade_type" size="small" style="width:88px;">
              <el-option label="买入" value="buy" />
              <el-option label="卖出" value="sell" />
            </el-select>
            <el-date-picker v-model="r.trade_date" type="date" size="small" value-format="YYYY-MM-DD" format="MM-DD" placeholder="日期" style="width:120px;" />
            <el-input-number v-model="r.price" size="small" :min="0" :step="0.01" :precision="isFund ? 4 : 2" :controls="false" style="width:96px;" placeholder="价格" />
            <el-input-number v-model="r.quantity" size="small" :min="1" :step="100" :controls="false" style="width:96px;" placeholder="数量" />
            <el-input-number v-model="r.fee" size="small" :min="0" :step="1" :precision="2" :controls="false" style="width:80px;" placeholder="手续费" />
            <el-input v-model="r.notes" size="small" placeholder="备注（可选）" style="width:140px;" />
            <el-button-group size="small">
              <el-button size="small" link @click="insertBatchRow(idx + 1)" title="在下方插入一行">➕</el-button>
              <el-button size="small" link type="danger" @click="removeBatchRow(idx)" title="删除该行">❌</el-button>
            </el-button-group>
          </div>
        </div>

        <div class="batch-footer">
          <el-button size="small" type="primary" plain @click="addBatchRow">➕ 添加一行</el-button>
          <span style="color:#666;font-size:12px;margin-left:12px;">
            共 <b>{{ batchRows.length }}</b> 行，有效 <b style="color:#67c23a;">{{ batchValidCount }}</b> 笔
          </span>
        </div>
      </div>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button v-if="batchMode" type="primary" :disabled="batchValidCount === 0 || !form.code || !form.name" :loading="batchSubmitting" @click="submitBatch">💾 批量保存 {{ batchValidCount }} 笔</el-button>
        <el-button v-else type="primary" :disabled="!canSubmit" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 关联指数对话框 -->
    <el-dialog
      v-model="linkDialog.visible"
      :title="`🔗 关联指数 · ${linkDialog.name}`"
      width="520px"
    >
      <div class="edit-tips">
        <div>💡 选择「{{ linkDialog.name }}」追踪的宽基/行业指数，系统自动读取该指数的10年分位数据作为信号。</div>
        <div>📌 先在「指数估值」页填入指数分位，信号才会显示档位。</div>
      </div>
      <div class="link-list" v-if="availableIndices.length">
        <div
          v-for="idx in availableIndices"
          :key="idx.code"
          class="link-item"
          :class="{ active: linkDialog.currentIndexCode === idx.code }"
          @click="doLink(idx)"
        >
          <div class="link-item-left">
            <span class="link-idx-name">{{ idx.name }}</span>
            <span class="link-idx-code">{{ idx.code }}</span>
            <span v-if="!idx.is_fixed" class="link-custom-tag">自选</span>
          </div>
          <div class="link-item-right">
            <span v-if="idx.has_pct" class="link-pct-ok">✅ PE={{ idx.pe_pct }}%</span>
            <span v-else class="link-pct-empty">❌ 未填分位</span>
          </div>
        </div>
      </div>
      <div v-else class="loading-row" style="padding: 20px;">
        <div class="spinner-sm"></div> 加载中...
      </div>
      <template #footer>
        <el-button @click="linkDialog.visible = false">取消</el-button>
        <el-button type="danger" plain v-if="linkDialog.currentIndexCode" @click="doUnlink">取消关联</el-button>
      </template>
    </el-dialog>

    <!-- 持仓收益曲线弹窗 -->
    <el-dialog v-model="holdingChart.visible" :title="holdingChart.title" width="780px" @closed="closeHoldingChart">
      <div v-if="holdingChart.loading" style="height:300px;display:flex;align-items:center;justify-content:center;">
        <div class="spinner-sm"></div> 计算收益曲线中…
      </div>
      <div v-else-if="holdingChart.data.length === 0" style="height:300px;display:flex;align-items:center;justify-content:center;color:#bbb;">
        暂无历史数据
      </div>
      <template v-else>
        <el-row :gutter="14" style="margin-bottom:12px;">
          <el-col :span="6"><div class="hc-stat"><div class="hc-stat-label">持仓成本</div><div class="hc-stat-value">¥{{ fmt(holdingChart.cost) }}</div></div></el-col>
          <el-col :span="6"><div class="hc-stat"><div class="hc-stat-label">当前市值</div><div class="hc-stat-value">¥{{ fmt(holdingChart.lastVal) }}</div></div></el-col>
          <el-col :span="6"><div class="hc-stat"><div class="hc-stat-label">累计收益</div><div class="hc-stat-value" :class="holdingChart.lastVal - holdingChart.cost >= 0 ? 'up' : 'down'">{{ (holdingChart.lastVal - holdingChart.cost) >= 0 ? '+' : '' }}¥{{ fmt(Math.abs(holdingChart.lastVal - holdingChart.cost)) }}</div></div></el-col>
          <el-col :span="6"><div class="hc-stat"><div class="hc-stat-label">收益率</div><div class="hc-stat-value" :class="holdingChart.pct >= 0 ? 'up' : 'down'">{{ holdingChart.pct >= 0 ? '+' : '' }}{{ holdingChart.pct.toFixed(2) }}%</div></div></el-col>
        </el-row>
        <div ref="holdingChartRef" style="height:340px;width:100%;"></div>
        <div style="font-size:12px;color:#999;margin-top:8px;">
          * 自 {{ holdingChart.data[0]?.date }} 首笔买入至 {{ holdingChart.data[holdingChart.data.length-1]?.date }}，按 FIFO 计算的累计持仓与日线收盘价/净值计算的市值变化
        </div>
      </template>
    </el-dialog>

    <!-- 某品种的历史交易记录弹窗 -->
    <el-dialog v-model="tradeHistory.visible" :title="tradeHistory.title" width="820px" @closed="closeTradeHistory">
      <div v-if="tradeHistory.rows.length === 0" style="padding:30px 0;text-align:center;color:#bbb;">暂无交易记录</div>
      <template v-else>
        <el-row :gutter="14" style="margin-bottom:14px;">
          <el-col :span="6"><div class="hc-stat"><div class="hc-stat-label">总笔数</div><div class="hc-stat-value">{{ tradeHistory.rows.length }}</div></div></el-col>
          <el-col :span="6"><div class="hc-stat"><div class="hc-stat-label">买入金额</div><div class="hc-stat-value up">¥{{ fmt(tradeHistory.buyTotal) }}</div></div></el-col>
          <el-col :span="6"><div class="hc-stat"><div class="hc-stat-label">卖出金额</div><div class="hc-stat-value down">¥{{ fmt(tradeHistory.sellTotal) }}</div></div></el-col>
          <el-col :span="6"><div class="hc-stat"><div class="hc-stat-label">净投入</div><div class="hc-stat-value" :class="tradeHistory.netTotal >= 0 ? 'up' : 'down'">¥{{ fmt(Math.abs(tradeHistory.netTotal)) }}</div></div></el-col>
        </el-row>
        <el-table :data="tradeHistory.rows" stripe size="small" max-height="420" empty-text="无数据">
          <el-table-column prop="trade_date" label="日期" width="110" />
          <el-table-column label="类型" width="70" align="center">
            <template #default="{ row }">
              <el-tag :type="row.trade_type === 'buy' ? 'danger' : 'success'" size="small" effect="light">
                {{ row.trade_type === 'buy' ? '买入' : '卖出' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="价格" width="100" align="right">
            <template #default="{ row }">{{ fmtPrice(row.price, row.isFund) }}</template>
          </el-table-column>
          <el-table-column label="数量" width="90" align="right">
            <template #default="{ row }">{{ row.quantity }}</template>
          </el-table-column>
          <el-table-column label="金额" width="120" align="right">
            <template #default="{ row }">¥{{ fmt(row.price * row.quantity) }}</template>
          </el-table-column>
          <el-table-column label="手续费" width="90" align="right" prop="fee">
            <template #default="{ row }">¥{{ fmt(row.fee || 0) }}</template>
          </el-table-column>
          <el-table-column prop="note" label="备注" min-width="120" show-overflow-tooltip />
          <el-table-column label="操作" width="80" align="center" fixed="right">
            <template #default="{ row }">
              <el-button link size="small" type="danger" @click="removeFromHistory(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-dialog>

    <!-- ══════════════════════════════════════════════
         分红记录独立弹窗
    ══════════════════════════════════════════════ -->
    <el-dialog v-model="divDialog.visible" title="💰 分红记录" width="620px" @closed="onDivDialogClosed">
      <div class="div-add-bar">
        <el-form :inline="true" :model="divForm" size="small" style="flex:1;">
          <el-form-item label="股票" style="margin-bottom:0;">
            <el-select v-model="divForm.code" filterable placeholder="选择或搜索股票" style="width:150px;" @change="onDivCodeChange">
              <el-option v-for="s in watchlistOptions" :key="s.code" :label="`${s.name} (${s.code})`" :value="s.code" />
            </el-select>
          </el-form-item>
          <el-form-item label="日期" style="margin-bottom:0;">
            <el-date-picker v-model="divForm.trade_date" type="date" value-format="YYYY-MM-DD" size="small" style="width:130px;" />
          </el-form-item>
          <el-form-item label="分红金额" style="margin-bottom:0;">
            <el-input-number v-model="divForm.dividend" :min="0.01" :step="10" :precision="2" size="small" style="width:120px;" />
          </el-form-item>
          <el-form-item label="备注" style="margin-bottom:0;">
            <el-input v-model="divForm.notes" size="small" placeholder="可选" style="width:120px;" />
          </el-form-item>
          <el-form-item style="margin-bottom:0;">
            <el-button type="danger" size="small" @click="submitDividend" :disabled="!divForm.code || !divForm.trade_date || !divForm.dividend">记一笔</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-divider style="margin: 12px 0;" />

      <!-- 分红历史列表 -->
      <div v-if="divRows.length === 0" style="padding:24px 0;text-align:center;color:#bbb;">
        暂无分红记录
      </div>
      <el-table v-else :data="divRows" stripe size="small" max-height="340">
        <el-table-column prop="trade_date" label="日期" width="120" />
        <el-table-column label="股票" min-width="140">
          <template #default="{ row }">{{ row.name }} ({{ row.code }})</template>
        </el-table-column>
        <el-table-column label="分红金额" width="120" align="right">
          <template #default="{ row }">
            <span style="color:#e6a23c;font-weight:600;">¥{{ fmt(row.dividend) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="notes" label="备注" min-width="120" show-overflow-tooltip />
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button link size="small" type="danger" @click="removeDividend(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <template #footer>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:13px;color:#888;">共 {{ divRows.length }} 笔 · 累计 <span style="color:#e6a23c;font-weight:600;">¥{{ fmt(totalDividend) }}</span></span>
          <el-button size="small" @click="divDialog.visible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTrades, addTrade, addTradesBatch, deleteTrade, getWatchlist, getStockHistory, getRealtimeQuote, getDividends, addDividend } from '../api/index.js'
import { getAvailableIndices, linkIndex } from '../api/index.js'
import axios from 'axios'
import echarts from '../utils/echarts'

const trades = ref([])
const watchlist = ref([])
const watchlistOptions = computed(() => (watchlist.value || []).filter(s => s && s.code && s.name))
const dialogVisible = ref(false)
const pickFromWatch = ref('')

// ─── 图表相关 ────────────────────────────────────────────────
const equityChartRef = ref(null)
let equityChartInst = null
const stockPieRef = ref(null)
const fundPieRef = ref(null)
let stockPieChart = null
let fundPieChart = null

// ─── 月度交易点状图 ────────────────────────────
const monthlyDialog = reactive({ visible: false })
const monthlyChartRef = ref(null)
let monthlyChart = null
const currentYear = new Date().getFullYear()
const monthlyBuy = computed(() => {
  const counts = new Array(12).fill(0)
  for (const t of trades.value) {
    if (t.trade_type !== 'buy') continue
    const d = t.trade_date
    if (!d || !d.startsWith(String(currentYear))) continue
    const m = parseInt(d.slice(5, 7), 10) - 1
    if (m >= 0 && m < 12) counts[m] += 1
  }
  return counts
})
const monthlySell = computed(() => {
  const counts = new Array(12).fill(0)
  for (const t of trades.value) {
    if (t.trade_type !== 'sell') continue
    const d = t.trade_date
    if (!d || !d.startsWith(String(currentYear))) continue
    const m = parseInt(d.slice(5, 7), 10) - 1
    if (m >= 0 && m < 12) counts[m] += 1
  }
  return counts
})

// ─── 持仓收益曲线弹窗 ────────────────────────────────────────────
const holdingChartRef = ref(null)
let holdingChartInst = null
const holdingChart = ref({
  visible: false,
  loading: false,
  title: '',
  data: [],
  cost: 0,
  lastVal: 0,
  pct: 0,
})

// ─── 某品种交易明细弹窗 ────────────────────────────────────────────
const tradeHistory = ref({
  visible: false,
  title: '',
  rows: [],
  buyTotal: 0,
  sellTotal: 0,
  netTotal: 0,
})

const equityData = ref([])       // [{date, value}]
const equityLoading = ref(false)

const stockPieData = computed(() =>
  holdings.value
    .filter(h => !h.isFund && h.marketVal > 0)
    .map(h => ({ name: h.name || h.code, value: Math.round(h.marketVal * 100) / 100 }))
)

const fundPieData = computed(() =>
  holdings.value
    .filter(h => h.isFund && h.marketVal > 0)
    .map(h => ({ name: h.name || h.code, value: Math.round(h.marketVal * 100) / 100 }))
)

const form = ref({
  code: '',
  name: '',
  trade_type: 'buy',
  trade_date: '',
  price: 0.01,
  quantity: 100,
  amountInput: 10000,  // 金额模式的 UI 临时值
  fee: 0,
  notes: '',
})

// qtyMode: 'qty' = 按数量输入, 'amt' = 按金额输入
const qtyMode = ref('qty')

// ─── 批量新增交易 ────────────────────────────
const batchMode = ref(false)            // 是否为批量模式
const batchRows = ref([])               // 批量行：[{trade_type,trade_date,price,quantity,fee,notes}]
const batchCsvText = ref('')            // CSV 粘贴文本
const batchSubmitting = ref(false)      // 提交中的 loading 状态

function makeEmptyRow() {
  return { trade_type: 'buy', trade_date: '', price: null, quantity: null, fee: 0, notes: '' }
}

function startBatchMode() {
  if (batchRows.value.length === 0) {
    // 默认给 5 行空白
    for (let i = 0; i < 5; i++) batchRows.value.push(makeEmptyRow())
  }
  batchMode.value = true
}
function exitBatchMode() {
  batchMode.value = false
  batchRows.value = []
  batchCsvText.value = ''
}
function addBatchRow() {
  batchRows.value.push(makeEmptyRow())
}
function insertBatchRow(idx) {
  batchRows.value.splice(idx, 0, makeEmptyRow())
}
function removeBatchRow(idx) {
  if (batchRows.value.length <= 1) {
    ElMessage.warning('至少保留一行')
    return
  }
  batchRows.value.splice(idx, 1)
}
function clearBatchRows() {
  batchRows.value = []
  batchCsvText.value = ''
}

// CSV / TSV 解析（支持表头中英映射、换行 / 空格 / 表格拼接）
const CSV_HEADERS = {
  方向: 'trade_type', 买卖: 'trade_type', type: 'trade_type',
  日期: 'trade_date', date: 'trade_date',
  价格: 'price', 价: 'price', price: 'price',
  数量: 'quantity', 份数: 'quantity', quantity: 'quantity', 股数: 'quantity',
  金额: 'amount',
  手续费: 'fee', fee: 'fee',
  备注: 'notes', note: 'notes', notes: 'notes',
}
function parseBatchText() {
  const text = (batchCsvText.value || '').trim()
  if (!text) {
    ElMessage.warning('请先粘贴表格内容')
    return
  }
  // 智能分隔：制表符优先（从 Excel/同花顺复制一般带 \t），否则逗号
  const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean)
  if (lines.length < 2) {
    ElMessage.warning('至少需要表头 + 1 行数据')
    return
  }
  const sep = lines[0].includes('\t') ? '\t' : (lines[0].includes(',') ? ',' : '\t')
  const headers = lines[0].split(sep).map(h => h.trim())
  const fieldMap = headers.map(h => CSV_HEADERS[h] || CSV_HEADERS[h.toLowerCase()] || null)

  if (fieldMap.every(f => f === null)) {
    ElMessage.error('表头无法识别，请包含：方向、日期、价格、数量、金额、手续费、备注 中的至少几列')
    return
  }
  const rows = []
  for (let i = 1; i < lines.length; i++) {
    const cells = lines[i].split(sep).map(c => c.trim())
    const obj = {}
    for (let j = 0; j < fieldMap.length; j++) {
      if (!fieldMap[j]) continue
      obj[fieldMap[j]] = cells[j] ?? ''
    }
    rows.push(obj)
  }
  // 将解析结果转为可保存行：处理方向中文化、处理金额/数量互算
  const code = (form.value.code || '').trim()
  const name = (form.value.name || '').trim()
  if (!code) {
    ElMessage.warning('请先填写代码')
    return
  }
  const out = []
  for (const r of rows) {
    const trade_type = (r.trade_type || '').includes('买') || /buy/i.test(r.trade_type) ? 'buy'
      : (r.trade_type || '').includes('卖') || /sell/i.test(r.trade_type) ? 'sell'
      : 'buy'
    const trade_date = (r.trade_date || '').replace(/\//g, '-')
    if (!trade_date) continue
    let price = parseFloat(r.price)
    if (isNaN(price) || price <= 0) continue
    let quantity = parseFloat(r.quantity)
    let amount = parseFloat(r.amount)
    if (isNaN(quantity) || quantity <= 0) {
      if (!isNaN(amount) && amount > 0) quantity = Math.round(amount / price)
      else continue
    }
    quantity = Math.round(quantity)
    const fee = parseFloat(r.fee) || 0
    out.push({ trade_type, trade_date, price, quantity, fee, notes: r.notes || '' })
  }
  if (out.length === 0) {
    ElMessage.error('未能从粘贴内容解析出有效行')
    return
  }
  batchRows.value = out
  ElMessage.success(`解析成功：${out.length} 行`)
  // 滚动到顶部
  nextTick(() => {
    const el = document.querySelector('.batch-rows')
    if (el) el.scrollTop = 0
  })
}

const batchValidCount = computed(() => {
  return batchRows.value.filter(r =>
    r.trade_type && r.trade_date && r.price > 0 && r.quantity > 0
  ).length
})

async function submitBatch() {
  if (batchSubmitting.value) return
  if (!form.value.code || !form.value.name) {
    ElMessage.warning('请填写代码和名称')
    return
  }
  const code = form.value.code.trim()
  const name = form.value.name.trim()
  // 1) 过滤 + 严格校验每一行（预防 422）
  const errors = []
  const validRows = []
  batchRows.value.forEach((r, idx) => {
    const rowNo = idx + 1
    if (!r.trade_type || !['buy', 'sell'].includes(r.trade_type)) {
      errors.push(`第 ${rowNo} 行：方向必须是买入/卖出`)
      return
    }
    if (!r.trade_date) {
      errors.push(`第 ${rowNo} 行：日期不能为空`)
      return
    }
    // 日期格式检查（YYYY-MM-DD）
    if (!/^\d{4}-\d{2}-\d{2}$/.test(r.trade_date)) {
      errors.push(`第 ${rowNo} 行：日期格式错误（应为 YYYY-MM-DD，当前 "${r.trade_date}"）`)
      return
    }
    const price = Number(r.price)
    if (!r.price || isNaN(price) || price <= 0) {
      errors.push(`第 ${rowNo} 行：价格必须为正数`)
      return
    }
    const qty = Number(r.quantity)
    if (!r.quantity || isNaN(qty) || qty <= 0) {
      errors.push(`第 ${rowNo} 行：数量必须为正数`)
      return
    }
    if (!Number.isInteger(qty)) {
      errors.push(`第 ${rowNo} 行：数量必须为整数（${qty}）`)
      return
    }
    validRows.push({ trade_type: r.trade_type, trade_date: r.trade_date, price, quantity: qty, fee: Number(r.fee) || 0, notes: r.notes || '' })
  })
  if (errors.length > 0) {
    // 弹窗提示前 3 条错误
    const shown = errors.slice(0, 3).join('；')
    const more = errors.length > 3 ? `；还有 ${errors.length - 3} 条错误` : ''
    ElMessage.error(`提交失败：${shown}${more}`)
    console.error('[batch validation errors]', errors)
    return
  }
  if (validRows.length === 0) {
    ElMessage.warning('请至少填写一笔有效交易')
    return
  }

  // 批量卖出校验：累加同一品种的卖出数量，检查是否超持仓
  const currentQty = getCurrentHoldingQty(code)
  const totalSellQty = validRows
    .filter(r => r.trade_type === 'sell')
    .reduce((sum, r) => sum + r.quantity, 0)
  if (totalSellQty > currentQty) {
    ElMessage.error(`批量卖出数量总计 (${totalSellQty}) 超过当前持仓 (${currentQty})，无法提交`)
    return
  }

  batchSubmitting.value = true
  try {
    const payload = validRows.map(r => ({
      code, name,
      trade_type: r.trade_type,
      trade_date: r.trade_date,
      price: r.price,
      quantity: r.quantity,
      fee: r.fee,
      notes: r.notes,
    }))
    console.log('[submitBatch] payload:', JSON.stringify(payload, null, 2))
    await addTradesBatch(payload)
    ElMessage.success(`已批量保存 ${validRows.length} 笔交易`)
    exitBatchMode()
    dialogVisible.value = false
    await loadTrades()
  } catch (e) {
    console.error('批量保存失败', e)
    const detail = e.response?.data?.detail
    let msg
    if (Array.isArray(detail)) {
      // Pydantic 422: [{loc:['body',0,'price'], msg:'...', type:'...'}]
      msg = detail.map(d => {
        const field = Array.isArray(d.loc) ? d.loc.slice(-2).join('.') : d.loc
        return `${field}: ${d.msg}`
      }).join('；')
    } else if (typeof detail === 'string') {
      msg = detail
    } else {
      msg = e.message
    }
    ElMessage.error(`批量保存失败（${e.response?.status || '未知'}）：${msg}`)
  } finally {
    batchSubmitting.value = false
  }
}

const canSubmit = computed(() => form.value.code && form.value.name && form.value.trade_date && form.value.price > 0 && form.value.quantity > 0)

// 价格自动提示信息
const priceHint = ref('')

// 判断是否为场外基金代码（与后端 _is_fund_code 保持一致）
// 股票代码：6 位、以 0/3/6 开头、且不是 000/001/002/003 之外的小数 0 开头
// 场外基金：其它 6 位数字，或非 6 位
function isFundCode(code) {
  if (!code || code.length !== 6) return true
  if ('036'.includes(code[0])) {
    if (code[0] === '0' && !['000', '001', '002', '003'].some(p => code.startsWith(p))) {
      return true
    }
    return false
  }
  return true
}

const isFund = computed(() => isFundCode(form.value.code))

// 根据选中的代码和日期自动获取价格（股票用收盘价，场外基金用净值）
async function fetchPriceByDate() {
  if (!form.value.code || !form.value.trade_date) {
    priceHint.value = ''
    return
  }
  priceHint.value = '正在获取历史价格…'
  try {
    const { data } = await getStockHistory(form.value.code, 365)
    const bars = data?.bars || []
    if (bars.length === 0) {
      priceHint.value = ''
      return
    }

    const targetDate = form.value.trade_date
    // 1. 精确匹配
    let match = bars.find(b => b.date === targetDate)
    let isApprox = false
    // 2. 找最近的前一个交易日
    if (!match) {
      const prevCandidates = bars.filter(b => b.date < targetDate)
      if (prevCandidates.length > 0) {
        match = prevCandidates[prevCandidates.length - 1]
        isApprox = true
      }
    }
    // 3. 找最近的下一个交易日
    if (!match) {
      match = bars.find(b => b.date > targetDate)
      isApprox = true
    }

    if (match) {
      form.value.price = match.close
      priceHint.value = isApprox
        ? `该日无数据，已使用 ${match.date} 的价格`
        : `已自动填入 ${match.date} 的价格`
    } else {
      priceHint.value = ''
    }
  } catch (e) {
    priceHint.value = ''
    console.error('获取价格失败', e)
  }
}

// 监听日期或代码变化，自动填充价格
watch(
  [() => form.value.trade_date, () => form.value.code],
  () => { fetchPriceByDate() }
)

// 按金额模式：同步 amountInput <-> quantity
watch(
  () => form.value.price,
  () => {
    if (qtyMode.value === 'amt' && form.value.price > 0 && form.value.amountInput > 0) {
      form.value.quantity = calcQtyVal(form.value.amountInput, form.value.price)
    }
  }
)

// 按金额模式切换时，金额<->数量互转
watch(qtyMode, (mode) => {
  if (mode === 'amt' && form.value.price > 0 && form.value.quantity > 0) {
    form.value.amountInput = Math.round(form.value.quantity * form.value.price * 100) / 100
  } else if (mode === 'qty' && form.value.price > 0 && form.value.amountInput > 0) {
    form.value.quantity = calcQtyVal(form.value.amountInput, form.value.price)
  }
})

function calcQtyVal(amt, price) {
  if (!price || price <= 0) return 0
  const qty = amt / price
  // 基金保留4位小数，股票取整
  return isFund.value ? Math.round(qty * 10000) / 10000 : Math.round(qty)
}

const calcAmount = computed(() => form.value.quantity * form.value.price)
const calcQty = computed(() => calcQtyVal(form.value.amountInput, form.value.price))

const buyCount = computed(() => trades.value.filter(t => t.trade_type === 'buy').length)
const sellCount = computed(() => trades.value.filter(t => t.trade_type === 'sell').length)
const buyAmount = computed(() => trades.value.filter(t => t.trade_type === 'buy').reduce((s, t) => s + t.price * t.quantity + (t.fee || 0), 0))
const sellAmount = computed(() => trades.value.filter(t => t.trade_type === 'sell').reduce((s, t) => s + t.price * t.quantity - (t.fee || 0), 0))
const netInvest = computed(() => buyAmount.value - sellAmount.value)
// 总收益 = 卖出金额 + 当前持仓市值 - 买入金额 - 手续费 （实际：卖出 - 净成本 + 当前市值 - 净成本）
// 简化：总收益 = 累计卖出金额 + 当前持仓市值 - 累计买入金额
const totalProfit = computed(() => {
  const marketVal = holdings.value.reduce((s, h) => s + (h.marketVal || 0), 0)
  return sellAmount.value + marketVal - buyAmount.value
})

// 收益历史波动弹窗
const equityDialog = reactive({ visible: false })
// equityChartRef 已在顶部声明

function openEquityDialog() {
  equityDialog.visible = true
}

function onEquityDialogOpened() {
  // 延迟以确保弹窗动画完成、容器有尺寸
  setTimeout(() => renderEquityChart(), 150)
}

function onEquityDialogClosed() {
  // 清理图表实例，下次打开重新初始化
  if (equityChartInst) {
    equityChartInst.dispose()
    equityChartInst = null
  }
}

// 收益率 = 总收益 / 累计投入资金（才是真实的「投入回报率」）
// 不再以「首日市值」为分母（那只是首日持仓的价格变化，不能反映全部资金的回报）
const equityPct = computed(() => {
  if (buyAmount.value <= 0) return 0
  return (totalProfit.value / buyAmount.value) * 100
})

// ---- 分红历史累计曲线 ----
const dividendDialog = reactive({ visible: false })
const dividendChartRef = ref(null)
let dividendChartInst = null

// 分红累计金额 — 独立接口，不混入交易列表
const totalDividend = ref(0)
async function refreshTotalDividend() {
  try {
    const { data } = await getDividends()
    totalDividend.value = (data || []).reduce((s, t) => s + (Number(t.dividend) || 0), 0)
  } catch (e) { /* ignore */ }
}
onMounted(refreshTotalDividend)

// 股息事件：来自独立分红接口，按日期排序
const dividendEvents = computed(() =>
  [...divRows.value].sort((a, b) => a.trade_date.localeCompare(b.trade_date))
)

// 累计曲线数据点
const dividendSeries = computed(() => {
  const evts = dividendEvents.value
  if (!evts.length) return []
  let cum = 0
  return evts.map(e => {
    cum += Number(e.dividend)
    return { date: e.trade_date, value: cum, raw: e }
  })
})

const dividendEventCount = computed(() => divRows.value.length)

function openDividendChart() {
  dividendDialog.visible = !dividendDialog.visible
  if (dividendDialog.visible) {
    loadDivRows()
    nextTick(renderDividendChart)
  }
}

function renderDividendChart() {
  const dom = dividendChartRef.value
  if (!dom) return
  if (!dividendChartInst) {
    dividendChartInst = echarts.init(dom)
  }
  const series = dividendSeries.value
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter(params) {
        const p = params[0]
        const raw = series[p.dataIndex]?.raw
        let tip = `<b>${p.value[0]}</b><br/>累计分红：¥${p.value[1].toFixed(2)}`
        if (raw) {
          tip += `<br/>${raw.name}<br/>${raw.code} · ${raw.trade_type === 'buy' ? '买入' : '卖出'} ¥${raw.price} × ${raw.quantity}`
        }
        return tip
      }
    },
    xAxis: {
      type: 'category',
      data: series.map(d => d.date),
      axisLabel: { fontSize: 11, color: '#666' }
    },
    yAxis: {
      type: 'value',
      name: '累计分红（元）',
      nameTextStyle: { fontSize: 11, color: '#888' },
      axisLabel: { fontSize: 11, color: '#666', formatter: v => `¥${v.toFixed(0)}` }
    },
    series: [{
      type: 'line',
      data: series.map(d => [d.date, d.value]),
      smooth: true,
      lineStyle: { width: 2, color: '#e6a23c' },
      itemStyle: { color: '#e6a23c' },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: 'rgba(230,162,60,0.3)' },
        { offset: 1, color: 'rgba(230,162,60,0.02)' }
      ]) },
      symbol: 'circle',
      symbolSize: 8
    }],
    grid: { left: 60, right: 20, top: 16, bottom: 32 }
  }
  dividendChartInst.setOption(option)
  nextTick(() => dividendChartInst && dividendChartInst.resize())
}

watch(() => dividendDialog.visible, v => { if (v) nextTick(renderDividendChart) })

// ══════════════════════════════════════════════
// 分红记录独立弹窗
// ══════════════════════════════════════════════
const divDialog = reactive({ visible: false })
const divRows = ref([])
const divForm = reactive({ code: '', name: '', trade_date: '', dividend: null, notes: '' })

function openDivDialog() {
  divDialog.visible = true
  loadDivRows()
  // 默认填今天
  if (!divForm.trade_date) {
    divForm.trade_date = new Date().toISOString().slice(0, 10)
  }
}

async function loadDivRows() {
  try {
    const { data } = await getDividends()
    divRows.value = data || []
  } catch (e) {
    console.error('loadDivRows error:', e)
  }
}

function onDivCodeChange(code) {
  if (!code) return
  const s = watchlistOptions.value.find(o => o && o.code === code)
  if (s) divForm.name = s.name
}

async function submitDividend() {
  if (!divForm.code || !divForm.trade_date || !divForm.dividend) return
  const name = divForm.name || divForm.code
  try {
    await addDividend({
      code: divForm.code,
      name,
      trade_date: divForm.trade_date,
      dividend: divForm.dividend,
      notes: divForm.notes,
    })
    ElMessage.success('分红已记录')
    // 重置表单
    divForm.dividend = null
    divForm.notes = ''
    await loadDivRows()
    await refreshTotalDividend()
  } catch (e) {
    console.error('submitDividend error:', e)
    ElMessage.error('记录失败：' + (e.message || '未知错误'))
  }
}

async function removeDividend(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除 ${row.name} (${row.code}) ${row.trade_date} 分红 ¥${row.dividend}？`,
      '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await deleteTrade(row.id)
    ElMessage.success('已删除')
    divRows.value = divRows.value.filter(r => r.id !== row.id)
    await refreshTotalDividend()
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  }
}

function onDivDialogClosed() {
  divForm.code = ''
  divForm.name = ''
  divForm.notes = ''
  divForm.dividend = null
  // 不清 trade_date，保留日期方便连续录入
}

// 实时行情缓存 { code: { price, change_pct, name } }
const quotes = ref({})

// 估值信号缓存 { code: { band, pe/pb/percentile } }
const holdingsSignals = ref({})

// ETF → 追踪的宽基指数代码（经验映射）
const ETF_TO_INDEX = {
  '512000': '000300', '512880': '000300', '510300': '000300',
  '159915': '399006',
  '510050': '000016',
}

async function loadSignals() {
  try {
    const { data } = await axios.get('/api/valuation/watchlist/signals')
    const sigMap = {}
    for (const s of (data.watchlist_signals || [])) {
      sigMap[s.code] = s
    }
    holdingsSignals.value = sigMap
  } catch (e) {
    console.error('loadSignals failed', e)
  }
}

const BAND_MAP = {
  extreme_low: '极度低估', low: '低估', normal: '正常',
  high: '高估', extreme_high: '极度高估', unknown: '暂无',
}
function bandLabel(band) { return BAND_MAP[band] || band || '—' }

/**
 * 持仓成本计算（FIFO 逻辑）
 * 1. 按时间顺序追踪每笔买/卖
 * 2. 卖出时，回收对应比例的买入成本
 * 3. cost = max(buyAmt - sell回收的成本, 0)
 * 4. costPerShare = cost / netQty（若仍持仓）
 * 5. 实时市值 = netQty * currentPrice
 * 6. 浮盈亏 = 市值 - cost
 */

// 获取指定代码的当前持仓数量（用于卖出校验）
function getCurrentHoldingQty(code) {
  const myTrades = trades.value
    .filter(t => t.code === code)
    .sort((a, b) => a.trade_date.localeCompare(b.trade_date) || (a.id - b.id))
  let buyQty = 0, sellQty = 0
  for (const t of myTrades) {
    if (t.trade_type === 'buy') {
      buyQty += t.quantity
    } else {
      sellQty += t.quantity
    }
  }
  return Math.max(buyQty - sellQty, 0)
}

function calcHoldingCost(code) {
  const myTrades = trades.value
    .filter(t => t.code === code)
    .sort((a, b) => a.trade_date.localeCompare(b.trade_date) || (a.id - b.id))

  let buyQty = 0, buyAmt = 0
  let sellQty = 0

  for (const t of myTrades) {
    if (t.trade_type === 'buy') {
      buyQty += t.quantity
      buyAmt += t.price * t.quantity + (t.fee || 0)
    } else {
      sellQty += t.quantity
      // 卖出时，按比例回收成本
      if (buyQty > 0) {
        const ratio = Math.min(t.quantity / buyQty, 1)
        buyAmt -= buyAmt * ratio
        buyQty -= t.quantity
      }
    }
  }

  const netQty = buyQty  // 剩余未卖出数量
  const cost = Math.max(buyAmt, 0)  // 剩余持仓成本
  const costPerShare = netQty > 0 ? cost / netQty : 0
  const quote = quotes.value[code]
  const curPrice = quote?.price || 0
  const marketVal = netQty * curPrice
  const unrealized = marketVal - cost
  const unrealizedPct = cost > 0 ? (unrealized / cost) * 100 : 0
  const isFund = isFundCode(code)

  return {
    code,
    // 名字优先级：行情API名字（且不是代码本身）> 交易记录中的名字 > 代码
    name: (quote?.name && quote.name !== code ? quote.name : null)
          || myTrades[0]?.name
          || code,
    netQty,
    cost,
    costPerShare,
    curPrice,
    marketVal,
    unrealized,
    unrealizedPct,
    changePct: quote?.change_pct ?? null,
    isFund,
    tradeCount: myTrades.length,
  }
}

// 持仓汇总（只显示有持仓的，已清仓的在清仓汇总里显示）
const holdings = computed(() => {
  const codes = [...new Set(trades.value.map(t => t.code))]
  return codes
    .map(code => calcHoldingCost(code))
    .filter(h => h.netQty > 0)  // 只显示有持仓的
    .sort((a, b) => b.marketVal - a.marketVal)
})

// 清仓汇总（已完全卖出的品种）
const closedPositions = computed(() => {
  const codes = [...new Set(trades.value.map(t => t.code))]
  const result = []
  for (const code of codes) {
    const myTrades = trades.value
      .filter(t => t.code === code)
      .sort((a, b) => a.trade_date.localeCompare(b.trade_date) || (a.id - b.id))
    if (myTrades.length === 0) continue
    let buyQty = 0, sellQty = 0
    let buyAmt = 0, sellAmt = 0
    let totalFee = 0
    for (const t of myTrades) {
      if (t.trade_type === 'buy') {
        buyQty += t.quantity
        buyAmt += t.price * t.quantity
      } else {
        sellQty += t.quantity
        sellAmt += t.price * t.quantity
      }
      totalFee += t.fee || 0
    }
    // 只有完全清仓的才显示（买入=卖出，且都有交易）
    if (buyQty > 0 && sellQty > 0 && buyQty === sellQty) {
      const firstDate = myTrades[0].trade_date
      const lastDate = myTrades[myTrades.length - 1].trade_date
      const holdDays = Math.max(1, Math.round((new Date(lastDate) - new Date(firstDate)) / (1000 * 60 * 60 * 24)))
      const profit = sellAmt - buyAmt - totalFee
      const profitPct = buyAmt > 0 ? (profit / buyAmt) * 100 : 0
      const isFund = isFundCode(code)
      result.push({
        code,
        name: myTrades[0].name || code,
        isFund,
        firstDate,
        lastDate,
        holdDays,
        buyAmt,
        sellAmt,
        totalFee,
        profit,
        profitPct,
        tradeCount: myTrades.length,
      })
    }
  }
  return result.sort((a, b) => new Date(b.lastDate) - new Date(a.lastDate))
})

async function loadQuotes() {
  const codes = [...new Set(trades.value.map(t => t.code))]
  const results = {}

  // 1. 先批量拿实时行情
  await Promise.allSettled(
    codes.map(async (code) => {
      try {
        const { data } = await getRealtimeQuote(code)
        results[code] = {
          price: data.price || 0,
          change_pct: data.change_pct ?? data.change ?? null,
          name: data.name,
        }
      } catch {
        results[code] = { price: 0, change_pct: null, name: '' }
      }
    })
  )

  // 2. 基金没有实时行情，用历史净值最后一条补充
  const fundCodes = codes.filter(c => (results[c]?.price || 0) === 0 && isFundCode(c))
  await Promise.allSettled(
    fundCodes.map(async (code) => {
      try {
        const { data } = await getStockHistory(code, 30)
        const bars = data?.bars || []
        if (bars.length > 0) {
          const last = bars[bars.length - 1]
          results[code] = {
            price: last.close,
            change_pct: last.change_pct ?? null,
            name: results[code]?.name || code,
          }
        }
      } catch {
        // 历史也拿不到就不展示了
      }
    })
  )

  quotes.value = results
  loadSignals()  // 同步刷新信号
}

// ════════════════════════════════════════════════════════════════
//  收益历史曲线
// ════════════════════════════════════════════════════════════════
async function loadEquityCurve() {
  if (trades.value.length === 0) { equityData.value = []; return }
  equityLoading.value = true

  try {
    // 1. 收集所有交易日期（含今天）
    const dates = [...new Set(trades.value.map(t => t.trade_date))]
    dates.sort()
    const today = new Date().toISOString().slice(0, 10)
    if (!dates.includes(today)) dates.push(today)

    // 2. 收集所有持仓代码
    const codes = [...new Set(trades.value.map(t => t.code))]

    // 3. 批量拉历史K线（取近365天，覆盖所有交易日期）
    const priceMap = {}   // code → { date → price }
    await Promise.allSettled(
      codes.map(async (code) => {
        try {
          const { data } = await getStockHistory(code, 180)  // 至少30天，后端最大720
          const bars = data?.bars || []
          priceMap[code] = {}
          for (const b of bars) {
            priceMap[code][b.date] = b.close
          }
        } catch {
          priceMap[code] = {}
        }
      })
    )

    // 4. 按 FIFO 模拟持仓，按日期计算市值
    const equity = []
    for (const date of dates) {
      // 截取该日期之前的交易（FIFO累计）
      const txs = trades.value
        .filter(t => t.trade_date <= date)
        .sort((a, b) => a.trade_date.localeCompare(b.trade_date) || (a.id - b.id))

      const pos = {}   // code → { qty, cost }
      for (const t of txs) {
        if (!pos[t.code]) pos[t.code] = { qty: 0, cost: 0 }
        if (t.trade_type === 'buy') {
          pos[t.code].qty += t.quantity
          pos[t.code].cost += t.price * t.quantity + (t.fee || 0)
        } else {
          if (pos[t.code].qty > 0) {
            const ratio = Math.min(t.quantity / pos[t.code].qty, 1)
            pos[t.code].cost -= pos[t.code].cost * ratio
            pos[t.code].qty -= t.quantity
          }
        }
      }

      let totalVal = 0
      for (const [code, p] of Object.entries(pos)) {
        if (p.qty <= 0) continue
        const price = priceMap[code]?.[date]
        if (price) {
          totalVal += p.qty * price
        } else {
          // 没有历史价格，用成本价（粗估）
          const cp = p.qty > 0 ? p.cost / p.qty : 0
          totalVal += p.qty * cp
        }
      }
      equity.push({ date, value: Math.round(totalVal * 100) / 100 })
    }

    equityData.value = equity

    await nextTick()
    renderEquityChart()
  } catch (e) {
    console.error('收益曲线计算失败', e)
  } finally {
    equityLoading.value = false
  }
}

function renderEquityChart() {
  if (!equityChartRef.value || equityData.value.length === 0) return
  if (!equityChartInst) {
    equityChartInst = echarts.init(equityChartRef.value)
  }

  const dates = equityData.value.map(d => d.date.slice(5))   // MM-DD
  const values = equityData.value.map(d => d.value)
  const first = values[0] || 0
  const last = values[values.length - 1] || 0
  const color = last >= first ? '#ef232a' : '#14b143'
  const costLine = Math.round(buyAmount.value * 100) / 100

  equityChartInst.setOption({
    tooltip: {
      trigger: 'axis',
      formatter(p) {
        const marketVal = p.find(x => x.seriesIndex === 0)?.value || 0
        const costLabel = p.find(x => x.seriesName === '成本线')
        const diff = marketVal - costLine
        const diffStr = diff >= 0
          ? `<span style="color:#ef232a">+¥${Math.abs(diff).toLocaleString()}</span>`
          : `<span style="color:#14b143">-¥${Math.abs(diff).toLocaleString()}</span>`
        return `${p[0].name}<br/>市值: <b>¥${marketVal.toLocaleString()}</b><br/>成本: ¥${costLine.toLocaleString()}<br/>相对成本: ${diffStr}`
      },
      confine: false, position: 'top',
    },
    legend: { show: true, top: 4, right: 20, itemWidth: 14, itemHeight: 2, textStyle: { fontSize: 11, color: '#999' } },
    grid: { top: 36, right: 20, bottom: 50, left: 70 },
    xAxis: {
      type: 'category', data: dates, axisLabel: { fontSize: 11, color: '#999' },
      axisLine: { lineStyle: { color: '#eee' } }, axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: Math.max(...values, costLine) * 1.05,  // 包含成本线，留 5% 边距
      axisLabel: {
        fontSize: 11, color: '#999',
        formatter: v => v >= 10000 ? (v / 10000).toFixed(1) + 'w' : v.toFixed(0),
      },
      splitLine: { lineStyle: { color: '#f5f5f5' } },
    },
    series: [
      {
        name: '市值',
        type: 'line', data: values,
        smooth: true, symbol: 'circle', symbolSize: 4,
        lineStyle: { color, width: 2 },
        itemStyle: { color },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: color + '33' },
            { offset: 1, color: color + '05' },
          ]),
        },
      },
      {
        name: '成本线',
        type: 'line',
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: '#f5a623', type: 'dashed', width: 1.5 },
          label: {
            formatter: `成本 ¥${costLine >= 10000 ? (costLine / 10000).toFixed(1) + 'w' : costLine.toFixed(0)}`,
            position: 'insideEndTop',
            fontSize: 11, color: '#f5a623',
          },
          data: [{ yAxis: costLine }],
        },
        data: [],
      },
    ],
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 18, bottom: 2,
        borderColor: 'transparent', fillerColor: '#e0e0e0',
        handleStyle: { color: color }, textStyle: { color: '#999', fontSize: 11 } },
    ],
  }, true)
  // 强制 resize 两次以确保弹窗内正确渲染
  setTimeout(() => equityChartInst?.resize(), 50)
  setTimeout(() => equityChartInst?.resize(), 300)
}

// ════════════════════════════════════════════════════════════════
//  饼图渲染
// ════════════════════════════════════════════════════════════════
function renderPieCharts() {
  renderStockPie()
  renderFundPie()
}

function renderStockPie() {
  if (!stockPieRef.value || stockPieData.value.length === 0) return
  if (!stockPieChart) stockPieChart = echarts.init(stockPieRef.value)
  const data = stockPieData.value
  const total = data.reduce((s, d) => s + d.value, 0)
  stockPieChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: p => `${p.name}<br/>¥${p.value.toLocaleString()} (${p.percent.toFixed(1)}%)`,
    },
    legend: { bottom: 0, type: 'scroll', textStyle: { fontSize: 11, color: '#666' } },
    series: [{
      type: 'pie', radius: ['38%', '68%'], center: ['50%', '45%'],
      label: { formatter: '{b}: {d}%', fontSize: 11, color: '#555' },
      labelLine: { show: true, lineStyle: { color: '#ccc' } },
      data,
      itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
      emphasis: { itemStyle: { shadowBlur: 8, shadowOffsetX: 2, shadowColor: 'rgba(0,0,0,0.2)' } },
    }],
  }, true)
}

function renderFundPie() {
  if (!fundPieRef.value || fundPieData.value.length === 0) return
  if (!fundPieChart) fundPieChart = echarts.init(fundPieRef.value)
  const data = fundPieData.value
  fundPieChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: p => `${p.name}<br/>¥${p.value.toLocaleString()} (${p.percent.toFixed(1)}%)`,
    },
    legend: { bottom: 0, type: 'scroll', textStyle: { fontSize: 11, color: '#666' } },
    series: [{
      type: 'pie', radius: ['38%', '68%'], center: ['50%', '45%'],
      label: { formatter: '{b}: {d}%', fontSize: 11, color: '#555' },
      labelLine: { show: true, lineStyle: { color: '#ccc' } },
      data,
      itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
      emphasis: { itemStyle: { shadowBlur: 8, shadowOffsetX: 2, shadowColor: 'rgba(0,0,0,0.2)' } },
    }],
  }, true)
}

// 监听数据变化自动重绘
watch([stockPieData, fundPieData], () => { nextTick(renderPieCharts) }, { deep: true })
watch(holdings, () => { nextTick(renderPieCharts) }, { deep: true })
// 收益曲线：equityData 变化后重绘（修复 v-else 重建 DOM 后初次图表为空）
watch(equityData, () => { nextTick(renderEquityChart) }, { deep: true })
// 收益曲线：弹窗打开时重绘（由 @opened 事件触发，此处 watch 作为兜底）
watch(() => equityDialog.visible, (v) => { if (v) nextTick(renderEquityChart) })

// 月度交易点状图：弹窗打开或交易数据变化时重绘
watch([monthlyBuy, monthlySell, () => monthlyDialog.visible], () => {
  if (monthlyDialog.visible) nextTick(renderMonthlyChart)
}, { deep: true })

function openMonthlyChart() {
  monthlyDialog.visible = true
}

watch(() => monthlyDialog.visible, (v) => {
  if (!v && monthlyChart) {
    // 关闭时清空 ECharts 实例避免内存泄露
    monthlyChart.dispose()
    monthlyChart = null
  }
})

// ════════════════════════════════════════════════════════════════
//  持仓收益曲线（点击代码/名称时打开）
// ════════════════════════════════════════════════════════════════
async function openHoldingChart(row) {
  // 如果是「关联指数」按钮点击触发的，不要打开
  if (!row || !row.code) return
  holdingChart.value = {
    visible: true,
    loading: true,
    title: `${row.name || row.code}（${row.code}） 累计收益曲线`,
    data: [],
    cost: 0,
    lastVal: 0,
    pct: 0,
  }
  // 等 DOM 出现（弹窗会有 nextTick）
  await nextTick()

  try {
    // 1. 拉历史价格
    const { data } = await getStockHistory(row.code, 180)
    const bars = data?.bars || []
    const priceMap = {}
    for (const b of bars) priceMap[b.date] = b.close

    // 2. 该品种所有交易
    const myTrades = trades.value
      .filter(t => t.code === row.code)
      .sort((a, b) => a.trade_date.localeCompare(b.trade_date) || (a.id - b.id))

    if (myTrades.length === 0) {
      holdingChart.value.loading = false
      return
    }

    // 3. 从首笔买入日到今天，逐日计算持仓成本、市值、收益
    const firstDate = myTrades[0].trade_date
    const today = new Date().toISOString().slice(0, 10)
    // 用 bars 涵盖范围 + 今天
    const allDates = [...new Set([
      ...bars.map(b => b.date),
      ...myTrades.map(t => t.trade_date),
      today,
    ])].sort()

    const series = []
    let posQty = 0, posCost = 0
    let tradeIdx = 0  // 指向已处理的下一笔交易
    for (const date of allDates) {
      // 处理所有交易日期 <= 当前日期 的交易
      while (tradeIdx < myTrades.length && myTrades[tradeIdx].trade_date <= date) {
        const t = myTrades[tradeIdx]
        if (t.trade_type === 'buy') {
          posQty += t.quantity
          posCost += t.price * t.quantity + (t.fee || 0)
        } else {
          if (posQty > 0) {
            const sellQty = Math.min(t.quantity, posQty)
            const ratio = sellQty / posQty
            posCost -= posCost * ratio
            posQty -= sellQty
          }
        }
        tradeIdx++
      }

      if (posQty <= 0) continue
      if (date < firstDate) continue  // 尚未有持仓

      const price = priceMap[date]
      if (!price) continue
      const marketVal = posQty * price
      const pnl = marketVal - posCost
      const pnlPct = posCost > 0 ? (pnl / posCost) * 100 : 0
      series.push({
        date,
        qty: posQty,
        cost: Math.round(posCost * 100) / 100,
        price: Math.round(price * 10000) / 10000,
        marketVal: Math.round(marketVal * 100) / 100,
        pnl: Math.round(pnl * 100) / 100,
        pnlPct: Math.round(pnlPct * 100) / 100,
      })
    }
    // series 中已经过虑了首笔买入前的日期
    const last = series[series.length - 1]
    holdingChart.value.data = series
    holdingChart.value.cost = last ? last.cost : 0
    holdingChart.value.lastVal = last ? last.marketVal : 0
    holdingChart.value.pct = last && last.cost > 0
      ? ((last.marketVal - last.cost) / last.cost) * 100
      : 0
  } catch (e) {
    console.error('持仓收益曲线计算失败', e)
    ElMessage.error('收益曲线计算失败：' + (e?.message || e))
  } finally {
    holdingChart.value.loading = false
    await nextTick()
    renderHoldingChart()
  }
}

function renderHoldingChart() {
  if (!holdingChartRef.value || holdingChart.value.data.length === 0) return
  if (!holdingChartInst) holdingChartInst = echarts.init(holdingChartRef.value)
  const arr = holdingChart.value.data
  const dates = arr.map(d => d.date.slice(5))
  const vals = arr.map(d => Math.round(d.marketVal * 100) / 100)
  const costs = arr.map(d => Math.round(d.cost * 100) / 100)
  const pnls = arr.map(d => Math.round(d.pnl * 100) / 100)
  const last = arr[arr.length - 1]
  const pnlColor = last && last.pnl >= 0 ? '#ef232a' : '#14b143'

  holdingChartInst.setOption({
    tooltip: {
      trigger: 'axis',
      formatter(p) {
        const idx = p[0].dataIndex
        const d = arr[idx]
        return `<b>${d.date}</b><br/>` +
          `持仓: ${d.qty} 份<br/>` +
          `价格: ¥${d.price}<br/>` +
          `成本: ¥${d.cost.toLocaleString()}<br/>` +
          `市值: ¥${d.marketVal.toLocaleString()}<br/>` +
          `浮盈: <b style="color:${d.pnl>=0?'#ef232a':'#14b143'}">${d.pnl>=0?'+':''}¥${d.pnl.toLocaleString()} (${d.pnlPct>=0?'+':''}${d.pnlPct.toFixed(2)}%)</b>`
      },
    },
    legend: { top: 0, textStyle: { fontSize: 12 }, data: ['市值', '成本', '浮盈'] },
    grid: { top: 30, right: 20, bottom: 30, left: 70 },
    xAxis: {
      type: 'category', data: dates,
      axisLabel: { fontSize: 11, color: '#999' },
      axisLine: { lineStyle: { color: '#eee' } }, axisTick: { show: false },
    },
    yAxis: [
      {
        type: 'value', name: '金额', position: 'left',
        axisLabel: { fontSize: 11, color: '#999', formatter: v => v >= 10000 ? (v/10000).toFixed(1)+'w' : v.toFixed(0) },
        splitLine: { lineStyle: { color: '#f5f5f5' } },
      },
      {
        type: 'value', name: '浮盈(元)', position: 'right',
        axisLabel: { fontSize: 11, color: '#999', formatter: v => v >= 10000 ? (v/10000).toFixed(1)+'w' : v.toFixed(0) },
        splitLine: { show: false },
      },
    ],
    series: [
      { name: '成本', type: 'line', data: costs, smooth: true, showSymbol: false, lineStyle: { color: '#888', width: 1.5, type: 'dashed' }, itemStyle: { color: '#888' } },
      { name: '市值', type: 'line', data: vals, smooth: true, symbol: 'circle', symbolSize: 4, lineStyle: { color: '#1976d2', width: 2 }, itemStyle: { color: '#1976d2' } },
      {
        name: '浮盈', type: 'line', yAxisIndex: 1, data: pnls, smooth: true, showSymbol: false,
        lineStyle: { color: pnlColor, width: 2 },
        itemStyle: { color: pnlColor },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: pnlColor + '33' },
            { offset: 1, color: pnlColor + '05' },
          ]),
        },
      },
    ],
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 18, bottom: 2, borderColor: 'transparent', fillerColor: '#e0e0e0', textStyle: { color: '#999', fontSize: 11 } },
    ],
  }, true)
}

function closeHoldingChart() {
  if (holdingChartInst) {
    holdingChartInst.dispose()
    holdingChartInst = null
  }
}

function renderMonthlyChart() {
  if (!monthlyChartRef.value) return
  if (!monthlyChart) monthlyChart = echarts.init(monthlyChartRef.value)
  const months = Array.from({ length: 12 }, (_, i) => `${i + 1}月`)
  const buy = monthlyBuy.value
  const sell = monthlySell.value
  const maxVal = Math.max(...buy, ...sell, 1)

  // 每个月只一个点：买入点 (红) + 卖出点 (绿)，y = 笔数
  // 点大小随笔数变化，最高月最大
  const sizeFor = (n) => (n === 0 ? 0 : 14 + Math.min(20, n * 4))
  const buyPts = buy.map((c, i) => c > 0 ? { value: [months[i], c], _n: c } : null).filter(Boolean)
  const sellPts = sell.map((c, i) => c > 0 ? { value: [months[i], c], _n: c } : null).filter(Boolean)

  monthlyChart.setOption({
    tooltip: {
      trigger: 'item',
      triggerOn: 'mousemove',
      confine: false,        // 允许超出图表区
      position: 'top',       // 始终在点上方浮动
      backgroundColor: 'rgba(50, 50, 50, 0.92)',
      borderWidth: 0,
      textStyle: { color: '#fff', fontSize: 12 },
      padding: [6, 10],
      formatter(p) {
        const n = p.data?._n ?? 0
        return `${p.name}<br/><b>${p.seriesName}</b>：${n} 笔`
      },
    },
    legend: { show: false },
    grid: { top: 20, right: 16, bottom: 28, left: 36 },
    xAxis: {
      type: 'category', data: months,
      axisLabel: { fontSize: 11, color: '#888' },
      splitLine: { show: false },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#eee' } },
    },
    yAxis: {
      type: 'value', name: '笔数', min: 0,
      axisLabel: { fontSize: 11, color: '#888' },
      splitLine: { lineStyle: { color: '#f5f5f5' } },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        name: '买入', type: 'scatter',
        data: buyPts, symbolSize: d => sizeFor(d._n),
        itemStyle: { color: '#ef232a', opacity: 0.85, borderColor: '#fff', borderWidth: 1 },
        emphasis: { itemStyle: { color: '#ef232a', opacity: 1, borderColor: '#fff', borderWidth: 2 } },
        label: {
          show: true, position: 'top', fontSize: 10, color: '#ef232a', fontWeight: 600,
          formatter(d) { return d.data._n > 0 ? d.data._n : '' },
        },
        z: 3,
      },
      {
        name: '卖出', type: 'scatter',
        data: sellPts, symbolSize: d => sizeFor(d._n),
        itemStyle: { color: '#14b143', opacity: 0.85, borderColor: '#fff', borderWidth: 1 },
        emphasis: { itemStyle: { color: '#14b143', opacity: 1, borderColor: '#fff', borderWidth: 2 } },
        label: {
          show: true, position: 'top', fontSize: 10, color: '#14b143', fontWeight: 600,
          formatter(d) { return d.data._n > 0 ? d.data._n : '' },
        },
        z: 3,
      },
    ],
  }, true)
}

// ─── 某品种历史交易记录 ────────────────────────────────────────────
function openTradeHistoryDialog(row) {
  const rows = trades.value
    .filter(t => t.code === row.code)
    .sort((a, b) => b.trade_date.localeCompare(a.trade_date) || (b.id - a.id))
    .map(t => ({ ...t, isFund: row.isFund }))
  let buyTotal = 0, sellTotal = 0
  for (const t of rows) {
    if (t.trade_type === 'buy') buyTotal += t.price * t.quantity + (t.fee || 0)
    else sellTotal += t.price * t.quantity - (t.fee || 0)
  }
  tradeHistory.value = {
    visible: true,
    title: `${row.name || row.code}（${row.code}） 交易记录 · 共 ${rows.length} 笔`,
    rows,
    buyTotal,
    sellTotal,
    netTotal: buyTotal - sellTotal,
  }
}

// ─── 清仓品种交易记录 ────────────────────────────────────────────
function openClosedTradeHistory(row) {
  const rows = trades.value
    .filter(t => t.code === row.code)
    .sort((a, b) => b.trade_date.localeCompare(a.trade_date) || (b.id - a.id))
    .map(t => ({ ...t, isFund: row.isFund }))
  let buyTotal = 0, sellTotal = 0
  for (const t of rows) {
    if (t.trade_type === 'buy') buyTotal += t.price * t.quantity + (t.fee || 0)
    else sellTotal += t.price * t.quantity - (t.fee || 0)
  }
  tradeHistory.value = {
    visible: true,
    title: `${row.name || row.code}（${row.code}） 清仓交易记录 · 共 ${rows.length} 笔`,
    rows,
    buyTotal,
    sellTotal,
    netTotal: buyTotal - sellTotal,
  }
}

function closeTradeHistory() {
  // 不需要 dispose，但清一下数据防占用
  tradeHistory.value.rows = []
}

// 从交易历史弹窗中删除单条交易（重新计算汇总 + 刷新主表格）
async function removeFromHistory(row) {
  const typeText = row.trade_type === 'buy' ? '买入' : '卖出'
  try {
    await ElMessageBox.confirm(
      `确认删除 ${row.name} ${row.trade_date} 的${typeText}记录？\n价格：${row.price} × ${row.quantity}`,
      '删除交易',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await deleteTrade(row.id)
    ElMessage.success('已删除')
    // 从弹窗数据中移除该行
    tradeHistory.value.rows = tradeHistory.value.rows.filter(r => r.id !== row.id)
    // 重新计算总金额
    let buyTotal = 0, sellTotal = 0
    for (const t of tradeHistory.value.rows) {
      if (t.trade_type === 'buy') buyTotal += t.price * t.quantity + (t.fee || 0)
      else sellTotal += t.price * t.quantity - (t.fee || 0)
    }
    tradeHistory.value.buyTotal = buyTotal
    tradeHistory.value.sellTotal = sellTotal
    tradeHistory.value.netTotal = buyTotal - sellTotal
    tradeHistory.value.title = `${row.name || row.code}（${row.code}） 交易记录 · 共 ${tradeHistory.value.rows.length} 笔`
    // 刷新主交易表 + 持仓 + 月度点状图
    await loadTrades()
  } catch (e) {
    console.error('删除失败', e)
    const detail = e.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : (e.message || '未知错误')
    ElMessage.error('删除失败：' + msg)
  }
}

function fmt(n) {
  return Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function fmtQty(qty, isFund) {
  if (!isFund) return qty.toLocaleString('zh-CN') + ' 股'
  if (qty >= 10000) return (qty / 10000).toFixed(2) + ' 万份'
  return qty.toLocaleString('zh-CN') + ' 份'
}

function fmtPrice(p, isFund) {
  if (!p) return '—'
  return isFund ? p.toFixed(4) : p.toFixed(2)
}

function fmtPct(pct) {
  if (pct == null || isNaN(pct)) return '—'
  const sign = pct >= 0 ? '+' : ''
  return sign + pct.toFixed(2) + '%'
}

function fmtPctClass(pct) {
  if (pct == null || isNaN(pct)) return ''
  return pct >= 0 ? 'up' : 'down'
}

async function loadTrades() {
  try {
    const { data } = await getTrades()
    trades.value = data || []
    await loadQuotes()
  } catch (e) {
    console.error('加载交易记录失败', e)
    ElMessage.error('加载交易记录失败')
  }
}

async function loadWatchlist() {
  try {
    const { data } = await getWatchlist()
    watchlist.value = data || []
  } catch (e) {
    watchlist.value = []
  }
}

function openAdd() {
  pickFromWatch.value = ''
  dialogVisible.value = true
}

function onPickWatch(code) {
  const w = watchlist.value.find(x => x.code === code)
  if (w) {
    form.value.code = w.code
    form.value.name = w.name
  }
}

function resetForm() {
  form.value = { code: '', name: '', trade_type: 'buy', trade_date: '', price: 0.01, quantity: 100, amountInput: 10000, fee: 0, notes: '' }
  pickFromWatch.value = ''
  priceHint.value = ''
  qtyMode.value = 'qty'
  // 关闭弹窗时同时重置批量状态
  batchMode.value = false
  batchRows.value = []
  batchCsvText.value = ''
}

async function submit() {
  if (!canSubmit.value) return
  try {
    // 按金额模式：直接用 amountInput / price 算出数量
    const rawQty = qtyMode.value === 'amt'
      ? calcQtyVal(form.value.amountInput, form.value.price)
      : Number(form.value.quantity)
    // quantity 统一取整（基金/股票均不支持小数份额）
    const quantity = Math.round(rawQty)

    // 卖出校验：检查持仓是否足够
    if (form.value.trade_type === 'sell') {
      const currentQty = getCurrentHoldingQty(form.value.code)
      if (quantity > currentQty) {
        ElMessage.error(`卖出数量 (${quantity}) 超过当前持仓 (${currentQty})，无法提交`)
        return
      }
    }

    const payload = {
      code: form.value.code,
      name: form.value.name,
      trade_type: form.value.trade_type,
      trade_date: form.value.trade_date,
      price: form.value.price,
      quantity,
      fee: form.value.fee ?? 0,
      notes: form.value.notes ?? '',
    }
    console.log('[submit] payload:', JSON.stringify(payload))
    await addTrade(payload)
    ElMessage.success('已保存')
    dialogVisible.value = false
    await loadTrades()
  } catch (e) {
    console.error('保存失败', e)
    const detail = e.response?.data?.detail
    const msg = Array.isArray(detail) ? detail.map(d => `${d.loc?.join('.')}: ${d.msg}`).join('；') : (detail || e.message)
    ElMessage.error('保存失败：' + msg)
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除 ${row.name} ${row.trade_date} 的这笔交易？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteTrade(row.id)
    ElMessage.success('已删除')
    await loadTrades()
  } catch (e) {
    console.error('删除失败', e)
    ElMessage.error('删除失败')
  }
}

// ── 关联指数 ──
const availableIndices = ref([])
const linkDialog = ref({
  visible: false,
  id: null, code: '', name: '',
  currentIndexCode: null,
})

async function loadAvailableIndices() {
  try {
    const { data } = await getAvailableIndices()
    availableIndices.value = data
  } catch { availableIndices.value = [] }
}

async function openLinkDialog(row, sig) {
  linkDialog.value = {
    visible: true,
    id: row.id,
    code: row.code,
    name: row.name,
    currentIndexCode: sig?.index_code || null,
  }
  if (!availableIndices.value.length) await loadAvailableIndices()
}

async function doLink(idx) {
  try {
    await linkIndex(linkDialog.value.id, idx.code)
    ElMessage.success(`已关联「${idx.name}」`)
    linkDialog.value.visible = false
    loadSignals()
  } catch (e) {
    ElMessage.error('关联失败：' + (e.message || e))
  }
}

async function doUnlink() {
  if (!confirm(`取消「${linkDialog.value.name}」的指数关联？`)) return
  try {
    await linkIndex(linkDialog.value.id, null)
    ElMessage.success('已取消关联')
    linkDialog.value.visible = false
    loadSignals()
  } catch { ElMessage.error('操作失败') }
}

function formatUpdated(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  const now = new Date()
  const diffMs = now - d
  const diffDays = Math.floor(diffMs / 86400000)
  if (diffDays === 0) return '今日'
  if (diffDays === 1) return '昨日'
  if (diffDays < 30) return `${diffDays}天前`
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

onMounted(async () => {
  await loadTrades()
  loadWatchlist()
  loadSignals()
  loadAvailableIndices()
  loadEquityCurve()

  // ECharts 响应式
  const handleResize = () => {
    equityChartInst?.resize()
    dividendChartInst?.resize()
    stockPieChart?.resize()
    fundPieChart?.resize()
    monthlyChart?.resize()
  }
  window.addEventListener('resize', handleResize)

  onUnmounted(() => {
    dividendChartInst?.dispose()
  })
})
</script>

<style scoped>
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.summary { margin-bottom: 16px; }
.clickable-card { cursor: pointer; transition: background 0.15s; }
.clickable-card:hover { background: #f5f9ff; }
.sum-label { font-size: 13px; color: #888; margin-bottom: 6px; }
.sum-value { font-size: 24px; font-weight: 700; color: #1a1a2e; }
.sum-value.up { color: #ef232a; }
.sum-value.down { color: #14b143; }
.sum-sub { font-size: 12px; color: #aaa; margin-top: 4px; }
.block { margin-bottom: 16px; }
.block-title { font-weight: 600; color: #1a1a2e; }
.block-tip { font-size: 12px; color: #aaa; margin-left: 10px; }
.price-hint { font-size: 12px; color: #909399; margin-top: 4px; line-height: 1; }
.calc-hint { font-size: 12px; color: #909399; margin-top: 4px; line-height: 1; }
.up { color: #ef232a; }
.down { color: #14b143; }
.pl-amount, .pl-pct { font-weight: 600; }

/* 信号徽章 */
.sig-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 20px;
}
.sig-extreme_low  { background: #e3f2fd; color: #1565c0; }
.sig-low          { background: #e8f5e9; color: #2e7d32; }
.sig-normal       { background: #fff8e1; color: #f57f17; }
.sig-high         { background: #fff3e0; color: #e65100; }
.sig-extreme_high { background: #fce4ec; color: #c62828; }
.sig-unknown      { background: #f5f5f5; color: #9e9e9e; }

/* 信号单元格：徽章 + 更新时间 */
.sig-cell { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.sig-cell.has-manual { background: #e3f2fd; padding: 4px 6px; border-radius: 4px; }
.sig-updated { font-size: 10px; color: #999; line-height: 1.2; }
.sig-updated.muted { color: #bbb; }
.sig-manual-dot {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  color: #ffffff;
  background: #1976d2;
  border-radius: 3px;
  padding: 0 4px;
  margin-left: 4px;
  vertical-align: middle;
  font-family: monospace;
}

/* 关联指数弹窗 */
.link-list {
  max-height: 400px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.link-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border: 1.5px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
}
.link-item:hover { border-color: #1976d2; background: #f5f9ff; }
.link-item.active { border-color: #1976d2; background: #e3f2fd; }
.link-item-left  { display: flex; align-items: center; gap: 8px; }
.link-idx-name   { font-size: 14px; font-weight: 600; color: #1a1a2e; }
.link-idx-code   { font-size: 11px; color: #999; font-family: monospace; }
.link-custom-tag { font-size: 10px; background: #fff3e0; color: #e65100; border-radius: 3px; padding: 0 5px; }
.link-item-right { font-size: 12px; }
.link-pct-ok    { color: #2e7d32; }
.link-pct-empty { color: #999; }

/* 小spinner */
.spinner-sm {
  display: inline-block;
  width: 16px; height: 16px;
  border: 2px solid #e0e0e0;
  border-top-color: #1976d2;
  border-radius: 50%;
  animation: spin-sm 0.7s linear infinite;
  margin-right: 8px;
  vertical-align: middle;
}
@keyframes spin-sm {
  to { transform: rotate(360deg); }

/* 批量新增模式 */
.mode-toggle-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 6px;
  margin-bottom: 14px;
}
.mode-hint {
  font-size: 12px;
  color: #909399;
}
/* 分红记录弹窗 */
.div-add-bar {
  padding: 10px 12px;
  background: #fff8f8;
  border: 1px solid #fde2e2;
  border-radius: 6px;
  margin-bottom: 4px;
}

.batch-mode {
  margin-top: 4px;
}
.batch-csv {
  background: #fafbfc;
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}
.batch-csv-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 13px;
}
.batch-rows {
  max-height: 320px;
  overflow-y: auto;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  background: #fff;
}
.batch-row {
  display: grid;
  grid-template-columns: 32px 90px 124px 100px 100px 84px 84px 1fr 80px;
  gap: 8px;
  align-items: center;
  padding: 6px 8px;
  border-bottom: 1px solid #f0f0f0;
}
.batch-row:last-child { border-bottom: none; }
.batch-row.batch-head {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  background: #f5f7fa;
  position: sticky;
  top: 0;
  z-index: 1;
}
.batch-row .c-num {
  font-size: 12px;
  color: #aaa;
  text-align: center;
}
.batch-footer {
  margin-top: 10px;
  display: flex;
  align-items: center;
}
.batch-row.is-invalid {
  background: #fef0f0;
}

/* 月度交易点状图 header & 图例 */
.monthly-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.monthly-legend {
  margin-left: auto;
  font-size: 12px;
  color: #666;
  display: flex;
  align-items: center;
  gap: 6px;
}
.ml-dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1px solid #fff;
  box-shadow: 0 0 0 1px rgba(0,0,0,0.05);
}
.ml-dot-buy { background: #ef232a; }
.ml-dot-sell { background: #14b143; }

/* 可点击链接样式（代码/名称） */
.link-name,
a.link-name {
  color: #1976d2 !important;
  cursor: pointer;
  text-decoration: none !important;
  text-decoration-line: none !important;
  border-bottom: 1px dashed #1976d2;
  padding-bottom: 1px;
  transition: all 0.15s;
  display: inline-block;
  font-weight: 500;
}
.link-name:hover,
a.link-name:hover {
  color: #0d47a1 !important;
  border-bottom: 1px solid #0d47a1;
  background: #f0f7ff;
  padding: 0 4px;
  border-radius: 3px;
}

/* 持仓收益曲线弹窗 */
.hc-stat {
  background: #f7f8fa;
  border-radius: 8px;
  padding: 12px 14px;
}
.hc-stat-label { font-size: 12px; color: #888; margin-bottom: 6px; }
.hc-stat-value { font-size: 18px; font-weight: 700; color: #1a1a2e; }
.hc-stat-value.up { color: #ef232a; }
.hc-stat-value.down { color: #14b143; }
}
</style>
