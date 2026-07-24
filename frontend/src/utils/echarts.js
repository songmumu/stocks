/**
 * ECharts 按需引入配置
 * 只打包实际用到的组件，大幅减少 bundle 体积
 */
import * as echarts from 'echarts/core'

// ── 图表类型 ──────────────────────────────────
import { LineChart, BarChart, PieChart, CandlestickChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkAreaComponent,
  TitleComponent,
  ToolboxComponent,
  VisualMapComponent,
  CalendarComponent,
} from 'echarts/components'

// ── 渲染器 ──────────────────────────────────
// Canvas 渲染器（体积小，首选）
import { CanvasRenderer } from 'echarts/renderers'

// 注册所有需要的组件
echarts.use([
  // 图表
  LineChart,
  BarChart,
  PieChart,
  CandlestickChart,
  // HeatMapChart (日历用 CSS Grid，无需 ECharts 热力图)
  // 组件
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkAreaComponent,
  TitleComponent,
  ToolboxComponent,
  VisualMapComponent,
  CalendarComponent,
  // 渲染器
  CanvasRenderer,
])

export default echarts
