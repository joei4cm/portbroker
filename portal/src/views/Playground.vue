<template>
  <div>
    <h1>API Playground</h1>
    
    <a-row :gutter="16">
      <a-col :span="12">
        <a-card title="Request Configuration">
          <a-form :model="form" layout="vertical">
            <a-form-item label="API Type">
              <a-radio-group v-model:value="form.apiType" @change="handleApiTypeChange">
                <a-radio value="openai">OpenAI Compatible</a-radio>
                <a-radio value="anthropic">Anthropic Compatible</a-radio>
              </a-radio-group>
            </a-form-item>
            
            <a-form-item label="Endpoint">
              <a-input v-model:value="form.endpoint" disabled />
            </a-form-item>
            
            <a-form-item label="Model">
              <a-select
                v-model:value="form.model"
                placeholder="Select a model"
                show-search
                :filter-option="filterOption"
              >
                <a-select-option v-for="model in availableModels" :key="model.value" :value="model.value">
                  {{ model.label }}
                </a-select-option>
              </a-select>
            </a-form-item>
            
            <a-form-item label="Messages">
              <a-textarea
                v-model:value="form.messages"
                :rows="8"
                placeholder="Enter your conversation messages in JSON format"
              />
            </a-form-item>
            
            <a-form-item label="Temperature">
              <a-slider v-model:value="form.temperature" :min="0" :max="2" :step="0.1" />
              <span>{{ form.temperature }}</span>
            </a-form-item>
            
            <a-form-item label="Max Tokens">
              <a-input-number v-model:value="form.maxTokens" :min="1" :max="4000" />
            </a-form-item>
            
            <a-form-item>
              <a-space>
                <a-button type="primary" @click="sendRequest" :loading="loading">
                  Send Request
                </a-button>
                <a-button @click="clearForm">Clear</a-button>
              </a-space>
            </a-form-item>
          </a-form>
        </a-card>
      </a-col>
      
      <a-col :span="12">
        <a-card title="Response">
          <div v-if="response" class="response-container">
            <a-tabs v-model:activeKey="activeTab">
              <a-tab-pane key="formatted" tab="Formatted">
                <pre class="response-json">{{ formattedResponse }}</pre>
              </a-tab-pane>
              <a-tab-pane key="raw" tab="Raw">
                <pre class="response-json">{{ JSON.stringify(response, null, 2) }}</pre>
              </a-tab-pane>
            </a-tabs>
          </div>
          <div v-else class="empty-response">
            <p>Send a request to see the response here</p>
          </div>
        </a-card>
        
        <a-card title="Request Details" style="margin-top: 16px;">
          <a-descriptions :column="1" size="small">
            <a-descriptions-item label="Status">
              <a-tag :color="requestStatus === 'success' ? 'green' : 'red'">
                {{ requestStatus || 'No request sent' }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="Response Time">
              {{ responseTime || '-' }}ms
            </a-descriptions-item>
            <a-descriptions-item label="Tokens Used">
              {{ tokensUsed || '-' }}
            </a-descriptions-item>
          </a-descriptions>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script>
import { message } from 'ant-design-vue'

export default {
  name: 'Playground',
  data() {
    return {
      form: {
        apiType: 'openai',
        endpoint: '/v1/chat/completions',
        model: '',
        messages: JSON.stringify([
          { role: 'user', content: 'Hello, how are you?' }
        ], null, 2),
        temperature: 0.7,
        maxTokens: 1000
      },
      availableModels: [
        { label: 'OpenAI - gpt-3.5-turbo', value: 'gpt-3.5-turbo' },
        { label: 'OpenAI - gpt-4', value: 'gpt-4' },
        { label: 'Anthropic - claude-3-haiku', value: 'claude-3-haiku' },
        { label: 'Anthropic - claude-3-sonnet', value: 'claude-3-sonnet' },
        { label: 'Anthropic - claude-3-opus', value: 'claude-3-opus' }
      ],
      response: null,
      loading: false,
      requestStatus: null,
      responseTime: null,
      tokensUsed: null,
      activeTab: 'formatted'
    }
  },
  computed: {
    formattedResponse() {
      if (!this.response) return ''
      
      if (this.form.apiType === 'openai') {
        return this.response.choices?.[0]?.message?.content || 'No content'
      } else {
        return this.response.content?.[0]?.text || 'No content'
      }
    }
  },
  methods: {
    handleApiTypeChange() {
      this.form.endpoint = this.form.apiType === 'openai' 
        ? '/v1/chat/completions' 
        : '/api/anthropic/v1/messages'
    },
    
    filterOption(input, option) {
      return option.children.toLowerCase().indexOf(input.toLowerCase()) >= 0
    },
    
    async sendRequest() {
      if (!this.form.model) {
        message.error('Please select a model')
        return
      }
      
      try {
        const messages = JSON.parse(this.form.messages)
        if (!Array.isArray(messages)) {
          throw new Error('Messages must be an array')
        }
      } catch (e) {
        message.error('Invalid JSON format for messages')
        return
      }
      
      this.loading = true
      const startTime = Date.now()
      
      try {
        const payload = {
          model: this.form.model,
          messages: JSON.parse(this.form.messages),
          temperature: this.form.temperature,
          max_tokens: this.form.maxTokens
        }
        
        const response = await fetch(this.form.endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token') || 'demo-token'}`
          },
          body: JSON.stringify(payload)
        })
        
        this.responseTime = Date.now() - startTime
        this.response = await response.json()
        
        if (response.ok) {
          this.requestStatus = 'success'
          this.tokensUsed = this.response.usage?.total_tokens || 'N/A'
          message.success('Request sent successfully')
        } else {
          this.requestStatus = 'error'
          message.error(`Request failed: ${this.response.error?.message || 'Unknown error'}`)
        }
      } catch (error) {
        this.requestStatus = 'error'
        message.error('Network error: ' + error.message)
      } finally {
        this.loading = false
      }
    },
    
    clearForm() {
      this.form = {
        ...this.form,
        model: '',
        messages: JSON.stringify([
          { role: 'user', content: 'Hello, how are you?' }
        ], null, 2),
        temperature: 0.7,
        maxTokens: 1000
      }
      this.response = null
      this.requestStatus = null
      this.responseTime = null
      this.tokensUsed = null
    }
  }
}
</script>

<style scoped>
.response-container {
  max-height: 400px;
  overflow-y: auto;
}

.response-json {
  background: #f5f5f5;
  padding: 16px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

.empty-response {
  text-align: center;
  color: #999;
  padding: 40px;
}
</style>