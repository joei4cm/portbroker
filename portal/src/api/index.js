import axios from 'axios'

const api = axios.create({
  baseURL: '/api/portal',
  timeout: 10000
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default {
  async login(credentials) {
    const response = await api.post('/login', { api_key: credentials.api_key })
    const data = response.data
    
    // Store the API key for future use (e.g., DELETE operations)
    localStorage.setItem('apiKey', credentials.api_key)
    
    return data
  },
  
  async getProviders() {
    const response = await api.get('/providers')
    return response.data
  },
  
  async createProvider(provider) {
    const response = await api.post('/providers', provider)
    return response.data
  },
  
  async updateProvider(id, provider) {
    const response = await api.put(`/providers/${id}`, provider)
    return response.data
  },
  
  async deleteProvider(id) {
    // Use the v1 endpoint for delete since it's not available in portal endpoint
    // Get the API key from localStorage (stored during login)
    const apiKey = localStorage.getItem('apiKey')
    if (!apiKey) {
      throw new Error('No API key found. Please log in again.')
    }
    
    // Create a separate axios instance for API key authentication
    const deleteApi = axios.create({
      baseURL: '/api/v1',
      timeout: 10000,
      headers: {
        'Authorization': `Bearer ${apiKey}`
      }
    })
    
    const response = await deleteApi.delete(`/providers/${id}`)
    return response.data
  },
  
  async getStrategies() {
    const response = await api.get('/strategies')
    return response.data
  },
  
  async createStrategy(strategy) {
    const response = await api.post('/strategies', strategy)
    return response.data
  },
  
  async updateStrategy(id, strategy) {
    const response = await api.put(`/strategies/${id}`, strategy)
    return response.data
  },
  
  async deleteStrategy(id) {
    const response = await api.delete(`/strategies/${id}`)
    return response.data
  },
  
  async getSettings() {
    const response = await api.get('/settings')
    return response.data
  },
  
  async updateSettings(settings) {
    const response = await api.put('/settings', settings)
    return response.data
  },
  
  async validateProviderModels(config) {
    const response = await api.post('/providers/validate-models', config)
    return response.data
  },
  
  async checkProviderHealth(id) {
    const response = await api.post(`/providers/${id}/health`)
    return response.data
  },

  async getStrategyModels(strategyType) {
    const response = await api.get(`/strategy-models?strategy_type=${strategyType}`)
    return response.data
  },

  async activateStrategy(id) {
    const response = await api.post(`/strategies/${id}/activate`)
    return response.data
  },

  async deactivateStrategy(id) {
    const response = await api.post(`/strategies/${id}/deactivate`)
    return response.data
  },

  // API Key management
  async getApiKeys() {
    const response = await api.get('/api-keys')
    return response.data
  },

  async createApiKey(keyData) {
    const response = await api.post('/api-keys', keyData)
    return response.data
  },

  async updateApiKey(id, keyData) {
    const response = await api.put(`/api-keys/${id}`, keyData)
    return response.data
  },

  async deleteApiKey(id) {
    const response = await api.delete(`/api-keys/${id}`)
    return response.data
  },

  async getUserInfo() {
    const response = await api.get('/user-info')
    return response.data
  }
}