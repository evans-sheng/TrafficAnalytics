// 坐标系转换工具函数
// 支持WGS84（GPS）、GCJ02（火星坐标系）、BD09（百度坐标系）之间的转换

const PI = Math.PI
const A = 6378245.0 // 长半轴
const EE = 0.00669342162296594323 // 偏心率平方

/**
 * 判断坐标是否在中国境内
 */
function isInChina(lng, lat) {
  return lng >= 72.004 && lng <= 137.8347 && lat >= 0.8293 && lat <= 55.8271
}

/**
 * 转换纬度
 */
function transformLat(lng, lat) {
  let ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * Math.sqrt(Math.abs(lng))
  ret += (20.0 * Math.sin(6.0 * lng * PI) + 20.0 * Math.sin(2.0 * lng * PI)) * 2.0 / 3.0
  ret += (20.0 * Math.sin(lat * PI) + 40.0 * Math.sin(lat / 3.0 * PI)) * 2.0 / 3.0
  ret += (160.0 * Math.sin(lat / 12.0 * PI) + 320 * Math.sin(lat * PI / 30.0)) * 2.0 / 3.0
  return ret
}

/**
 * 转换经度
 */
function transformLng(lng, lat) {
  let ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * Math.sqrt(Math.abs(lng))
  ret += (20.0 * Math.sin(6.0 * lng * PI) + 20.0 * Math.sin(2.0 * lng * PI)) * 2.0 / 3.0
  ret += (20.0 * Math.sin(lng * PI) + 40.0 * Math.sin(lng / 3.0 * PI)) * 2.0 / 3.0
  ret += (150.0 * Math.sin(lng / 12.0 * PI) + 300.0 * Math.sin(lng / 30.0 * PI)) * 2.0 / 3.0
  return ret
}

/**
 * WGS84 转 GCJ02（火星坐标系）
 */
export function wgs84ToGcj02(lng, lat) {
  if (!isInChina(lng, lat)) {
    return { longitude: lng, latitude: lat }
  }
  
  let dlat = transformLat(lng - 105.0, lat - 35.0)
  let dlng = transformLng(lng - 105.0, lat - 35.0)
  const radlat = lat / 180.0 * PI
  let magic = Math.sin(radlat)
  magic = 1 - EE * magic * magic
  const sqrtmagic = Math.sqrt(magic)
  dlat = (dlat * 180.0) / ((A * (1 - EE)) / (magic * sqrtmagic) * PI)
  dlng = (dlng * 180.0) / (A / sqrtmagic * Math.cos(radlat) * PI)
  const mglat = lat + dlat
  const mglng = lng + dlng
  
  return { longitude: mglng, latitude: mglat }
}

/**
 * GCJ02（火星坐标系） 转 WGS84
 */
export function gcj02ToWgs84(lng, lat) {
  if (!isInChina(lng, lat)) {
    return { longitude: lng, latitude: lat }
  }
  
  let dlat = transformLat(lng - 105.0, lat - 35.0)
  let dlng = transformLng(lng - 105.0, lat - 35.0)
  const radlat = lat / 180.0 * PI
  let magic = Math.sin(radlat)
  magic = 1 - EE * magic * magic
  const sqrtmagic = Math.sqrt(magic)
  dlat = (dlat * 180.0) / ((A * (1 - EE)) / (magic * sqrtmagic) * PI)
  dlng = (dlng * 180.0) / (A / sqrtmagic * Math.cos(radlat) * PI)
  const mglat = lat - dlat
  const mglng = lng - dlng
  
  return { longitude: mglng, latitude: mglat }
}

/**
 * GCJ02（火星坐标系） 转 BD09（百度坐标系）
 */
export function gcj02ToBd09(lng, lat) {
  const z = Math.sqrt(lng * lng + lat * lat) + 0.00002 * Math.sin(lat * PI * 3000.0 / 180.0)
  const theta = Math.atan2(lat, lng) + 0.000003 * Math.cos(lng * PI * 3000.0 / 180.0)
  const bd_lng = z * Math.cos(theta) + 0.0065
  const bd_lat = z * Math.sin(theta) + 0.006
  
  return { longitude: bd_lng, latitude: bd_lat }
}

/**
 * BD09（百度坐标系） 转 GCJ02（火星坐标系）
 */
export function bd09ToGcj02(lng, lat) {
  const x = lng - 0.0065
  const y = lat - 0.006
  const z = Math.sqrt(x * x + y * y) - 0.00002 * Math.sin(y * PI * 3000.0 / 180.0)
  const theta = Math.atan2(y, x) - 0.000003 * Math.cos(x * PI * 3000.0 / 180.0)
  const gcj_lng = z * Math.cos(theta)
  const gcj_lat = z * Math.sin(theta)
  
  return { longitude: gcj_lng, latitude: gcj_lat }
}

/**
 * WGS84 转 BD09（百度坐标系）
 */
export function wgs84ToBd09(lng, lat) {
  const gcj02 = wgs84ToGcj02(lng, lat)
  return gcj02ToBd09(gcj02.longitude, gcj02.latitude)
}

/**
 * BD09（百度坐标系） 转 WGS84
 */
export function bd09ToWgs84(lng, lat) {
  const gcj02 = bd09ToGcj02(lng, lat)
  return gcj02ToWgs84(gcj02.longitude, gcj02.latitude)
}

/**
 * 统一坐标转换函数
 * @param {number} lng - 经度
 * @param {number} lat - 纬度
 * @param {string} fromType - 源坐标系类型: 'wgs84', 'gcj02', 'bd09'
 * @param {string} toType - 目标坐标系类型: 'wgs84', 'gcj02', 'bd09'
 * @returns {object} 转换后的坐标 {longitude, latitude}
 */
export function convertCoordinate(lng, lat, fromType, toType) {
  if (fromType === toType) {
    return { longitude: lng, latitude: lat }
  }
  
  const converters = {
    'wgs84_gcj02': wgs84ToGcj02,
    'wgs84_bd09': wgs84ToBd09,
    'gcj02_wgs84': gcj02ToWgs84,
    'gcj02_bd09': gcj02ToBd09,
    'bd09_wgs84': bd09ToWgs84,
    'bd09_gcj02': bd09ToGcj02
  }
  
  const converterKey = `${fromType}_${toType}`
  const converter = converters[converterKey]
  
  if (converter) {
    return converter(lng, lat)
  } else {
    console.warn(`不支持的坐标转换类型: ${fromType} -> ${toType}`)
    return { longitude: lng, latitude: lat }
  }
}

/**
 * 获取坐标系类型信息
 */
export const coordinateSystemInfo = {
  wgs84: {
    name: 'GPS坐标系',
    description: 'WGS84 - 国际标准GPS坐标系',
    code: 'wgs84'
  },
  gcj02: {
    name: '火星坐标系',
    description: 'GCJ-02 - 中国标准坐标系（高德、腾讯地图）',
    code: 'gcj02'
  },
  bd09: {
    name: '百度坐标系',
    description: 'BD-09 - 百度地图坐标系',
    code: 'bd09'
  }
} 