import { createRouter, createWebHistory } from 'vue-router'
import LoginForm from '../components/LoginForm.vue'
import GamePlayList from '../components/GamePlayList.vue'
import PlayGameForm from '../components/PlayGameForm.vue'
import AdminDashboard from '../components/AdminDashboard.vue'
import BusinessDashboard from '../components/BusinessDashboard.vue'
import ReportsPanel from '../components/ReportsPanel.vue'
import axios from 'axios'

const routes = [
  { path: '/', component: LoginForm },
  { path: '/play', component: PlayGameForm },
  { path: '/gameplays', component: GamePlayList },
  { path: '/admin-dashboard', component: AdminDashboard },
  { path: '/business-dashboard', component: BusinessDashboard },
  { path: '/business-reports', component: ReportsPanel },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Route guard
router.beforeEach(async (to, from, next) => {
  try {
    const { data } = await axios.get('http://127.0.0.1:8000/api/whoami/', {
      withCredentials: true,
    })
    const role = data.role // <-- backend ile uyumlu

    // Giriş sayfasındayken zaten auth'luysa yönlendir
    if (to.path === '/') {
      if (role === 'admin') return next('/admin-dashboard')
      if (role === 'business_user') return next('/business-dashboard')
      if (role === 'player') return next('/play')
      return next() // unknown -> login'de kalsın
    }

    // Yetkisiz erişimlere karşı koru
    if (to.path.startsWith('/admin') && role !== 'admin') {
      return next('/')
    }
    if (to.path.startsWith('/business') && role !== 'business_user') {
      return next('/')
    }

    
    if (to.path === '/play' && role !== 'player' && role !== 'business_user' && role !== 'admin') {
      return next('/')
    }
    next()
  } catch (e) {
    // whoami 401 ise sadece login'e izin ver
    if (to.path !== '/') return next('/')
    next()
  }
})

export default router
