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
            
            <a-form-item v-if="showStreamToggle" label="Enable Streaming">
              <a-switch v-model:checked="form.stream" />
              <span style="margin-left: 8px;">{{ form.stream ? 'On' : 'Off' }}</span>
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
              <a-tab-pane key="preview" tab="Preview">
                <div class="preview-container">
                  <div v-if="streamingResponse" class="streaming-preview">
                    <div class="typing-content" v-html="formattedMarkdown"></div>
                    <div class="typing-indicator" v-if="isTyping">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                  <div v-else class="static-preview" v-html="formattedMarkdown"></div>
                </div>
              </a-tab-pane>
              <a-tab-pane key="raw" tab="Raw">
                <div class="raw-container">
                  <div v-if="streamingResponse" class="streaming-raw">
                    <div class="raw-header">
                      <strong>Streaming Response ({{ streamingChunks.length }} chunks)</strong>
                    </div>
                    <div class="raw-chunks">
                      <div v-for="(chunk, index) in streamingChunks" :key="index" class="raw-chunk">
                        <div class="chunk-header">Chunk {{ index + 1 }}</div>
                        <pre class="chunk-content">{{ JSON.stringify(chunk, null, 2) }}</pre>
                      </div>
                    </div>
                  </div>
                  <div v-else class="static-raw">
                    <pre class="raw-response">{{ JSON.stringify(response, null, 2) }}</pre>
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
import { marked } from 'marked'

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
        embeddingInput: 'Hello, world!',
        stream: false
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
      activeTab: 'preview',
      requestTab: 'payload',
      requestPayload: null,
      requestHeaders: null,
      currentTypingContent: '',
      isTyping: false,
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
    showStreamToggle() {
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
    },
    formattedMarkdown() {
      const content = this.streamingResponse ? this.currentTypingContent : this.formattedResponse
      return marked(content || 'No content')
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
              label: `${model.name} (${model.provider_name || 'Unknown'})`,
              value: `${model.name}|${model.provider_id}|${model.provider_name || 'Unknown'}`
            }))
          }
        } catch (error) {
          console.error('Failed to load models:', error)
          // Fallback to basic models
          this.availableModels = this.form.apiType === 'openai' ? [
            { label: 'gpt-3.5-turbo (Fallback)', value: 'gpt-3.5-turbo|fallback|Fallback' },
            { label: 'gpt-4 (Fallback)', value: 'gpt-4|fallback|Fallback' }
          ] : [
            { label: 'claude-3-haiku (Fallback)', value: 'claude-3-haiku|fallback|Fallback' },
            { label: 'claude-3-sonnet (Fallback)', value: 'claude-3-sonnet|fallback|Fallback' },
            { label: 'claude-3-opus (Fallback)', value: 'claude-3-opus|fallback|Fallback' }
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
        // Extract model name from the combined value (format: "modelName|providerId|providerName")
        const modelName = this.form.model.includes('|') ? this.form.model.split('|')[0] : this.form.model
        
        if (this.form.endpoint.includes('chat')) {
          const messages = JSON.parse(this.form.messages)
          if (!Array.isArray(messages)) {
            throw new Error('Messages must be an array')
          }
          payload = {
            model: modelName,
            messages: messages,
            temperature: this.form.temperature,
            max_tokens: this.form.maxTokens,
            stream: this.form.stream
          }
        } else if (this.form.endpoint.includes('messages')) {
          const messages = JSON.parse(this.form.anthropicMessages)
          if (!Array.isArray(messages)) {
            throw new Error('Messages must be an array')
          }
          payload = {
            model: modelName,
            messages: messages,
            max_tokens: this.form.maxTokens,
            temperature: this.form.temperature,
            stream: this.form.stream
          }
        } else if (this.form.endpoint.includes('embeddings')) {
          payload = {
            model: modelName || 'text-embedding-ada-002',
            input: this.form.embeddingInput
          }
        } else if (this.form.endpoint.includes('count_tokens')) {
          payload = {
            model: modelName,
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
        if ((this.form.endpoint.includes('chat') || this.form.endpoint.includes('messages')) && payload.stream) {
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
      this.activeTab = 'preview'  // Default to preview tab
      this.currentTypingContent = ''
      this.isTyping = true
      this.streamingChunks = []
      
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
        const errorText = await response.text()
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`)
      }
      
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let accumulatedContent = ''
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')
        
        let isAnthropicFormat = false
        let lastEventType = ''
        
        // Buffer for incomplete JSON data
        let jsonBuffer = ''
        
        for (const line of lines) {
          if (line.trim() === '') continue
          
          // Handle Anthropic SSE format - event lines
          if (line.startsWith('event: ')) {
            lastEventType = line.slice(7).trim()
            isAnthropicFormat = true
            continue
          }
          // Handle data lines (both OpenAI and Anthropic)
          else if (line.startsWith('data: ')) {
            const data = line.slice(6).trim()
            if (data === '[DONE]') {
              this.requestStatus = 'success'
              this.isTyping = false
              return
            }
            
            try {
              const parsed = JSON.parse(data)
              this.streamingChunks.push(parsed)
              
              if (isAnthropicFormat) {
                // Handle Anthropic format
                if (parsed.type === 'content_block_delta' && parsed.delta && parsed.delta.text) {
                  // Properly handle newlines by replacing escaped newlines with actual newlines
                  const content = parsed.delta.text.replace(/\\n/g, '\n')
                  accumulatedContent += content
                  this.currentTypingContent = accumulatedContent
                  
                  // Update response with accumulated content
                  if (!this.response) {
                    this.response = { content: [{ text: '' }] }
                  }
                  if (!this.response.content) {
                    this.response.content = [{ text: '' }]
                  }
                  this.response.content[0].text = accumulatedContent
                }
                
                // Handle message_start event (initial message setup)
                if (parsed.type === 'message_start' && parsed.message) {
                  if (!this.response) {
                    this.response = { content: [{ text: '' }] }
                  }
                }
                
                if (parsed.type === 'message_delta' && parsed.usage) {
                  this.tokensUsed = parsed.usage.input_tokens + parsed.usage.output_tokens || 'N/A'
                }
                
                if (parsed.type === 'message_stop') {
                  this.requestStatus = 'success'
                  this.isTyping = false
                  return
                }
              } else {
                // Handle OpenAI format - extract content from various delta fields
                if (parsed.choices && parsed.choices[0] && parsed.choices[0].delta) {
                  const delta = parsed.choices[0].delta
                  let content = ''
                  
                  // Handle different content fields in OpenAI delta
                  if (delta.content) {
                    content = delta.content.replace(/\\n/g, '\n')
                  } else if (delta.reasoning_content) {
                    content = delta.reasoning_content.replace(/\\n/g, '\n')
                  } else if (delta.role === 'assistant') {
                    // Skip role changes, they don't contain visible content
                    content = ''
                  }
                  
                  if (content) {
                    accumulatedContent += content
                    this.currentTypingContent = accumulatedContent
                    
                    // Update response with accumulated content
                    if (!this.response) {
                      this.response = { choices: [{ message: { content: '' } }] }
                    }
                    if (!this.response.choices) {
                      this.response.choices = [{ message: { content: '' } }]
                    }
                    if (!this.response.choices[0].message) {
                      this.response.choices[0].message = { content: '' }
                    }
                    this.response.choices[0].message.content = accumulatedContent
                  }
                }
                
                if (parsed.usage) {
                  this.tokensUsed = parsed.usage.total_tokens || 
                                   (parsed.usage.input_tokens + parsed.usage.output_tokens) || 
                                   'N/A'
                }
              }
            } catch (e) {
              // Handle incomplete JSON by buffering
              if (e instanceof SyntaxError && e.message.includes('Unexpected end of JSON')) {
                jsonBuffer += data
                // Try to parse the buffered data
                try {
                  const bufferedParsed = JSON.parse(jsonBuffer)
                  this.streamingChunks.push(bufferedParsed)
                  jsonBuffer = '' // Clear buffer on success
                } catch (bufferError) {
                  // Keep buffering until we get complete JSON
                  console.warn('Buffering incomplete JSON:', jsonBuffer)
                }
              } else {
                console.warn('Failed to parse chunk:', data, e)
                jsonBuffer = '' // Clear buffer on other errors
              }
            }
          }
        }
        
        this.isTyping = false
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
        embeddingInput: 'Hello, world!',
        stream: false
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
      this.currentTypingContent = ''
      this.isTyping = false
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

.streaming-header {
  padding: 12px;
  background: #e6f7ff;
  border-radius: 4px;
  margin-bottom: 16px;
  color: #1890ff;
}

.streaming-content {
  margin-bottom: 20px;
}

.accumulated-content {
  padding: 12px;
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  border-radius: 4px;
  margin-bottom: 16px;
}

.content-display {
  margin-top: 8px;
  font-family: 'Courier New', monospace;
  white-space: pre-wrap;
  background: white;
  padding: 12px;
  border-radius: 4px;
  border: 1px solid #d9d9d9;
}

.streaming-chunks {
  border-top: 1px solid #f0f0f0;
  padding-top: 16px;
}

.streaming-chunks h4 {
  color: #666;
  margin-bottom: 12px;
}

.streaming-chunk small {
  color: #666;
  display: block;
  margin-bottom: 4px;
}

.streaming-chunk pre {
  margin: 0;
  font-size: 10px;
}

.combined-streaming-view {
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  max-height: 600px;
  overflow-y: auto;
}

.combined-header {
  text-align: center;
  padding: 12px;
  background: #1890ff;
  color: white;
  border-radius: 6px;
  margin-bottom: 16px;
  font-weight: bold;
}

.combined-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.formatted-section, .raw-section {
  background: white;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  padding: 12px;
}

.formatted-section h4, .raw-section h4 {
  margin: 0 0 8px 0;
  color: #333;
  font-size: 14px;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 8px;
}

.typing-display {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  min-height: 60px;
  white-space: pre-wrap;
  word-break: break-word;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 4px;
  border: 1px solid #e8e8e8;
}

.typing-cursor {
  color: #1890ff;
  font-weight: bold;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.raw-display {
  font-family: 'Courier New', monospace;
  font-size: 11px;
  line-height: 1.4;
  max-height: 200px;
  overflow-y: auto;
  background: #f5f5f5;
  border-radius: 4px;
  padding: 12px;
  border: 1px solid #e8e8e8;
}

.raw-display pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.streaming-stats {
  display: flex;
  justify-content: space-around;
  background: white;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  padding: 12px;
  font-size: 12px;
}

.stat-item {
  text-align: center;
}

.stat-item strong {
  display: block;
  color: #666;
  margin-bottom: 4px;
}

/* Preview Tab Styles */
.preview-container {
  max-height: 500px;
  overflow-y: auto;
}

.streaming-preview {
  position: relative;
  min-height: 100px;
}

.typing-content {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  line-height: 1.6;
  font-size: 14px;
  color: #333;
}

.typing-content h1, .typing-content h2, .typing-content h3 {
  margin-top: 0;
  margin-bottom: 16px;
  color: #1890ff;
}

.typing-content p {
  margin-bottom: 12px;
}

.typing-content code {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.typing-content pre {
  background: #f5f5f5;
  padding: 16px;
  border-radius: 6px;
  border-left: 4px solid #1890ff;
  overflow-x: auto;
  margin: 16px 0;
}

.typing-content blockquote {
  border-left: 4px solid #1890ff;
  padding-left: 16px;
  margin: 16px 0;
  color: #666;
  font-style: italic;
}

.typing-indicator {
  display: inline-flex;
  align-items: center;
  margin-left: 4px;
}

.typing-indicator span {
  height: 8px;
  width: 8px;
  background-color: #1890ff;
  border-radius: 50%;
  display: inline-block;
  margin: 0 2px;
  animation: typing 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-indicator span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.static-preview {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  line-height: 1.6;
  font-size: 14px;
  color: #333;
}

/* Raw Tab Styles */
.raw-container {
  max-height: 500px;
  overflow-y: auto;
}

.raw-header {
  background: #f0f0f0;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 14px;
  color: #666;
}

.raw-chunks {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.raw-chunk {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
}

.chunk-header {
  background: #f8f9fa;
  padding: 8px 12px;
  font-size: 12px;
  color: #666;
  border-bottom: 1px solid #e0e0e0;
  font-weight: 500;
}

.chunk-content {
  margin: 0;
  padding: 12px;
  font-family: 'Courier New', monospace;
  font-size: 11px;
  line-height: 1.4;
  background: #fafafa;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
}

.static-raw {
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 16px;
}

.raw-response {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}

/* Responsive design */
@media (max-width: 768px) {
  .preview-container,
  .raw-container {
    max-height: 400px;
  }
  
  .typing-content,
  .static-preview {
    font-size: 13px;
  }
  
  .chunk-content {
    font-size: 10px;
  }
}
</style>