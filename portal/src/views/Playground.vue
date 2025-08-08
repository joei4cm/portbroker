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
            
            <a-form-item label="API Key">
              <a-input-password
                v-model:value="form.apiKey"
                placeholder="Enter your API key"
                :disabled="loading"
              />
            </a-form-item>
            
            <a-form-item label="Endpoint">
              <a-select
                v-model:value="form.endpoint"
                placeholder="Select endpoint"
                @change="handleEndpointChange"
              >
                <a-select-option v-for="endpoint in currentEndpoints" :key="endpoint.path" :value="endpoint.path">
                  {{ endpoint.name }}
                </a-select-option>
              </a-select>
            </a-form-item>
            
            <a-form-item v-if="form.endpoint.includes('chat') || form.endpoint.includes('messages')" label="Model">
              <a-select
                v-model:value="form.model"
                placeholder="Select a model"
                show-search
                :filter-option="filterOption"
                :loading="loadingModels"
              >
                <a-select-option v-for="model in availableModels" :key="model.value" :value="model.value">
                  {{ model.label }}
                </a-select-option>
              </a-select>
            </a-form-item>
            
            <a-form-item v-if="form.endpoint.includes('chat')" label="Messages">
              <a-textarea
                v-model:value="form.messages"
                :rows="8"
                placeholder="Enter your conversation messages in JSON format"
              />
            </a-form-item>
            
            <a-form-item v-if="form.endpoint.includes('messages')" label="Messages">
              <a-textarea
                v-model:value="form.anthropicMessages"
                :rows="8"
                placeholder="Enter your conversation messages in JSON format"
              />
            </a-form-item>
            
            <a-form-item v-if="showTemperature" label="Temperature">
              <a-slider v-model:value="form.temperature" :min="0" :max="2" :step="0.1" />
              <span>{{ form.temperature }}</span>
            </a-form-item>
            
            <a-form-item v-if="showMaxTokens" label="Max Tokens">
              <a-input-number v-model:value="form.maxTokens" :min="1" :max="4000" />
            </a-form-item>
            
            <a-form-item v-if="form.endpoint.includes('embeddings')" label="Input">
              <a-textarea
                v-model:value="form.embeddingInput"
                :rows="4"
                placeholder="Enter text to embed"
              />
            </a-form-item>
            
            <a-form-item>
              <a-space>
                <a-button type="primary" @click="sendRequest" :loading="loading">
                  Send Request
                </a-button>
                <a-button @click="clearForm">Clear</a-button>
                <a-button v-if="form.endpoint.includes('chat') || form.endpoint.includes('messages')" @click="loadExample">
                  Load Example
                </a-button>
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
              <a-tab-pane key="streaming" tab="Streaming" v-if="streamingResponse">
                <div class="streaming-response">
                  <div v-for="(chunk, index) in streamingChunks" :key="index" class="streaming-chunk">
                    {{ chunk }}
                  </div>
                </div>
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
            <a-descriptions-item label="Strategy">
              {{ activeStrategy || '-' }}
            </a-descriptions-item>
          </a-descriptions>
        </a-card>
        
        <a-card title="Full Request" style="margin-top: 16px;">
          <a-tabs v-model:activeKey="requestTab">
            <a-tab-pane key="payload" tab="Payload">
              <pre class="request-json">{{ JSON.stringify(requestPayload, null, 2) }}</pre>
            </a-tab-pane>
            <a-tab-pane key="headers" tab="Headers">
              <pre class="request-json">{{ JSON.stringify(requestHeaders, null, 2) }}</pre>
            </a-tab-pane>
          </a-tabs>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script>
import { message } from 'ant-design-vue'
import api from '../api'

export default {
  name: 'Playground',
  data() {
    return {
      form: {
        apiType: 'openai',
        endpoint: '',
        apiKey: '',
        model: '',
        messages: JSON.stringify([
          { role: 'user', content: 'Hello, how are you?' }
        ], null, 2),
        anthropicMessages: JSON.stringify([
          { role: 'user', content: 'Hello, how are you?' }
        ], null, 2),
        temperature: 0.7,
        maxTokens: 1000,
        embeddingInput: 'Hello, world!'
      },
      availableModels: [],
      loadingModels: false,
      response: null,
      loading: false,
      requestStatus: null,
      responseTime: null,
      tokensUsed: null,
      activeStrategy: null,
      streamingResponse: false,
      streamingChunks: [],
      activeTab: 'formatted',
      requestTab: 'payload',
      requestPayload: null,
      requestHeaders: null,
      availableEndpoints: {
        openai: [
          { name: 'Chat Completions', path: '/v1/chat/completions' },
          { name: 'List Models', path: '/v1/models' },
          { name: 'Create Embeddings', path: '/v1/embeddings' },
          { name: 'Create Moderation', path: '/v1/moderations' }
        ],
        anthropic: [
          { name: 'Create Message', path: '/api/anthropic/v1/messages' },
          { name: 'List Models', path: '/api/anthropic/v1/models' },
          { name: 'Count Tokens', path: '/api/anthropic/v1/messages/count_tokens' }
        ]
      }
    }
  },
  computed: {
    showTemperature() {
      return this.form.endpoint.includes('chat') || this.form.endpoint.includes('messages')
    },
    showMaxTokens() {
      return this.form.endpoint.includes('chat') || this.form.endpoint.includes('messages')
    },
    currentEndpoints() {
      return this.availableEndpoints[this.form.apiType] || []
    },
    formattedResponse() {
      if (!this.response) return ''
      
      if (this.form.apiType === 'openai') {
        if (this.form.endpoint.includes('chat')) {
          return this.response.choices?.[0]?.message?.content || 'No content'
        } else if (this.form.endpoint.includes('embeddings')) {
          return JSON.stringify(this.response.data?.[0]?.embedding || [], null, 2)
        }
      } else {
        if (this.form.endpoint.includes('messages')) {
          return this.response.content?.[0]?.text || 'No content'
        } else if (this.form.endpoint.includes('count_tokens')) {
          return `Input tokens: ${this.response.input_tokens}`
        }
      }
      return JSON.stringify(this.response, null, 2)
    }
  },
  async mounted() {
    this.form.endpoint = this.availableEndpoints.openai[0].path
    await this.loadModels()
  },
  methods: {
    handleApiTypeChange() {
      this.form.endpoint = this.availableEndpoints[this.form.apiType][0].path
      this.loadModels()
    },
    
    handleEndpointChange() {
      this.loadModels()
    },
    
    filterOption(input, option) {
      return option.children.toLowerCase().indexOf(input.toLowerCase()) >= 0
    },
    
    async loadModels() {
      if (!this.form.endpoint.includes('models')) {
        this.loadingModels = true
        try {
          // Use strategy-based models endpoint
          const strategyType = this.form.apiType === 'openai' ? 'openai' : 'anthropic'
          const response = await api.getStrategyModels(strategyType)
          
          if (response && response.models) {
            this.availableModels = response.models.map(model => ({
              label: `${model.id} (${model.provider_name || 'Unknown'})`,
              value: model.id
            }))
          }
        } catch (error) {
          console.error('Failed to load models:', error)
          // Fallback to basic models
          this.availableModels = this.form.apiType === 'openai' ? [
            { label: 'gpt-3.5-turbo', value: 'gpt-3.5-turbo' },
            { label: 'gpt-4', value: 'gpt-4' }
          ] : [
            { label: 'claude-3-haiku', value: 'claude-3-haiku' },
            { label: 'claude-3-sonnet', value: 'claude-3-sonnet' },
            { label: 'claude-3-opus', value: 'claude-3-opus' }
          ]
        } finally {
          this.loadingModels = false
        }
      }
    },
    
    async sendRequest() {
      if (!this.form.apiKey) {
        message.error('Please enter your API key')
        return
      }
      
      if (!this.form.model && (this.form.endpoint.includes('chat') || this.form.endpoint.includes('messages'))) {
        message.error('Please select a model')
        return
      }
      
      let payload = {}
      let headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.form.apiKey}`
      }
      
      try {
        if (this.form.endpoint.includes('chat')) {
          const messages = JSON.parse(this.form.messages)
          if (!Array.isArray(messages)) {
            throw new Error('Messages must be an array')
          }
          payload = {
            model: this.form.model,
            messages: messages,
            temperature: this.form.temperature,
            max_tokens: this.form.maxTokens
          }
        } else if (this.form.endpoint.includes('messages')) {
          const messages = JSON.parse(this.form.anthropicMessages)
          if (!Array.isArray(messages)) {
            throw new Error('Messages must be an array')
          }
          payload = {
            model: this.form.model,
            messages: messages,
            max_tokens: this.form.maxTokens,
            temperature: this.form.temperature
          }
        } else if (this.form.endpoint.includes('embeddings')) {
          payload = {
            model: this.form.model || 'text-embedding-ada-002',
            input: this.form.embeddingInput
          }
        } else if (this.form.endpoint.includes('count_tokens')) {
          payload = {
            model: this.form.model,
            text: this.form.embeddingInput
          }
        }
        
        this.requestPayload = payload
        this.requestHeaders = headers
        
      } catch (e) {
        message.error('Invalid JSON format: ' + e.message)
        return
      }
      
      this.loading = true
      this.streamingResponse = false
      this.streamingChunks = []
      const startTime = Date.now()
      
      try {
        if (this.form.endpoint.includes('chat') && payload.stream) {
          await this.sendStreamingRequest(payload, headers)
        } else {
          // Use the correct API endpoint based on the type
          let endpoint = this.form.endpoint
          
          // Ensure endpoint is properly prefixed for the proxy
          if (!endpoint.startsWith('/api/')) {
            if (endpoint.startsWith('/v1/')) {
              endpoint = `/api${endpoint}`
            }
            // /api/anthropic/v1/ endpoints are already correctly prefixed
          }
          
          const response = await fetch(endpoint, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(payload)
          })
          
          this.responseTime = Date.now() - startTime
          this.response = await response.json()
          
          if (response.ok) {
            this.requestStatus = 'success'
            this.tokensUsed = this.response.usage?.total_tokens || 
                             this.response.usage?.input_tokens + this.response.usage?.output_tokens || 
                             'N/A'
            this.activeStrategy = this.response.strategy || 'Default'
            message.success('Request sent successfully')
          } else {
            this.requestStatus = 'error'
            message.error(`Request failed: ${this.response.error?.message || 'Unknown error'}`)
          }
        }
      } catch (error) {
        this.requestStatus = 'error'
        message.error('Network error: ' + error.message)
      } finally {
        this.loading = false
      }
    },
    
    async sendStreamingRequest(payload, headers) {
      this.streamingResponse = true
      // Use the correct API endpoint
      let endpoint = this.form.endpoint
      
      // Ensure endpoint is properly prefixed for the proxy
      if (!endpoint.startsWith('/api/')) {
        if (endpoint.startsWith('/v1/')) {
          endpoint = `/api${endpoint}`
        }
        // /api/anthropic/v1/ endpoints are already correctly prefixed
      }
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(payload)
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') {
              this.requestStatus = 'success'
              return
            }
            
            try {
              const parsed = JSON.parse(data)
              this.streamingChunks.push(parsed)
              
              if (parsed.choices && parsed.choices[0] && parsed.choices[0].delta) {
                const content = parsed.choices[0].delta.content
                if (content) {
                  // Update response with accumulated content
                  if (!this.response) {
                    this.response = { choices: [{ message: { content: '' } }] }
                  }
                  this.response.choices[0].message.content += content
                }
              }
              
              if (parsed.usage) {
                this.tokensUsed = parsed.usage.total_tokens || 'N/A'
              }
            } catch (e) {
              // Ignore parsing errors for streaming chunks
            }
          }
        }
      }
    },
    
    loadExample() {
      if (this.form.apiType === 'openai') {
        this.form.messages = JSON.stringify([
          { role: 'system', content: 'You are a helpful assistant.' },
          { role: 'user', content: 'What are the main benefits of using FastAPI for web development?' }
        ], null, 2)
      } else {
        this.form.anthropicMessages = JSON.stringify([
          { role: 'user', content: 'What are the main benefits of using FastAPI for web development?' }
        ], null, 2)
      }
      this.form.temperature = 0.7
      this.form.maxTokens = 1000
    },
    
    clearForm() {
      this.form = {
        ...this.form,
        model: '',
        messages: JSON.stringify([
          { role: 'user', content: 'Hello, how are you?' }
        ], null, 2),
        anthropicMessages: JSON.stringify([
          { role: 'user', content: 'Hello, how are you?' }
        ], null, 2),
        temperature: 0.7,
        maxTokens: 1000,
        embeddingInput: 'Hello, world!'
      }
      this.response = null
      this.requestStatus = null
      this.responseTime = null
      this.tokensUsed = null
      this.activeStrategy = null
      this.streamingResponse = false
      this.streamingChunks = []
      this.requestPayload = null
      this.requestHeaders = null
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

.request-json {
  background: #f9f9f9;
  padding: 12px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 11px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
}

.empty-response {
  text-align: center;
  color: #999;
  padding: 40px;
}

.streaming-response {
  background: #f0f9ff;
  border: 1px solid #e0f2fe;
  border-radius: 4px;
  padding: 16px;
  max-height: 400px;
  overflow-y: auto;
}

.streaming-chunk {
  margin-bottom: 8px;
  padding: 8px;
  background: white;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 11px;
  border-left: 3px solid #3b82f6;
}

.streaming-chunk:last-child {
  border-left-color: #10b981;
}
</style>