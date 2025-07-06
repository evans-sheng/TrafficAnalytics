<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { 
  loadCSVData, 
  processDataByDirection, 
  getLanesFromData, 
  createLaneTimeSeriesData, 
  getChartColors,
  loadSupplyDemandData,
  processSupplyDemandByDirection,
  createSupplyDemandTimeSeriesData
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
const selectedChartType = ref('traffic-flow')
const isLoading = ref(false)

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

// 图表类型选项
const chartTypeOptions = [
  { value: 'traffic-flow', label: '流量图' },
  { value: 'supply-demand', label: '供需曲线' }
]

// 动态图表容器管理
const chartContainers = ref([])
const chartInstances = ref([])
const dynamicChartCount = ref(4)

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

// 根据图表数量生成布局类名
const getChartLayoutClass = () => {
  const count = dynamicChartCount.value
  if (count <= 4) {
    return 'layout-2x2'
  } else if (count <= 6) {
    return 'layout-2x3'
  } else if (count <= 8) {
    return 'layout-2x4'
  } else {
    return 'layout-3x3'
  }
}

// 处理显示按钮点击
const handleDisplayClick = async () => {
  if (isLoading.value) return
  
  console.log('开始加载数据...')
  isLoading.value = true
  
  try {
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))
    await loadData()
    console.log('数据加载完成')
  } catch (error) {
    console.error('数据加载失败:', error)
  } finally {
    isLoading.value = false
  }
}

// 清空所有图表容器 - 强化版
const clearAllCharts = () => {
  const chartRefs = [chartRef1, chartRef2, chartRef3, chartRef4]
  
  console.log('正在清空所有图表实例...')
  
  // 清理固定的图表容器
  chartRefs.forEach((ref, index) => {
    if (ref.value) {
      const chart = echarts.getInstanceByDom(ref.value)
      if (chart) {
        chart.dispose()
        console.log(`已清空图表 ${index + 1}`)
      }
      ref.value.innerHTML = '' // 清空DOM
    }
  })
  
  // 清理动态图表容器
  chartInstances.value.forEach((chart, index) => {
    if (chart) {
      chart.dispose()
      console.log(`已清空动态图表 ${index + 1}`)
    }
  })
  chartInstances.value = []
  
  // 强制垃圾回收
  if (window.gc) {
    window.gc()
  }
  
  console.log('所有图表清空完成')
}

// 加载数据的方法
const loadData = async () => {
  try {
    if (selectedChartType.value === 'traffic-flow') {
      await loadTrafficFlowData()
    } else if (selectedChartType.value === 'supply-demand') {
      await loadSupplyDemandChartData()
    }
  } catch (error) {
    console.error('加载数据失败:', error)
    isLoading.value = false
  }
}

// 加载流量图数据
const loadTrafficFlowData = async () => {
  // 从交叉口选择中提取数字
  const intersectionNumber = selectedIntersection.value.split('-')[1]
  
  // 根据单位选择确定文件路径
  const basePath = selectedUnit.value === '1min' ? 'minutes' : 'minutes15'
  const fileName = selectedUnit.value === '1min' 
    ? `${intersectionNumber}minute_lane_flow.csv`
    : `15minute_lane_flow${intersectionNumber}.csv`
  
  const filePath = `${basePath}/${fileName}`
  
  console.log('Loading traffic flow file:', filePath)
  // 加载新的数据
  data170.value = await loadCSVData(filePath)
  
  // 按方向分组数据
  const directionData = processDataByDirection(data170.value)
  
  // 重置为固定的4个图表
  dynamicChartCount.value = 4
  
  // 更新四张图表
  const directions = ['NW', 'NE', 'SW', 'SE']
  const chartRefs = [chartRef1, chartRef2, chartRef3, chartRef4]
  const titles = ['西北方向 (NW)', '东北方向 (NE)', '西南方向 (SW)', '东南方向 (SE)']
  const colors = getChartColors()
  
  renderTrafficFlowCharts(directions, chartRefs, titles, colors, directionData)
  
  console.log(`交叉口 ${intersectionNumber} 的流量图表渲染完成`)
}

// 加载供需曲线数据
const loadSupplyDemandChartData = async () => {
  // 从交叉口选择中提取数字
  const intersectionNumber = selectedIntersection.value.split('-')[1]
  const fileName = `${intersectionNumber}Supply-demand.csv`
  
  console.log(`正在加载交叉口 ${intersectionNumber} 的供需数据文件:`, fileName)
  
  // 加载供需数据
  const supplyDemandData = await loadSupplyDemandData(fileName)
  
  if (supplyDemandData.length === 0) {
    console.warn(`交叉口 ${intersectionNumber} 的供需数据文件为空或加载失败`)
    return
  }
  
  console.log(`成功加载交叉口 ${intersectionNumber} 的供需数据，共 ${supplyDemandData.length} 条记录`)
  
  // 数据验证和统计
  const timeRange = {
    start: new Date(Math.min(...supplyDemandData.map(d => d.time))),
    end: new Date(Math.max(...supplyDemandData.map(d => d.time)))
  }
  
  const demandStats = {
    min: Math.min(...supplyDemandData.map(d => d.smoothedDemand)),
    max: Math.max(...supplyDemandData.map(d => d.smoothedDemand)),
    avg: supplyDemandData.reduce((sum, d) => sum + d.smoothedDemand, 0) / supplyDemandData.length
  }
  
  const supplyStats = {
    min: Math.min(...supplyDemandData.map(d => d.utilizedSupply)),
    max: Math.max(...supplyDemandData.map(d => d.utilizedSupply)),
    avg: supplyDemandData.reduce((sum, d) => sum + d.utilizedSupply, 0) / supplyDemandData.length
  }
  
  console.log(`交叉口 ${intersectionNumber} 数据统计:`)
  console.log(`  时间范围: ${timeRange.start.toLocaleString()} - ${timeRange.end.toLocaleString()}`)
  console.log(`  需求统计: 最小=${demandStats.min.toFixed(2)}, 最大=${demandStats.max.toFixed(2)}, 平均=${demandStats.avg.toFixed(2)}`)
  console.log(`  供给统计: 最小=${supplyStats.min.toFixed(2)}, 最大=${supplyStats.max.toFixed(2)}, 平均=${supplyStats.avg.toFixed(2)}`)
  
  // 获取唯一的方向和转向组合
  const uniqueDirections = [...new Set(supplyDemandData.map(d => d.direction))]
  const uniqueMovements = [...new Set(supplyDemandData.map(d => d.movement))]
  const uniqueCombinations = [...new Set(supplyDemandData.map(d => `${d.direction}-${d.movement}`))]
  
  console.log(`  方向: ${uniqueDirections.join(', ')}`)
  console.log(`  转向: ${uniqueMovements.join(', ')}`)
  console.log(`  方向-转向组合: ${uniqueCombinations.join(', ')}`)
  
  // 按方向-转向分组数据
  const groupedData = processSupplyDemandByDirection(supplyDemandData)
  
  const groupCount = Object.keys(groupedData).length
  console.log(`交叉口 ${intersectionNumber} 的供需数据已分组，共 ${groupCount} 个方向-转向组合:`, Object.keys(groupedData))
  
  // 设置动态图表数量
  dynamicChartCount.value = groupCount
  
  // 为每个组合输出详细统计
  Object.keys(groupedData).forEach(groupKey => {
    const groupData = groupedData[groupKey]
    const groupDemandAvg = groupData.reduce((sum, d) => sum + d.smoothedDemand, 0) / groupData.length
    const groupSupplyAvg = groupData.reduce((sum, d) => sum + d.utilizedSupply, 0) / groupData.length
    console.log(`  ${groupKey}: ${groupData.length} 条数据, 平均需求=${groupDemandAvg.toFixed(2)}, 平均供给=${groupSupplyAvg.toFixed(2)}`)
  })
  
  renderSupplyDemandCharts(groupedData)
  
  console.log(`交叉口 ${intersectionNumber} 的供需曲线图表渲染完成`)
}

// 渲染流量图表
const renderTrafficFlowCharts = (directions, chartRefs, titles, colors, directionData) => {
  // 清空所有图表容器
  clearAllCharts()
  
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
}

// 渲染供需曲线图表 - 增强版
const renderSupplyDemandCharts = (groupedData) => {
  // 强制清空所有图表容器
  clearAllCharts()
  
  // 添加延迟确保清理完成
  setTimeout(() => {
    const groupKeys = Object.keys(groupedData)
    const colors = ['#ff6b6b', '#4ecdc4']
    
    // 记录当前交叉口信息
    const intersectionNumber = selectedIntersection.value.split('-')[1]
    console.log(`=== 交叉口 ${intersectionNumber} 供需曲线渲染 ===`)
    console.log('方向-转向组合数量:', groupKeys.length)
    
    // 为每个组合输出统计信息
    groupKeys.forEach((groupKey, index) => {
      const data = groupedData[groupKey]
      console.log(`${index + 1}. ${groupKey}: ${data.length} 条数据`)
      if (data.length > 0) {
        const demands = data.map(d => d.smoothedDemand)
        const supplies = data.map(d => d.utilizedSupply)
        console.log(`   需求范围: ${Math.min(...demands).toFixed(1)} - ${Math.max(...demands).toFixed(1)}`)
        console.log(`   供给范围: ${Math.min(...supplies).toFixed(1)} - ${Math.max(...supplies).toFixed(1)}`)
      }
    })
    
    // 如果是展开状态，只渲染展开的图表
    if (expandedChart.value !== null) {
      const expandedIndex = expandedChart.value
      const chartElement = expandedChartRef.value
      
      if (chartElement && groupKeys[expandedIndex]) {
        const chart = echarts.init(chartElement)
        const groupKey = groupKeys[expandedIndex]
        const data = groupedData[groupKey]
        const [direction, movement] = groupKey.split('-')
        
        const demandData = createSupplyDemandTimeSeriesData(data, 'demand')
        const supplyData = createSupplyDemandTimeSeriesData(data, 'supply')
        
        const series = [
          {
            name: '平滑需求',
            type: 'line',
            data: demandData,
            smooth: true,
            lineStyle: { color: colors[0], width: 3 },
            itemStyle: { color: colors[0] },
            symbol: 'circle',
            symbolSize: 6
          },
          {
            name: '利用供给',
            type: 'line',
            data: supplyData,
            smooth: true,
            lineStyle: { color: colors[1], width: 3, type: 'dashed' },
            itemStyle: { color: colors[1] },
            symbol: 'diamond',
            symbolSize: 6
          }
        ]
        
        chart.setOption({
          title: {
            text: `${direction} - ${movement}`,
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
            borderColor: '#4ecdc4',
            textStyle: { 
              color: '#333',
              fontSize: 24
            },
            formatter: function(params) {
              let result = `时间: ${new Date(params[0].value[0]).toLocaleString()}<br/>`
              params.forEach(param => {
                result += `${param.seriesName}: ${param.value[1].toFixed(1)}<br/>`
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
            name: '数量',
            nameTextStyle: { 
              color: '#666',
              fontSize: 24
            }
          },
          series: series,
          backgroundColor: 'transparent',
          grid: {
            left: '5%',
            right: '5%',
            bottom: '5%',
            top: '15%',
            containLabel: true
          }
        })
      }
      return
    }
    
    // 正常状态，渲染所有图表
    // 清空并重新创建图表容器
    chartContainers.value = []
    chartInstances.value = []
    
    // 在下一个tick中创建图表
    nextTick(() => {
      groupKeys.forEach((groupKey, index) => {
        const chartElement = document.getElementById(`dynamic-chart-${index}`)
        if (!chartElement) return
        
        const chart = echarts.init(chartElement)
        const data = groupedData[groupKey]
        const [direction, movement] = groupKey.split('-')
        
        const demandData = createSupplyDemandTimeSeriesData(data, 'demand')
        const supplyData = createSupplyDemandTimeSeriesData(data, 'supply')
        
        const series = [
          {
            name: '平滑需求',
            type: 'line',
            data: demandData,
            smooth: true,
            lineStyle: { color: colors[0], width: 2 },
            itemStyle: { color: colors[0] },
            symbol: 'circle',
            symbolSize: 4
          },
          {
            name: '利用供给',
            type: 'line',
            data: supplyData,
            smooth: true,
            lineStyle: { color: colors[1], width: 2, type: 'dashed' },
            itemStyle: { color: colors[1] },
            symbol: 'diamond',
            symbolSize: 4
          }
        ]
        
        chart.setOption({
          title: {
            text: `${direction} - ${movement}`,
            left: 'center',
            top: 10,
            textStyle: { 
              color: '#333', 
              fontSize: 14,
              fontWeight: 'bold'
            }
          },
          tooltip: { 
            trigger: 'axis',
            backgroundColor: 'rgba(255,255,255,0.95)',
            borderColor: '#4ecdc4',
            textStyle: { 
              color: '#333',
              fontSize: 12
            },
            formatter: function(params) {
              let result = `时间: ${new Date(params[0].value[0]).toLocaleString()}<br/>`
              params.forEach(param => {
                result += `${param.seriesName}: ${param.value[1].toFixed(1)}<br/>`
              })
              return result
            }
          },
          legend: {
            top: 35,
            textStyle: { 
              color: '#333', 
              fontSize: 9
            },
            itemWidth: 15,
            itemHeight: 10
          },
          xAxis: {
            type: 'time',
            axisLabel: { 
              color: '#666',
              fontSize: 9,
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
              fontSize: 9
            },
            axisLine: { lineStyle: { color: '#ccc' } },
            name: '数量',
            nameTextStyle: { 
              color: '#666',
              fontSize: 9
            }
          },
          series: series,
          backgroundColor: 'transparent',
          grid: {
            left: '5%',
            right: '5%',
            bottom: '5%',
            top: '15%',
            containLabel: true
          }
        })
        
        chartInstances.value[index] = chart
      })
    })
  }, 100)
}

// 监听选择器变化
watch([selectedIntersection, selectedTimeRange, selectedUnit, selectedChartType], async (newValues, oldValues) => {
  const [newIntersection, newTimeRange, newUnit, newChartType] = newValues
  const [oldIntersection, oldTimeRange, oldUnit, oldChartType] = oldValues || []
  
  console.log('选择器变化:', {
    交叉口: `${oldIntersection} → ${newIntersection}`,
    日期: `${oldTimeRange} → ${newTimeRange}`,
    单位: `${oldUnit} → ${newUnit}`,
    图表类型: `${oldChartType} → ${newChartType}`
  })
  
  // 特别处理供需曲线模式下的交叉口切换
  if (newChartType === 'supply-demand' && newIntersection !== oldIntersection) {
    console.log(`供需曲线模式下交叉口切换: ${oldIntersection} → ${newIntersection}`)
  }
  
  // 防止重复调用
  if (isLoading.value) return
  
  await nextTick()
  setTimeout(() => {
    handleDisplayClick()
  }, 100)
})

// 监听展开状态变化，重新渲染图表
watch(expandedChart, async (newVal, oldVal) => {
  if (newVal !== oldVal) {
    await nextTick()
    // 延迟一下确保DOM更新完成
    setTimeout(() => {
      handleDisplayClick()
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
    
    // 初始化时直接调用handleDisplayClick，它会处理加载状态
    handleDisplayClick()
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
      if (selectedChartType.value === 'traffic-flow') {
        [chartRef1, chartRef2, chartRef3, chartRef4].forEach(ref => {
          if (ref.value) {
            echarts.getInstanceByDom(ref.value)?.resize()
          }
        })
      } else {
        // 供需曲线图表
        chartInstances.value.forEach(chart => {
          if (chart) {
            chart.resize()
          }
        })
      }
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
        <div class="selector-group" v-if="selectedChartType !== 'supply-demand'">
          <label class="selector-group label">单位:</label>
          <select v-model="selectedUnit" class="header-select">
            <option v-for="option in unitOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>
        <div class="selector-group">
          <label class="selector-group label">图表类型:</label>
          <select v-model="selectedChartType" class="header-select chart-type-select">
            <option v-for="option in chartTypeOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>
        <button class="display-btn" @click="handleDisplayClick" :disabled="isLoading">
          {{ isLoading ? '加载中...' : '显示' }}
        </button>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts">
      <!-- 加载状态 -->
      <div v-if="isLoading" class="loading-overlay">
        <div class="loading-spinner">
          <div class="spinner"></div>
          <p>正在加载{{ selectedChartType === 'supply-demand' ? '供需曲线' : '流量图' }}数据...</p>
        </div>
      </div>
      
      <!-- 正常显示的图表 -->
      <div v-if="expandedChart === null" class="normal-charts-container">
        <!-- 流量图 - 固定4个图表 -->
        <template v-if="selectedChartType === 'traffic-flow'">
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
        </template>
        
        <!-- 供需曲线 - 动态数量图表 -->
        <template v-else-if="selectedChartType === 'supply-demand'">
          <div class="dynamic-charts-container" :class="getChartLayoutClass()">
            <div 
              v-for="(item, index) in dynamicChartCount" 
              :key="`dynamic-chart-${index}`"
              :id="`dynamic-chart-${index}`"
              class="chart-dynamic"
              @dblclick="toggleChartSize(index)"
            ></div>
          </div>
        </template>
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

/* 动态图表容器 */
.dynamic-charts-container {
  width: 100%;
  height: 100%;
  display: grid;
  gap: 12px;
  padding: 0;
}

/* 2x2 布局 (最多4个图表) */
.layout-2x2 {
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
}

/* 2x3 布局 (最多6个图表) */
.layout-2x3 {
  grid-template-columns: 1fr 1fr 1fr;
  grid-template-rows: 1fr 1fr;
}

/* 2x4 布局 (最多8个图表) */
.layout-2x4 {
  grid-template-columns: 1fr 1fr 1fr 1fr;
  grid-template-rows: 1fr 1fr;
}

/* 3x3 布局 (更多图表) */
.layout-3x3 {
  grid-template-columns: 1fr 1fr 1fr;
  grid-template-rows: 1fr 1fr 1fr;
}

/* 动态图表样式 */
.chart-dynamic {
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

.chart-dynamic:hover {
  border-color: rgba(200, 150, 100, 0.5);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
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

.chart-type-select {
  background: rgba(245, 245, 255, 0.9);
  border: 1px solid rgba(102, 102, 204, 0.4);
  color: #4a5568;
  font-weight: 500;
}

.chart-type-select:hover {
  border-color: rgba(102, 102, 204, 0.6);
  background: rgba(245, 245, 255, 1);
}

.chart-type-select:focus {
  border-color: #6666cc;
  box-shadow: 0 0 0 2px rgba(102, 102, 204, 0.2);
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

.display-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.display-btn:disabled:hover {
  background: #ccc;
  transform: none;
  box-shadow: none;
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

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.loading-spinner {
  text-align: center;
  color: #666;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #ff6b6b;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-spinner p {
  font-size: 16px;
  font-weight: 500;
  margin: 0;
}

/* 响应式设计 */
@media (max-width: 1600px) {
  .layout-2x4 {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr 1fr 1fr;
  }
}

@media (max-width: 1200px) {
  .layout-2x3 {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr 1fr;
  }
  
  .layout-3x3 {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr 1fr 1fr;
  }
}

@media (max-width: 768px) {
  .layout-2x2, .layout-2x3, .layout-2x4, .layout-3x3 {
    grid-template-columns: 1fr;
    grid-template-rows: repeat(auto-fit, minmax(200px, 1fr));
  }
  
  .chart-dynamic {
    min-height: 200px;
  }
  
  .control-panel {
    position: relative;
    top: 0;
    left: 0;
    padding: 10px;
  }
  
  .selector-info {
    flex-direction: column;
    gap: 8px;
  }
  
  .selector-group {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style> 