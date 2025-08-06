import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/components/Layout.vue'
import Login from '@/views/Login.vue'
import Dashboard from '@/views/Dashboard.vue'
import Playground from '@/views/Playground.vue'
import Providers from '@/views/Providers.vue'
import Strategies from '@/views/Strategies.vue'
import Settings from '@/views/Settings.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: Dashboard
      },
      {
        path: 'playground',
        name: 'Playground',
        component: Playground
      },
      {
        path: 'providers',
        name: 'Providers',
        component: Providers
      },
      {
        path: 'strategies',
        name: 'Strategies',
        component: Strategies
      },
      {
        path: 'settings',
        name: 'Settings',
        component: Settings
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.name !== 'Login' && !token) {
    next({ name: 'Login' })
  } else {
    next()
  }
})

export default router