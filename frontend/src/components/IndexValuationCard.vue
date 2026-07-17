<template>
  <div class="val-card" :class="'band-' + band">
    <div class="val-name">{{ name }}</div>
    <div class="val-metrics">
      <div class="val-pairs">
        <!-- PE -->
        <div class="val-pair">
          <span class="val-label">PE</span>
          <span class="val-num">{{ peStr }}</span>
          <span v-if="pePct != null" class="val-pct" :class="pctClass(pePct)">
            {{ pePct }}%
          </span>
          <span v-else class="val-pct neutral">—</span>
        </div>
        <!-- PB -->
        <div class="val-pair">
          <span class="val-label">PB</span>
          <span class="val-num">{{ pbStr }}</span>
          <span v-if="pbPct != null" class="val-pct" :class="pctClass(pbPct)">
            {{ pbPct }}%
          </span>
          <span v-else class="val-pct neutral">—</span>
        </div>
      </div>
      <div class="val-badge" :class="'badge-' + band">
        {{ bandLabel }}
      </div>
    </div>
    <div class="val-bottom">
      <div class="val-price">
        <span class="price">{{ priceStr }}</span>
        <span class="pct" :class="pct >= 0 ? 'up' : 'down'">
          {{ pct >= 0 ? '+' : '' }}{{ pctStr }}%
        </span>
      </div>
      <div v-if="historyDays > 0" class="val-days">
        {{ historyDays >= 2000 ? '10年数据' :
           historyDays >= 30  ? `历史${historyDays}天` :
           `收集中(${historyDays}天)` }}
      </div>
      <div v-if="dataSource === 'csi_10y'" class="val-source csi">CSI</div>
      <div v-if="dataSource === 'manual'" class="val-source manual">手动</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  code:       { type: String,  required: true },
  name:       { type: String,  required: true },
  price:      { type: Number,  default: null },
  pct:        { type: Number,  default: null },
  pe:         { type: Number,  default: null },
  pb:         { type: Number,  default: null },
  pePct:      { type: Number,  default: null },   // PE历史分位 0~100
  pbPct:      { type: Number,  default: null },    // PB历史分位 0~100
  historyDays:{ type: Number,  default: 0 },       // 快照历史天数
  dataSource: { type: String,  default: 'none' },     // csi_10y|manual|local_snapshot|tencent|none
  band:       { type: String,  default: 'unknown' },
})

const fmt = (v, decimals = 2) =>
  v != null ? v.toFixed(decimals) : '—'

const priceStr = computed(() => fmt(props.price, 2))
const pctStr   = computed(() => fmt(props.pct, 2))
const peStr    = computed(() => fmt(props.pe, 2))
const pbStr    = computed(() => fmt(props.pb, 2))

const BAND_MAP = {
  extreme_low:  '极度低估',
  low:          '偏低',
  normal:       '适中',
  high:         '偏高',
  extreme_high: '极度高估',
  unknown:      '数据不足',
}
const bandLabel = computed(() => BAND_MAP[props.band] ?? '未知')

// 分位颜色：低<30 绿，高>70 红，中间黄
const pctClass = (v) => {
  if (v == null) return 'neutral'
  if (v < 30) return 'low'
  if (v > 70) return 'high'
  return 'mid'
}
</script>

<style scoped>
.val-card {
  border-radius: 10px;
  padding: 14px 16px 12px;
  border: 1px solid #e8e8ee;
  background: #fff;
  transition: box-shadow .15s, transform .15s;
  cursor: default;
}
.val-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,.08);
  transform: translateY(-2px);
}

.val-name {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
  font-weight: 500;
}

.val-metrics {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.val-pairs {
  display: flex;
  gap: 14px;
}

.val-pair {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.val-label {
  font-size: 11px;
  color: #999;
}

.val-num {
  font-size: 15px;
  font-weight: 700;
  color: #1a1a2e;
}

/* 历史分位 */
.val-pct {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 8px;
}
.val-pct.low    { background: #e8f5e9; color: #2e7d32; }
.val-pct.mid    { background: #fff8e1; color: #f57f17; }
.val-pct.high   { background: #fce4ec; color: #c62828; }
.val-pct.neutral { background: #f5f5f5; color: #9e9e9e; }

/* 档位徽章 */
.val-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 20px;
  white-space: nowrap;
  flex-shrink: 0;
}

.badge-extreme_low  { background: #e3f2fd; color: #1565c0; }
.badge-low          { background: #e8f5e9; color: #2e7d32; }
.badge-normal       { background: #fff8e1; color: #f57f17; }
.badge-high         { background: #fff3e0; color: #e65100; }
.badge-extreme_high { background: #fce4ec; color: #c62828; }
.badge-unknown      { background: #f5f5f5; color: #9e9e9e; }

.val-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.val-price {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.price {
  font-size: 13px;
  color: #888;
}
.pct {
  font-size: 12px;
  font-weight: 600;
}
.pct.up    { color: #ef232a; }
.pct.down  { color: #14b143; }

.val-days {
  font-size: 11px;
  color: #bbb;
}

.val-source {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 10px;
  margin-left: 6px;
}
.val-source.csi    { background: #ede7f6; color: #6a1b9a; }
.val-source.manual { background: #e3f2fd; color: #1565c0; }
</style>
