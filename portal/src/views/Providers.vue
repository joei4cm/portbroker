<template>
  <div>
    <div class="page-header">
      <h1>Providers</h1>
      <a-button type="primary" @click="showAddModal">
        <plus-outlined />
        Add Provider
      </a-button>
    </div>
    
    <a-table
      :columns="columns"
      :data-source="providers"
      :loading="loading"
      row-key="id"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag :color="record.is_active ? 'green' : 'red'">
            {{ record.is_active ? 'Active' : 'Inactive' }}
          </a-tag>
        </template>
        
        <template v-if="column.key === 'health'">
          <a-tooltip :title="getHealthTooltip(record)">
            <div 
              class="health-indicator" 
              :class="getHealthClass(record)"
              @click="checkProviderHealth(record)"
            >
              <div class="health-dot"></div>
            </div>
          </a-tooltip>
        </template>
        
        <template v-if="column.key === 'actions'">
          <a-space>
            <a-button type="link" size="small" @click="editProvider(record)">
              <edit-outlined />
            </a-button>
            <a-button type="link" size="small" danger @click="deleteProvider(record)">
              <delete-outlined />
            </a-button>
          </a-space>
        </template>
      </template>
    </a-table>
    
    <!-- Add/Edit Provider Modal -->
    <a-modal
      v-model:visible="modalVisible"
      :title="editingProvider ? 'Edit Provider' : 'Add Provider'"
      @ok="handleModalOk"
      @cancel="handleModalCancel"
      :ok-button-props="{ disabled: isSubmitting }"
      :confirm-loading="isSubmitting"
      width="800px"
    >
      <a-form
        :model="form"
        :rules="rules"
        ref="formRef"
        layout="vertical"
        @submit.prevent
      >
        <a-form-item label="Name" name="name">
          <a-input v-model:value="form.name" placeholder="Enter provider name" />
        </a-form-item>
        
        <a-form-item label="Provider Type" name="provider_type">
          <a-select 
            v-model:value="form.provider_type" 
            placeholder="Select provider type"
            @change="onProviderTypeChange"
          >
            <a-select-option value="openai">OpenAI</a-select-option>
            <a-select-option value="anthropic">Anthropic</a-select-option>
            <a-select-option value="google">Google Gemini</a-select-option>
            <a-select-option value="azure">Azure OpenAI</a-select-option>
            <a-select-option value="cohere">Cohere</a-select-option>
            <a-select-option value="mistral">Mistral</a-select-option>
            <a-select-option value="perplexity">Perplexity</a-select-option>
            <a-select-option value="custom">Custom (OpenAI Compatible)</a-select-option>
          </a-select>
        </a-form-item>
        
        <a-form-item label="Base URL" name="base_url">
          <a-input v-model:value="form.base_url" placeholder="Enter base URL" />
        </a-form-item>
        
        <a-form-item label="API Key" name="api_key">
          <a-input-password 
            v-model:value="form.api_key" 
            placeholder="Enter API key"
            :type="showApiKey ? 'text' : 'password'"
          >
            <template #suffix>
              <a-button 
                type="text" 
                size="small" 
                @click="showApiKey = !showApiKey"
              >
                <eye-outlined v-if="!showApiKey" />
                <eye-invisible-outlined v-else />
              </a-button>
            </template>
          </a-input-password>
        </a-form-item>
        
        <a-form-item label="SSL Verification">
          <a-switch v-model:checked="form.verify_ssl" />
          <span class="form-help-text">Disable if using self-signed certificates</span>
        </a-form-item>
        
        <a-form-item>
          <a-space>
            <a-button 
              type="primary" 
              @click="validateModels"
              :loading="validatingModels"
            >
              <search-outlined />
              Validate Models
            </a-button>
            <span class="form-help-text" v-if="availableModels.length > 0">
              {{ availableModels.length }} models found
            </span>
          </a-space>
        </a-form-item>
        
        <a-form-item label="Available Models" name="model_list">
          <a-select
            v-model:value="form.model_list"
            mode="multiple"
            placeholder="Select models (validate first)"
            :options="modelOptions"
            :filter-option="filterModelOption"
            :loading="validatingModels"
            :disabled="availableModels.length === 0"
          >
            <template #suffixIcon>
              <down-outlined />
            </template>
          </a-select>
        </a-form-item>
        
        <a-form-item label="Active">
          <a-switch v-model:checked="form.is_active" />
          <span class="form-help-text">Models will be available for strategies</span>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script>
import { message } from 'ant-design-vue'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  DownOutlined
} from '@ant-design/icons-vue'
import api from '@/api'

export default {
  name: 'Providers',
  components: {
    PlusOutlined,
    EditOutlined,
    DeleteOutlined,
    SearchOutlined,
    EyeOutlined,
    EyeInvisibleOutlined,
    DownOutlined
  },
  data() {
    return {
      loading: false,
      providers: [],
      modalVisible: false,
      editingProvider: null,
      formRef: null,
      showApiKey: false,
      validatingModels: false,
      isSubmitting: false,
      availableModels: [],
      healthStatus: {},
      form: {
        name: '',
        provider_type: 'openai',
        base_url: '',
        api_key: '',
        model_list: [],
        verify_ssl: true,
        is_active: true
      },
      rules: {
        name: [{ required: true, message: 'Please enter provider name' }],
        provider_type: [{ required: true, message: 'Please select provider type' }],
        base_url: [{ required: true, message: 'Please enter base URL' }],
        api_key: [{ required: true, message: 'Please enter API key' }],
        model_list: [{ required: true, message: 'Please select at least one model' }]
      },
      providerUrls: {
        openai: 'https://api.openai.com/v1',
        anthropic: 'https://api.anthropic.com/v1',
        google: 'https://generativelanguage.googleapis.com/v1beta',
        azure: 'https://your-resource.openai.azure.com/openai/deployments/your-deployment',
        cohere: 'https://api.cohere.com/v1',
        mistral: 'https://api.mistral.ai/v1',
        perplexity: 'https://api.perplexity.ai'
      },
      columns: [
        {
          title: 'Name',
          dataIndex: 'name',
          key: 'name'
        },
        {
          title: 'Provider Type',
          dataIndex: 'provider_type',
          key: 'provider_type'
        },
        {
          title: 'Base URL',
          dataIndex: 'base_url',
          key: 'base_url'
        },
        {
          title: 'Models',
          key: 'models',
          customRender: ({ record }) => {
            return record.model_list ? record.model_list.length : 0
          }
        },
        {
          title: 'Status',
          key: 'status'
        },
        {
          title: 'Health',
          key: 'health',
          width: 80
        },
        {
          title: 'Actions',
          key: 'actions',
          width: 120
        }
      ]
    }
  },
  async mounted() {
    await this.loadProviders()
  },
  
  updated() {
    // Ensure form reference is available when component updates
    this.$nextTick(() => {
      if (this.$refs && this.$refs.formRef) {
        this.formRef = this.$refs.formRef
      }
    })
  },
  computed: {
    modelOptions() {
      return this.availableModels.map(model => ({
        label: model,
        value: model
      }))
    }
  },
  methods: {
    async loadProviders() {
      this.loading = true
      try {
        const response = await api.getProviders()
        this.providers = response || []
      } catch (error) {
        message.error('Failed to load providers')
      } finally {
        this.loading = false
      }
    },
    
    showAddModal() {
      this.editingProvider = null
      this.resetForm()
      this.modalVisible = true
      
      // Ensure form reference is available after modal is shown
      this.$nextTick(() => {
        if (this.$refs && this.$refs.formRef) {
          this.formRef = this.$refs.formRef
        }
      })
    },
    
    editProvider(provider) {
      this.editingProvider = provider
      this.form = { ...provider }
      this.availableModels = provider.model_list || []
      this.modalVisible = true
      
      // Ensure form reference is available after modal is shown
      this.$nextTick(() => {
        if (this.$refs && this.$refs.formRef) {
          this.formRef = this.$refs.formRef
        }
      })
    },
    
    resetForm() {
      this.form = {
        name: '',
        provider_type: 'openai',
        base_url: '',
        api_key: '',
        model_list: [],
        verify_ssl: true,
        is_active: true
      }
      this.showApiKey = false
      this.availableModels = []
      this.validatingModels = false
      this.isSubmitting = false
    },
    
    onProviderTypeChange(value) {
      // Auto-populate URL based on provider type
      if (this.providerUrls[value]) {
        this.form.base_url = this.providerUrls[value]
      }
      // Clear models when provider type changes
      this.availableModels = []
      this.form.model_list = []
    },
    
    async validateModels() {
      if (!this.form.base_url || !this.form.api_key) {
        message.error('Please enter base URL and API key first')
        return
      }
      
      this.validatingModels = true
      try {
        const response = await api.validateProviderModels({
          provider_type: this.form.provider_type,
          base_url: this.form.base_url,
          api_key: this.form.api_key,
          verify_ssl: this.form.verify_ssl
        })
        
        if (response.success) {
          this.availableModels = response.models
          message.success(`Found ${response.models.length} models`)
        } else {
          message.error(`Validation failed: ${response.error}`)
        }
      } catch (error) {
        message.error('Failed to validate models')
      } finally {
        this.validatingModels = false
      }
    },
    
    filterModelOption(input, option) {
      return option.label.toLowerCase().includes(input.toLowerCase())
    },
    
    async handleModalOk() {
      // Prevent duplicate submissions
      if (this.isSubmitting) {
        return
      }
      
      this.isSubmitting = true
      
      try {
        // Wait for the form to be properly mounted
        await this.$nextTick()
        
        if (!this.formRef) {
          throw new Error('Form reference is not available')
        }
        
        await this.formRef.validate()
        
        // Check for duplicate names when creating new provider
        if (!this.editingProvider) {
          const existingProvider = this.providers.find(p => p.name === this.form.name)
          if (existingProvider) {
            throw new Error('Provider with this name already exists')
          }
        }
        
        // Check for duplicate names when editing (excluding current provider)
        if (this.editingProvider) {
          const duplicateProvider = this.providers.find(p => 
            p.name === this.form.name && p.id !== this.editingProvider.id
          )
          if (duplicateProvider) {
            throw new Error('Provider with this name already exists')
          }
        }
        
        // Refresh providers list to ensure we have the latest data
        await this.loadProviders()
        
        // Double-check for duplicates after refresh
        if (!this.editingProvider) {
          const existingProvider = this.providers.find(p => p.name === this.form.name)
          if (existingProvider) {
            throw new Error('Provider with this name already exists. Please refresh the page and try again.')
          }
        }
        
        if (this.editingProvider) {
          const duplicateProvider = this.providers.find(p => 
            p.name === this.form.name && p.id !== this.editingProvider.id
          )
          if (duplicateProvider) {
            throw new Error('Provider with this name already exists. Please refresh the page and try again.')
          }
        }
        
        const formData = { ...this.form }
        
        if (this.editingProvider) {
          await api.updateProvider(this.editingProvider.id, formData)
          message.success('Provider updated successfully')
        } else {
          await api.createProvider(formData)
          message.success('Provider created successfully')
        }
        
        this.modalVisible = false
        await this.loadProviders()
      } catch (error) {
        if (error.message) {
          message.error(`Validation failed: ${error.message}`)
        } else {
          message.error('Operation failed')
        }
      } finally {
        this.isSubmitting = false
      }
    },
    
    handleModalCancel() {
      this.modalVisible = false
      this.resetForm()
    },
    
    async deleteProvider(provider) {
      try {
        await api.deleteProvider(provider.id)
        message.success('Provider deleted successfully')
        await this.loadProviders()
      } catch (error) {
        message.error('Failed to delete provider')
      }
    },
    
    async checkProviderHealth(provider) {
      try {
        const response = await api.checkProviderHealth(provider.id)
        this.healthStatus[provider.id] = response
        
        if (response.healthy) {
          message.success('Provider is healthy')
        } else {
          message.error(`Provider health check failed: ${response.error}`)
        }
      } catch (error) {
        message.error('Failed to check provider health')
      }
    },
    
    getHealthClass(provider) {
      const health = this.healthStatus[provider.id]
      if (!health) return 'unknown'
      return health.healthy ? 'healthy' : 'unhealthy'
    },
    
    getHealthTooltip(provider) {
      const health = this.healthStatus[provider.id]
      if (!health) return 'Click to check health'
      
      if (health.healthy) {
        return `Healthy - ${health.response_time?.toFixed(2)}s response time`
      } else {
        return `Unhealthy - ${health.error}`
      }
    }
  }
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.health-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 4px;
  border-radius: 50%;
  transition: background-color 0.2s;
}

.health-indicator:hover {
  background-color: #f5f5f5;
}

.health-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #d9d9d9;
}

.health-indicator.healthy .health-dot {
  background-color: #52c41a;
}

.health-indicator.unhealthy .health-dot {
  background-color: #ff4d4f;
}

.health-indicator.unknown .health-dot {
  background-color: #d9d9d9;
}

.form-help-text {
  margin-left: 8px;
  color: #666;
  font-size: 12px;
}
</style>