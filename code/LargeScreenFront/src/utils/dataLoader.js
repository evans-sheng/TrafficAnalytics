// CSV数据加载和处理工具函数

/**
 * 读取CSV文件数据
 * @param {string} filename - CSV文件名
 * @returns {Array} 处理后的数据数组
 */
export const loadCSVData = async (filename) => {
  try {
    const response = await fetch(`/data/${filename}`)
    const text = await response.text()
    const lines = text.split('\n')
    const data = []
    
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim()
      if (line) {
        const [direction, lane, minute, vehicle_count] = line.split(',')
        
        // 解析时间并转换为东八区时间（UTC+8）
        const originalTime = new Date(minute)
        const utc8Time = new Date(originalTime.getTime() + 8 * 60 * 60 * 1000)
        
        data.push({
          direction: direction,
          lane: lane,
          time: utc8Time,
          count: parseInt(vehicle_count)
        })
      }
    }
    
    console.log(`已加载 ${data.length} 条数据，时间已转换为东八区`)
    return data
  } catch (error) {
    console.error('Error loading CSV:', error)
    return []
  }
}

/**
 * 按方向分组数据
 * @param {Array} data - 原始数据数组
 * @returns {Object} 按方向分组的数据对象
 */
export const processDataByDirection = (data) => {
  const directions = ['NW', 'NE', 'SW', 'SE']
  const directionData = {}
  
  directions.forEach(dir => {
    directionData[dir] = data.filter(item => item.direction === dir)
  })
  
  return directionData
}

/**
 * 获取指定方向的车道列表
 * @param {Array} data - 该方向的数据数组
 * @returns {Array} 排序后的车道列表
 */
export const getLanesFromData = (data) => {
  return [...new Set(data.map(item => item.lane))].sort()
}

/**
 * 为指定车道创建时间序列数据
 * @param {Array} data - 该方向的数据数组
 * @param {string} lane - 车道标识
 * @returns {Array} 时间序列数据数组
 */
export const createLaneTimeSeriesData = (data, lane) => {
  return data.filter(item => item.lane === lane)
    .sort((a, b) => a.time - b.time)
    .map(item => [item.time, item.count])
}

/**
 * 获取图表颜色数组
 * @returns {Array} 颜色数组
 */
export const getChartColors = () => {
  return ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7', '#dda0dd', '#98d8c8', '#f7dc6f']
}

/**
 * 读取供需CSV文件数据
 * @param {string} filename - 供需CSV文件名
 * @returns {Array} 处理后的供需数据数组
 */
export const loadSupplyDemandData = async (filename) => {
  try {
    console.log(`开始加载供需数据文件: ${filename}`)
    
    const response = await fetch(`/data/supplydemand/${filename}`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const text = await response.text()
    
    // 验证文件内容
    if (!text || text.trim().length === 0) {
      throw new Error(`文件 ${filename} 为空`)
    }
    
    // 检查是否包含JavaScript代码（避免之前的错误）
    if (text.includes('const ') || text.includes('function') || text.includes('//')) {
      throw new Error(`文件 ${filename} 包含无效的JavaScript代码，不是有效的CSV文件`)
    }
    
    const lines = text.split('\n')
    const data = []
    
    console.log(`文件 ${filename} 共 ${lines.length} 行`)
    
    // 跳过第一行（表头）
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim()
      if (line) {
        const values = line.split(',')
        if (values.length >= 13) { // 确保行数据完整
          const timeStr = values[2]
          const direction = values[3]
          const movement = values[4]
          const smoothedDemand = parseFloat(values[6])
          const utilizedSupply = parseFloat(values[11])
          
          // 验证数据有效性
          if (isNaN(smoothedDemand) || isNaN(utilizedSupply)) {
            console.warn(`行 ${i + 1}: 无效的数值数据`)
            continue
          }
          
          // 解析时间
          const time = new Date(timeStr)
          if (isNaN(time.getTime())) {
            console.warn(`行 ${i + 1}: 无效的时间格式: ${timeStr}`)
            continue
          }
          
          data.push({
            time: time,
            direction: direction,
            movement: movement,
            smoothedDemand: smoothedDemand,
            utilizedSupply: utilizedSupply
          })
        }
      }
    }
    
    console.log(`成功加载文件 ${filename}，有效数据 ${data.length} 条`)
    
    // 数据完整性检查
    if (data.length === 0) {
      throw new Error(`文件 ${filename} 没有有效的数据行`)
    }
    
    // 生成数据指纹用于验证
    const dataFingerprint = {
      filename: filename,
      recordCount: data.length,
      firstRecord: data[0] ? {
        time: data[0].time.toISOString(),
        direction: data[0].direction,
        movement: data[0].movement,
        demand: data[0].smoothedDemand,
        supply: data[0].utilizedSupply
      } : null,
      lastRecord: data[data.length - 1] ? {
        time: data[data.length - 1].time.toISOString(),
        direction: data[data.length - 1].direction,
        movement: data[data.length - 1].movement,
        demand: data[data.length - 1].smoothedDemand,
        supply: data[data.length - 1].utilizedSupply
      } : null
    }
    
    console.log(`数据指纹 (${filename}):`, dataFingerprint)
    
    return data
  } catch (error) {
    console.error(`加载供需数据文件 ${filename} 失败:`, error)
    return []
  }
}

/**
 * 按方向和转向类型分组供需数据
 * @param {Array} data - 原始供需数据数组
 * @returns {Object} 按方向-转向组合分组的数据对象
 */
export const processSupplyDemandByDirection = (data) => {
  // 过滤早高峰时间段 (5:00-15:00)
  const filteredData = data.filter(item => {
    const hour = item.time.getHours()
    return hour >= 5 && hour <= 15
  })
  
  const groupedData = {}
  
  filteredData.forEach(item => {
    const key = `${item.direction}-${item.movement}`
    if (!groupedData[key]) {
      groupedData[key] = []
    }
    groupedData[key].push(item)
  })
  
  // 对每个组的数据按时间排序
  Object.keys(groupedData).forEach(key => {
    groupedData[key].sort((a, b) => a.time - b.time)
  })
  
  return groupedData
}

/**
 * 创建供需时间序列数据
 * @param {Array} data - 该方向-转向的数据数组
 * @param {string} type - 'demand' 或 'supply'
 * @returns {Array} 时间序列数据数组
 */
export const createSupplyDemandTimeSeriesData = (data, type) => {
  return data.map(item => [
    item.time, 
    type === 'demand' ? item.smoothedDemand : item.utilizedSupply
  ])
} 