<template>
  <div class="top-header">
    <!-- 顶部横条 -->
    <div class="header-bar">
      <div class="bar-left"></div>
      <div class="bar-gap"></div>
      <div class="bar-right">
        <!-- 时间信息 -->
        <div class="time-info">
          <div class="current-time">{{ currentTime }}</div>
          <div class="current-date">{{ currentDate }}</div>
        </div>
        <!-- 插槽用于额外的导航按钮 -->
        <slot name="navigation"></slot>
      </div>
    </div>
    <!-- 中间凸出部分（刘海） -->
    <div class="header-notch">
      <div class="title">智慧交通大屏</div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'

export default {
  name: 'TopHeader',
  setup() {
    const currentTime = ref('')
    const currentDate = ref('')
    let timeInterval = null

    // 更新时间
    const updateTime = () => {
      const now = new Date()
      currentTime.value = now.toLocaleTimeString('zh-CN', { hour12: false })
      currentDate.value = now.toLocaleDateString('zh-CN', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        weekday: 'long'
      })
    }

    onMounted(() => {
      // 初始化时间并每秒更新
      updateTime()
      timeInterval = setInterval(updateTime, 1000)
    })

    onUnmounted(() => {
      if (timeInterval) {
        clearInterval(timeInterval)
      }
    })

    return {
      currentTime,
      currentDate
    }
  }
}
</script>

<style scoped>
.top-header {
  position: relative;
  height: 60px;
  width: 100%;
}

.header-bar {
  display: flex;
  height: 30px;
  background: linear-gradient(135deg, rgba(255, 250, 245, 0.95), rgba(255, 240, 230, 0.9));
  position: relative;
  border-bottom: 2px solid rgba(200, 150, 100, 0.4);
}

.bar-left {
  flex: 1;
  height: 30px;
  background: linear-gradient(135deg, rgba(255, 250, 245, 0.95), rgba(255, 240, 230, 0.9));
  position: relative;
  z-index: 1;
  margin-right: -1px;
}

.bar-right {
  flex: 1;
  height: 30px;
  background: linear-gradient(135deg, rgba(255, 250, 245, 0.95), rgba(255, 240, 230, 0.9));
  position: relative;
  z-index: 1;
  margin-left: -1px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding-right: 15px;
  min-width: 200px;
  overflow: hidden;
}

.bar-gap {
  width: 300px;
  height: 30px;
  background: linear-gradient(135deg, rgba(255, 250, 245, 0.95), rgba(255, 240, 230, 0.9));
  position: relative;
  z-index: 2;
  margin: 0 -1px;
}

.header-notch {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 320px;
  height: 50px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(255, 245, 235, 0.95));
  border-left: 2px solid rgba(200, 150, 100, 0.4);
  border-right: 2px solid rgba(200, 150, 100, 0.4);
  border-bottom: 2px solid rgba(200, 150, 100, 0.4);
  border-radius: 0 0 20px 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.1),
    inset 0 1px 5px rgba(255, 200, 150, 0.2);
  z-index: 3;
}

.title {
  font-size: 2rem;
  font-weight: bold;
  letter-spacing: 6px;
  color: #333333;
  text-align: center;
  text-shadow: 
    0 0 20px rgba(255, 200, 150, 0.6),
    0 2px 4px rgba(0, 0, 0, 0.1);
  white-space: nowrap;
}

.time-info {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 15px;
  white-space: nowrap;
  max-width: 100%;
}

.current-time {
  font-size: 1rem;
  font-weight: bold;
  color: #cc6600;
  text-shadow: 0 0 8px rgba(204, 102, 0, 0.4);
  letter-spacing: 0.5px;
}

.current-date {
  font-size: 0.8rem;
  color: #666666;
  opacity: 0.9;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}
</style> 