<template>
  <div id="app">
    <a-config-provider>
      <router-view />
    </a-config-provider>
  </div>
</template>

<script>
import { onMounted } from 'vue'
import api from '@/api'

export default {
  name: 'App',
  setup() {
    const fetchUserInfo = async () => {
      try {
        const token = localStorage.getItem('token')
        if (token && !localStorage.getItem('user')) {
          const userInfo = await api.getUserInfo()
          localStorage.setItem('user', JSON.stringify(userInfo))
        }
      } catch (error) {
        console.error('Failed to fetch user info:', error)
        // If we can't fetch user info, clear the token and redirect to login
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.location.href = '/login'
      }
    }

    onMounted(() => {
      fetchUserInfo()
    })
  }
}
</script>

<style>
#app {
  min-height: 100vh;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>