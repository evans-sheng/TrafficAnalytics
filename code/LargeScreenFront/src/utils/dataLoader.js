// CSV数据加载和处理工具函数

/**
 * 读取CSV文件数据
 * @param {string} filename - CSV文件名
 * @returns {Array} 处理后的数据数组
 */
export const loadCSVData = async (filename) => {
  try {
    const response = await fetch(`/src/assets/data/${filename}`)
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