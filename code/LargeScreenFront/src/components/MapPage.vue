<script>
import { ref, onMounted, onUnmounted } from 'vue'
import TopHeader from './TopHeader.vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { convertCoordinate, coordinateSystemInfo } from '../utils/coordinateConverter.js'

// 修复Leaflet默认标记图标问题
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

export default {
  name: 'MapPage',
  components: {
    TopHeader
  },
  setup() {
    const mapContainer = ref(null)
    const map = ref(null)
    const locationData = ref([])
    const isLoadingData = ref(false)
    const locationMarkers = ref([])
    const selectedCoordinateSystem = ref('gcj02') // 默认选择火星坐标系

    // 加载点位数据
    const loadLocationData = async () => {
      try {
        isLoadingData.value = true
        console.log('开始加载数据...')
        
        // 先尝试硬编码数据来测试功能
        const testData = [
          {"longitude":"116.511681","latitude":"39.761152"},
          {"longitude":"116.511659","latitude":"39.760459"},
          {"longitude":"116.511654","latitude":"39.761188"},
          {"longitude":"116.511677","latitude":"39.761249"},
          {"longitude":"116.512052","latitude":"39.760736"}
        ]
        
        console.log('使用测试数据:', testData)
        locationData.value = testData
        
        // 显示点位
        displayLocationPoints()
        
        // 然后尝试加载真实数据
        try {
          const response = await fetch('/data/position/170location.txt')
          if (response.ok) {
            const text = await response.text()
            console.log('获取到文件数据:', text.substring(0, 200) + '...')
            
            const lines = text.trim().split('\n')
            const locations = lines.map(line => {
              try {
                return JSON.parse(line)
              } catch (e) {
                console.warn('Failed to parse line:', line)
                return null
              }
            }).filter(item => item !== null)
            
            if (locations.length > 0) {
              locationData.value = locations
              console.log(`从文件加载了 ${locations.length} 个点位`)
              displayLocationPoints()
            }
          }
        } catch (fileError) {
          console.warn('文件加载失败，使用测试数据:', fileError)
        }
        
      } catch (error) {
        console.error('加载数据出错:', error)
        alert(`加载数据失败: ${error.message}`)
      } finally {
        isLoadingData.value = false
      }
    }

    // 在地图上显示点位数据
    const displayLocationPoints = () => {
      if (!map.value || locationData.value.length === 0) {
        console.warn('地图未初始化或没有位置数据', {
          mapExists: !!map.value,
          locationCount: locationData.value.length
        })
        return
      }

      console.log('开始显示点位...')

      // 清除之前的点位标记
      locationMarkers.value.forEach(marker => {
        map.value.removeLayer(marker)
      })
      locationMarkers.value = []

      const bounds = L.latLngBounds([]) // 创建边界对象

      // 根据点位数量确定样式
      const pointCount = locationData.value.length
      const useSmallBlackDots = pointCount > 100
      
      console.log(`点位数量: ${pointCount}, 使用${useSmallBlackDots ? '黑色小点' : '红色大点'}`)

      // 设置样式参数
      const markerStyle = useSmallBlackDots ? {
        radius: 5,
        fillColor: '#000000',
        color: '#ffffff',
        weight: 1,
        opacity: 1,
        fillOpacity: 0.8
      } : {
        radius: 8,
        fillColor: '#ff0000',
        color: '#ffffff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8
      }

      // 添加所有点位到地图
      locationData.value.forEach((location, index) => {
        const originalLat = parseFloat(location.latitude)
        const originalLng = parseFloat(location.longitude)
        
        if (!isNaN(originalLat) && !isNaN(originalLng)) {
          // 坐标系转换逻辑：
          // - GPS坐标系：不转换，直接使用
          // - 火星坐标系：转换为GPS坐标系
          // - 百度坐标系：转换为GPS坐标系
          let lat, lng
          if (selectedCoordinateSystem.value === 'wgs84') {
            // GPS坐标系，不转换
            lat = originalLat
            lng = originalLng
          } else {
            // 火星坐标系或百度坐标系，转换为GPS坐标系
            const converted = convertCoordinate(originalLng, originalLat, selectedCoordinateSystem.value, 'wgs84')
            lat = converted.latitude
            lng = converted.longitude
          }
          
          console.log(`添加点位 ${index + 1}:`, { 
            original: { lat: originalLat, lng: originalLng },
            converted: { lat, lng },
            coordinateSystem: selectedCoordinateSystem.value,
            converted_to: selectedCoordinateSystem.value === 'wgs84' ? '无转换' : 'GPS坐标系'
          })
          
          // 使用 CircleMarker，根据点位数量应用不同样式
          const marker = L.circleMarker([lat, lng], markerStyle).addTo(map.value)
          
          marker.bindPopup(`
            <div style="color: #000; font-size: 14px; font-weight: bold;">
              <b>📍 位置点 ${index + 1}</b><br>
              <div style="margin-top: 8px;">
                <strong>原始坐标 (${coordinateSystemInfo[selectedCoordinateSystem.value].name}):</strong><br>
                <div style="margin-left: 10px; font-size: 12px;">
                  经度: ${originalLng}<br>
                  纬度: ${originalLat}
                </div>
                <strong>地图坐标 (GPS坐标系):</strong><br>
                <div style="margin-left: 10px; font-size: 12px;">
                  经度: ${lng.toFixed(6)}<br>
                  纬度: ${lat.toFixed(6)}
                </div>
                <div style="margin-top: 5px; font-size: 12px; color: #666;">
                  ${selectedCoordinateSystem.value === 'wgs84' ? '未进行坐标转换' : '已转换为GPS坐标系'}<br>
                  总计: ${pointCount} 个点位
                </div>
              </div>
            </div>
          `)
          
          locationMarkers.value.push(marker)
          bounds.extend([lat, lng])
        } else {
          console.warn('无效的经纬度:', location)
        }
      })

      // 如果有点位，调整地图视图
      if (locationMarkers.value.length > 0) {
        console.log(`成功添加 ${locationMarkers.value.length} 个点位`)
        // 调整地图视图以显示所有点位，增加更多边距
        map.value.fitBounds(bounds.pad(0.2))
        
        // 确保最小缩放级别，让点位可见
        setTimeout(() => {
          if (map.value.getZoom() > 18) {
            map.value.setZoom(16)
          }
        }, 100)
      } else {
        console.warn('没有添加任何点位')
      }
    }

    // 初始化OpenStreetMap
    const initializeMap = () => {
      if (mapContainer.value && !map.value) {
        try {
          console.log('开始初始化地图...')
          
          // 确保 Leaflet 默认图标路径正确
          delete L.Icon.Default.prototype._getIconUrl
          L.Icon.Default.mergeOptions({
            iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
            iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
          })
          
          // 创建地图实例
          map.value = L.map(mapContainer.value, {
            center: [39.9042, 116.4074], // 北京中心
            zoom: 12,
            zoomControl: true,
            attributionControl: true
          })

          console.log('地图实例创建完成，中心点:', map.value.getCenter())

          // 添加OSM瓦片层
          const tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19,
            subdomains: ['a', 'b', 'c']
          }).addTo(map.value)

          console.log('瓦片层已添加')

          // 地图准备就绪事件
          map.value.whenReady(() => {
            console.log('地图完全就绪')
            console.log('地图大小:', map.value.getSize())
            console.log('地图缩放级别:', map.value.getZoom())
          })

          console.log('地图初始化完成')

          // 如果已经加载了点位数据，显示在地图上
          if (locationData.value.length > 0) {
            displayLocationPoints()
          }
        } catch (error) {
          console.error('初始化地图出错:', error)
        }
      }
    }

    onMounted(() => {
      initializeMap()
    })

    onUnmounted(() => {
      if (map.value) {
        map.value.remove()
        map.value = null
      }
    })

    return {
      mapContainer,
      loadLocationData,
      isLoadingData,
      locationData,
      selectedCoordinateSystem,
      coordinateSystemInfo
    }
  }
}
</script>

<template>
  <div class="map-page">
    <TopHeader>
      <template #navigation>
        <button class="nav-to-stats" @click="$router.push('/')">统计视图</button>
      </template>
    </TopHeader>
    <div class="map-container">
      <div class="map-content">
        <div class="map-header">
          <h3>实时交通地图 - OpenStreetMap</h3>
          <div class="map-info">
            <div class="coordinate-selector">
              <label for="coordinate-system">坐标系:</label>
              <select 
                id="coordinate-system" 
                v-model="selectedCoordinateSystem"
                class="coordinate-select"
                @change="displayLocationPoints"
              >
                <option value="gcj02">{{ coordinateSystemInfo.gcj02.name }}</option>
                <option value="wgs84">{{ coordinateSystemInfo.wgs84.name }}</option>
                <option value="bd09">{{ coordinateSystemInfo.bd09.name }}</option>
              </select>
            </div>
            <button 
              class="import-button" 
              @click="loadLocationData"
              :disabled="isLoadingData"
            >
              {{ isLoadingData ? '加载中...' : '导入点位数据' }}
            </button>
            <span v-if="locationData.length > 0" class="location-count">
              位置点: {{ locationData.length }}
            </span>
          </div>
        </div>
        <div ref="mapContainer" class="osm-map-container"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.map-page {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #fefefe 0%, #fff8f5 50%, #ffeee8 100%);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
  margin: 0;
}

.map-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin: 20px;
  border-radius: 12px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.8);
  border: 2px solid rgba(200, 150, 100, 0.3);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  min-height: 0;
}

.map-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.map-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: rgba(255, 250, 245, 0.9);
  border-bottom: 1px solid rgba(200, 150, 100, 0.2);
  flex-shrink: 0;
}

.map-header h3 {
  font-size: 1.5rem;
  font-weight: bold;
  color: #333333;
  text-shadow: 0 0 10px rgba(255, 200, 150, 0.4);
  margin: 0;
}

.map-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.coordinate-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.coordinate-selector label {
  font-size: 0.9rem;
  color: #333;
  font-weight: 600;
  white-space: nowrap;
}

.coordinate-select {
  padding: 6px 12px;
  border: 1px solid rgba(200, 150, 100, 0.4);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.9);
  color: #333;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 120px;
}

.coordinate-select:hover {
  border-color: rgba(200, 150, 100, 0.6);
  background: rgba(255, 255, 255, 1);
}

.coordinate-select:focus {
  outline: none;
  border-color: #cc6600;
  box-shadow: 0 0 0 2px rgba(204, 102, 0, 0.2);
}

.import-button {
  background: linear-gradient(135deg, #00cc66, #00aa44);
  border: none;
  border-radius: 8px;
  padding: 10px 20px;
  color: #ffffff;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  transition: all 0.3s ease;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.import-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #00aa44, #008833);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 200, 100, 0.3);
}

.import-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.location-count {
  font-size: 0.9rem;
  color: #00aa44;
  font-weight: 600;
  text-shadow: 0 0 5px rgba(0, 170, 68, 0.3);
}

.nav-to-stats {
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

.nav-to-stats:hover {
  background: linear-gradient(135deg, #aa5500, #884400);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(204, 102, 0, 0.3);
}

.osm-map-container {
  flex: 1;
  width: 100%;
  height: 100%;
  border: none;
  outline: none;
  position: relative;
  min-height: 400px;
}

/* Leaflet 地图样式覆盖 */
.osm-map-container :deep(.leaflet-container) {
  background: #f8f8f8;
  font-family: inherit;
  height: 100% !important;
  width: 100% !important;
}

.osm-map-container :deep(.leaflet-popup-content-wrapper) {
  background: rgba(255, 255, 255, 0.95);
  color: #333333;
  border: 1px solid rgba(200, 150, 100, 0.4);
  border-radius: 8px;
}

.osm-map-container :deep(.leaflet-popup-tip) {
  background: rgba(255, 255, 255, 0.95);
}

.location-point-icon .location-dot {
  position: relative;
  width: 24px;
  height: 24px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.location-point-icon .location-center {
  width: 16px;
  height: 16px;
  background: #ff0000;
  border-radius: 50%;
  border: 3px solid #ffffff;
  box-shadow: 
    0 0 20px rgba(255, 0, 0, 0.8),
    0 0 10px rgba(255, 0, 0, 1),
    inset 0 0 5px rgba(255, 255, 255, 0.3);
  z-index: 2;
  position: relative;
}

.location-point-icon .location-pulse {
  position: absolute;
  width: 24px;
  height: 24px;
  border: 2px solid #ff0000;
  border-radius: 50%;
  animation: pulse 2s infinite;
  opacity: 0.6;
}

@keyframes pulse {
  0% {
    transform: scale(1);
    opacity: 0.8;
  }
  50% {
    transform: scale(1.5);
    opacity: 0.4;
  }
  100% {
    transform: scale(2);
    opacity: 0;
  }
}

.location-point-icon .location-dot:hover .location-center {
  transform: scale(1.3);
  box-shadow: 
    0 0 30px rgba(255, 0, 0, 1),
    0 0 15px rgba(255, 0, 0, 1),
    inset 0 0 8px rgba(255, 255, 255, 0.5);
}

.location-point-icon .location-dot:hover .location-pulse {
  animation-duration: 1s;
}
</style> 