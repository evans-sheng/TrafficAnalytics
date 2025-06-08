<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { 
  loadCSVData, 
  processDataByDirection, 
  getLanesFromData, 
  createLaneTimeSeriesData, 
  getChartColors 
} from '../utils/dataLoader.js'
import TopHeader from './TopHeader.vue'

const stats = ref({
  todayTraffic: 0,
  incidents: 3,
  avgSpeed: 45
})


const data170 = ref([])

// 添加选择器数据
const selectedIntersection = ref('intersection-170')
const selectedTimeRange = ref('2025.3.7')
const selectedUnit = ref('1min')

// 交叉口选项
const intersectionOptions = [
  { value: 'intersection-57', label: '交叉口-57' },
  { value: 'intersection-67', label: '交叉口-67' },
  { value: 'intersection-170', label: '交叉口-170' },
  { value: 'intersection-256', label: '交叉口-256' },
  { value: 'intersection-257', label: '交叉口-257' }
]

// 时间选项
const timeRangeOptions = [
  { value: '2025.3.7', label: '2025.3.7' }
]

// 单位选项
const unitOptions = [
  { value: '1min', label: '1分钟' },
  { value: '15min', label: '15分钟' }
]





const chartRef1 = ref(null)
const chartRef2 = ref(null)
const chartRef3 = ref(null)
const chartRef4 = ref(null)
const expandedChartRef = ref(null)
const expandedChart = ref(null)

// 切换图表大小
const toggleChartSize = (chartIndex) => {
  if (expandedChart.value === chartIndex) {
    // 如果当前图表已经是展开状态，则收起
    expandedChart.value = null
  } else {
    // 否则展开当前图表
    expandedChart.value = chartIndex
  }
}

// 加载数据的方法
const loadData = async () => {
  // 从交叉口选择中提取数字
  const intersectionNumber = selectedIntersection.value.split('-')[1]
  
  // 根据单位选择确定文件路径
  const basePath = selectedUnit.value === '1min' ? 'minutes' : 'minutes15'
  const fileName = selectedUnit.value === '1min' 
    ? `${intersectionNumber}minute_lane_flow.csv`
    : `15minute_lane_flow${intersectionNumber}.csv`
  
  const filePath = `${basePath}/${fileName}`
  
  try {
    console.log('Loading file:', filePath) // 添加日志
    // 加载新的数据
    data170.value = await loadCSVData(filePath)
    
    // 按方向分组数据
    const directionData = processDataByDirection(data170.value)
    
    // 更新四张图表
    const directions = ['NW', 'NE', 'SW', 'SE']
    const chartRefs = [chartRef1, chartRef2, chartRef3, chartRef4]
    const titles = ['西北方向 (NW)', '东北方向 (NE)', '西南方向 (SW)', '东南方向 (SE)']
    const colors = getChartColors()
    
    // 如果是展开状态，只渲染展开的图表
    if (expandedChart.value !== null) {
      const expandedIndex = expandedChart.value
      const direction = directions[expandedIndex]
      const data = directionData[direction]
      const chartElement = expandedChartRef.value
      
      if (chartElement) {
        const chart = echarts.init(chartElement)
        
        // 获取该方向的所有车道
        const lanes = getLanesFromData(data)
        
        // 为每个车道创建时间序列数据
        const series = lanes.map((lane, laneIndex) => {
          const laneData = createLaneTimeSeriesData(data, lane)
          
          return {
            name: `车道 ${lane}`,
            type: 'line',
            data: laneData,
            smooth: true,
            lineStyle: { 
              color: colors[laneIndex % colors.length],
              width: 2
            },
            itemStyle: { 
              color: colors[laneIndex % colors.length]
            },
            symbol: 'circle',
            symbolSize: 4
          }
        })
        
        chart.setOption({
          title: {
            text: titles[expandedIndex],
            left: 'center',
            top: 5,
            textStyle: { 
              color: '#333', 
              fontSize: 36,
              fontWeight: 'bold'
            }
          },
          tooltip: { 
            trigger: 'axis',
            backgroundColor: 'rgba(255,255,255,0.95)',
            borderColor: '#cc6600',
            textStyle: { 
              color: '#333',
              fontSize: 24
            },
            formatter: function(params) {
              let result = `时间: ${new Date(params[0].value[0]).toLocaleString()}<br/>`
              params.forEach(param => {
                result += `${param.seriesName}: ${param.value[1]} 辆<br/>`
              })
              return result
            }
          },
          legend: {
            top: 50,
            textStyle: { 
              color: '#333', 
              fontSize: 24
            },
            itemWidth: 30,
            itemHeight: 20
          },
          xAxis: {
            type: 'time',
            axisLabel: { 
              color: '#666',
              fontSize: 24,
              formatter: function(value) {
                return new Date(value).toLocaleTimeString('zh-CN', { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                })
              }
            },
            axisLine: { lineStyle: { color: '#ccc' } }
          },
          yAxis: { 
            type: 'value', 
            axisLabel: { 
              color: '#666', 
              fontSize: 24
            },
            axisLine: { lineStyle: { color: '#ccc' } },
            name: '车辆数',
            nameTextStyle: { 
              color: '#666',
              fontSize: 24
            }
          },
          series: series,
          backgroundColor: 'transparent',
          grid: {
            left: '3%',
            right: '3%',
            bottom: '5%',
            top: '10%',
            containLabel: true
          },
          graphic: [
            {
              type: 'text',
              left: 'center',
              bottom: '0.5%',
              style: {
                text: `车道数: ${lanes.length} | 数据点: ${data.length}`,
                textAlign: 'center',
                fill: '#999',
                fontSize: 20,
                fontWeight: 'bold'
              }
            }
          ]
        })
      }
      return
    }
    
    // 正常状态，渲染所有四个图表
    directions.forEach((direction, index) => {
      const chartElement = chartRefs[index].value
      if (!chartElement) return
      
      const chart = echarts.init(chartElement)
      const data = directionData[direction]
      
      // 获取该方向的所有车道
      const lanes = getLanesFromData(data)
      
      // 为每个车道创建时间序列数据
      const series = lanes.map((lane, laneIndex) => {
        const laneData = createLaneTimeSeriesData(data, lane)
        
        return {
          name: `车道 ${lane}`,
          type: 'line',
          data: laneData,
          smooth: true,
          lineStyle: { 
            color: colors[laneIndex % colors.length],
            width: 2
          },
          itemStyle: { 
            color: colors[laneIndex % colors.length]
          },
          symbol: 'circle',
          symbolSize: 4
        }
      })
      
            chart.setOption({
        title: {
          text: titles[index],
          left: 'center',
          top: 10,
          textStyle: { 
            color: '#333', 
            fontSize: 16,
            fontWeight: 'bold'
          }
        },
        tooltip: { 
          trigger: 'axis',
          backgroundColor: 'rgba(255,255,255,0.95)',
          borderColor: '#cc6600',
          textStyle: { 
            color: '#333',
            fontSize: 12
          },
          formatter: function(params) {
            let result = `时间: ${new Date(params[0].value[0]).toLocaleString()}<br/>`
            params.forEach(param => {
              result += `${param.seriesName}: ${param.value[1]} 辆<br/>`
            })
            return result
          }
        },
        legend: {
          top: 35,
          textStyle: { 
            color: '#333', 
            fontSize: 10
          },
          itemWidth: 15,
          itemHeight: 10
        },
        xAxis: {
          type: 'time',
          axisLabel: { 
            color: '#666',
            fontSize: 10,
            formatter: function(value) {
              return new Date(value).toLocaleTimeString('zh-CN', { 
                hour: '2-digit', 
                minute: '2-digit' 
              })
            }
          },
          axisLine: { lineStyle: { color: '#ccc' } }
        },
        yAxis: { 
          type: 'value', 
          axisLabel: { 
            color: '#666', 
            fontSize: 10
          },
          axisLine: { lineStyle: { color: '#ccc' } },
          name: '车辆数',
          nameTextStyle: { 
            color: '#666',
            fontSize: 10
          }
        },
        series: series,
        backgroundColor: 'transparent',
        grid: {
          left: '10%',
          right: '10%',
          bottom: '20%',
          top: '25%',
          containLabel: true
        },
        graphic: [
          {
            type: 'text',
            left: 'center',
            bottom: '2%',
            style: {
              text: `车道数: ${lanes.length} | 数据点: ${data.length}`,
              textAlign: 'center',
              fill: '#999',
              fontSize: 12
            }
          }
        ]
      })
    })
  } catch (error) {
    console.error('加载数据失败:', error)
  }
}

// 监听选择器变化
watch([selectedIntersection, selectedTimeRange, selectedUnit], () => {
  loadData()
})

// 监听展开状态变化，重新渲染图表
watch(expandedChart, async (newVal, oldVal) => {
  if (newVal !== oldVal) {
    await nextTick()
    setTimeout(() => {
      loadData()
    }, 100)
  }
})

onMounted(async () => {
  await nextTick()
  
  // 延迟加载确保DOM完全渲染
  setTimeout(async () => {
    console.log('开始初始化图表...')
    console.log('Chart refs:', {
      ref1: chartRef1.value,
      ref2: chartRef2.value, 
      ref3: chartRef3.value,
      ref4: chartRef4.value
    })
    
    await loadData()
  }, 200)
  
  // 监听窗口大小变化，自动调整图表大小
  window.addEventListener('resize', () => {
    if (expandedChart.value !== null) {
      // 展开状态
      if (expandedChartRef.value) {
        echarts.getInstanceByDom(expandedChartRef.value)?.resize()
      }
    } else {
      // 正常状态
      [chartRef1, chartRef2, chartRef3, chartRef4].forEach(ref => {
        if (ref.value) {
          echarts.getInstanceByDom(ref.value)?.resize()
        }
      })
    }
  })
})
</script>

<template>
  <div class="dashboard">
    <TopHeader>
      <template #navigation>
        <button class="nav-to-map" @click="$router.push('/map')">地图视图</button>
      </template>
    </TopHeader>

    <!-- 控制区域 -->
    <div class="control-panel">
      <div class="selector-info">
        <div class="selector-group">
          <label class="selector-group label">交叉口:</label>
          <select v-model="selectedIntersection" class="header-select">
            <option v-for="option in intersectionOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>
        <div class="selector-group">
          <label class="selector-group label">日期:</label>
          <select v-model="selectedTimeRange" class="header-select">
            <option v-for="option in timeRangeOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>
        <div class="selector-group">
          <label class="selector-group label">单位:</label>
          <select v-model="selectedUnit" class="header-select">
            <option v-for="option in unitOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>
        <button class="display-btn" @click="loadData">显示</button>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts">
      <!-- 正常显示的四个图表 -->
      <div v-if="expandedChart === null" class="normal-charts-container">
        <div class="chart-row">
          <div 
            ref="chartRef1" 
            class="chart-quarter"
            @dblclick="toggleChartSize(0)"
          ></div>
          <div 
            ref="chartRef2" 
            class="chart-quarter"
            @dblclick="toggleChartSize(1)"
          ></div>
        </div>
        <div class="chart-row">
          <div 
            ref="chartRef3" 
            class="chart-quarter"
            @dblclick="toggleChartSize(2)"
          ></div>
          <div 
            ref="chartRef4" 
            class="chart-quarter"
            @dblclick="toggleChartSize(3)"
          ></div>
        </div>
      </div>
      
      <!-- 展开的图表 -->
      <div v-else class="expanded-chart-container">
        <div 
          ref="expandedChartRef"
          class="chart-quarter expanded"
          @dblclick="toggleChartSize(expandedChart)"
        ></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #fefefe 0%, #fff8f5 50%, #ffeee8 100%);
  color: #333;
  display: flex;
  flex-direction: column;
  padding: 0;
  box-sizing: border-box;
  overflow: hidden;
}



.charts {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  position: relative;
  z-index: 2;
  padding: 12px;
}

.normal-charts-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chart {
  flex: 1;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(200, 150, 100, 0.3);
  border-radius: 12px;
  padding: 12px;
  min-height: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.chart-row {
  display: flex;
  gap: 12px;
  flex: 1;
  min-height: 0;
  position: relative;
}

.chart-quarter {
  flex: 1;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(200, 150, 100, 0.3);
  border-radius: 12px;
  padding: 8px;
  min-height: 0;
  min-width: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  cursor: pointer;
}

.expanded-chart-container {
  width: 100%;
  height: 100%;
  display: flex;
}

.chart-quarter.expanded {
  flex: 1;
  background: rgba(255, 255, 255, 0.98);
  border: 2px solid rgba(200, 150, 100, 0.5);
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  padding: 20px;
  width: 95%;
  height: 95%;
  margin: auto;
  transform: scale(0.95);
}

.control-panel {
  padding: 6px 15px;
  background: transparent;
  position: absolute;
  top: 35px;
  left: 10px;
  z-index: 10;
}

.selector-info {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  white-space: nowrap;
  max-width: 100%;
  justify-content: flex-start;
}

.selector-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.selector-group label {
  font-size: 0.8rem;
  color: #333;
  font-weight: 600;
  white-space: nowrap;
}

.header-select {
  padding: 2px 6px;
  border: 1px solid rgba(200, 150, 100, 0.4);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.9);
  color: #333;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 85px;
}

.header-select:hover {
  border-color: rgba(200, 150, 100, 0.6);
  background: rgba(255, 255, 255, 1);
}

.header-select:focus {
  outline: none;
  border-color: #cc6600;
  box-shadow: 0 0 0 2px rgba(204, 102, 0, 0.2);
}

.display-btn {
  margin-left: 12px;
  padding: 2px 8px;
  background: linear-gradient(135deg, #ff9966, #ff7733);
  border: none;
  border-radius: 4px;
  color: #fff;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.display-btn:hover {
  background: linear-gradient(135deg, #ff7733, #ff5500);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(255, 119, 51, 0.3);
}

.nav-to-map {
  margin-left: 15px;
  padding: 6px 12px;
  background: linear-gradient(135deg, #cc6600, #aa5500);
  border: none;
  border-radius: 4px;
  color: #fff;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.nav-to-map:hover {
  background: linear-gradient(135deg, #aa5500, #884400);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(204, 102, 0, 0.3);
}
</style> 