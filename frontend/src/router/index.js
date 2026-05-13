import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../composables/useAuth.js'

const routes = [
  {
    path:      '/login',
    name:      'login',
    component: () => import('../pages/LoginPage.vue'),
    meta:      { public: true },
  },
  {
    path:      '/callback',
    name:      'callback',
    component: () => import('../pages/CallbackPage.vue'),
    meta:      { public: true },
  },
  {
    path:      '/',
    name:      'chat',
    component: () => import('../components/ChatWindow.vue'),
  },
  // Catch-all → redirect home
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Auth guard — redirect unauthenticated users to /login
router.beforeEach((to) => {
  if (to.meta.public) return true
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated.value) return { name: 'login' }
  return true
})

export default router
