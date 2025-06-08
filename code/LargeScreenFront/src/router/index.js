import { createRouter, createWebHistory } from 'vue-router'
import MainPage from '../components/MainPage.vue'
import MapPage from '../components/MapPage.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: MainPage
  },
  {
    path: '/map',
    name: 'Map',
    component: MapPage
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router 