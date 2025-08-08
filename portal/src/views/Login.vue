<template>
  <div class="login-container">
    <div class="login-form">
      <h1>PortBroker Portal</h1>
      <a-form
        :model="form"
        @finish="handleLogin"
        layout="vertical"
      >
        <a-form-item
          label="API Key"
          name="api_key"
          :rules="[{ required: true, message: 'Please input your API key!' }]"
        >
          <a-input-password v-model:value="form.api_key" size="large" placeholder="Enter your API key" />
        </a-form-item>
        
        <a-form-item>
          <a-button type="primary" html-type="submit" size="large" block :loading="loading">
            Login
          </a-button>
        </a-form-item>
      </a-form>
    </div>
  </div>
</template>

<script>
import { message } from 'ant-design-vue'
import api from '@/api'

export default {
  name: 'Login',
  data() {
    return {
      form: {
        api_key: ''
      },
      loading: false
    }
  },
  methods: {
    async handleLogin() {
      this.loading = true
      try {
        const response = await api.login(this.form)
        localStorage.setItem('token', response.access_token)
        
        // Fetch user information
        const userInfo = await api.getUserInfo()
        localStorage.setItem('user', JSON.stringify(userInfo))
        
        message.success('Login successful')
        this.$router.push('/')
      } catch (error) {
        message.error('Login failed: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-form {
  background: white;
  padding: 40px;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
}

.login-form h1 {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
}
</style>