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
    component: () => import('../pages/ChatPage.vue'),
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  if (to.meta.public) return true
  const { isAuthenticated, fetchUser } = useAuth()
  // If not authenticated, try to restore from cookie before redirecting
  if (!isAuthenticated.value) {
    await fetchUser()
  }
  if (!isAuthenticated.value) return { name: 'login' }
  return true
})

export default router
