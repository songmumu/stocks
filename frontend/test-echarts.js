// Test ECharts layout with the same config as Dashboard.vue
const { JSDOM } = require('jsdom');
const dom = new JSDOM('<!DOCTYPE html><html><body><div id="chart" style="width:800px;height:460px"></div></body></html>', {
  pretendToBeVisual: true,
});
global.window = dom.window;
global.document = dom.window.document;
global.navigator = dom.window.navigator;
global.HTMLCanvasElement = dom.window.HTMLCanvasElement;
global.HTMLElement = dom.window.HTMLElement;
global.Node = dom.window.Node;
global.Element = dom.window.Element;
global.getComputedStyle = dom.window.getComputedStyle;

// Try-catch wrapper
let echarts;
try {
  echarts = require('echarts');
} catch (e) {
  console.log('Failed to load echarts (probably needs canvas):', e.message);
  process.exit(1);
}

const dates = ["2026-06-01","2026-06-02","2026-06-03","2026-06-04","2026-06-05","2026-06-08","2026-06-09","2026-06-10","2026-06-11","2026-06-12","2026-06-15","2026-06-16","2026-06-17","2026-06-18","2026-06-22","2026-06-23","2026-06-24","2026-06-25","2026-06-26","2026-06-29","2026-06-30","2026-07-01","2026-07-02","2026-07-03","2026-07-06","2026-07-07","2026-07-08","2026-07-09","2026-07-10","2026-07-13"];
const candleData = [[4067.16,4057.74,4045.69,4093.04],[4061.46,4075.1,4032.58,4089.57],[4068.34,4083.97,4059.91,4107.05],[4053.67,4057.78,4043.43,4080.72],[4044.83,4027.74,4015.06,4078.93],[3938.71,3959.34,3927.85,4007.49],[3977.54,4010.03,3955.91,4010.87],[3985.12,3993.23,3963.44,4006.31],[3979.71,3987.01,3958.44,3997.48],[4017.86,4031.51,4008.18,4060.27],[4053.58,4096.47,4051.07,4097.17],[4094.21,4091.89,4077.87,4103.93],[4074.29,4108.08,4073.73,4109.96],[4094.23,4090.48,4080.29,4117.45],[4093.95,4163.1,4070.17,4164.42],[4153.59,4106.25,4085.59,4175.35],[4090.1,4110.81,4075.49,4117.28],[4103.48,4120.28,4093.01,4133.1],[4098.69,4027.26,4007.86,4099.78],[4026.69,4073.9,3992.55,4075.33],[4058.17,4094.4,4052.17,4097.42],[4090.76,4112.45,4087.54,4143.31],[4054.09,4028.9,4019.21,4093.68],[4031.34,4043.64,4027.26,4073.88],[4059.19,4041.24,4005.41,4060.07],[4019.49,3990.24,3971.71,4028.51],[3996.81,3970.88,3967.91,4016.03],[3977.55,4036.59,3938.88,4040.54],[4031.54,3996.16,3995.81,4074.83],[3966.02,3913.79,3900.67,3983.05]];

const chartEl = document.getElementById('chart');
console.log('container size:', chartEl.offsetWidth, 'x', chartEl.offsetHeight);

const chart = echarts.init(chartEl);
chart.setOption({
  tooltip: { trigger: 'axis' },
  grid: [
    { left: 60, right: 50, top: 40, height: '60%' },
    { left: 60, right: 50, top: '76%', height: '14%' },
  ],
  xAxis: [
    { type: 'category', data: dates, gridIndex: 0, boundaryGap: false },
    { type: 'category', data: dates, gridIndex: 1, axisLabel: { show: false } },
  ],
  yAxis: [
    { scale: true, gridIndex: 0, position: 'right' },
    { scale: true, gridIndex: 1, position: 'right' },
  ],
  dataZoom: [],
  series: [
    { type: 'candlestick', data: candleData, itemStyle: { color:'#ef232a', color0:'#14b143' } },
    { type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: candleData.map((_,i)=>100) },
  ],
});

setTimeout(() => {
  const opt = chart.getOption();
  console.log('===== Final chart state =====');
  console.log('dataZoom:', JSON.stringify(opt.dataZoom));
  console.log('xAxis[0] min/max:', opt.xAxis[0].min, '/', opt.xAxis[0].max, '   data len:', opt.xAxis[0].data?.length);
  console.log('xAxis[1] min/max:', opt.xAxis[1].min, '/', opt.xAxis[1].max, '   data len:', opt.xAxis[1].data?.length);
  console.log('series[0] data len:', opt.series[0].data?.length);
}, 1000);
