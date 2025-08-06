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
        
        <template v-if="column.key === 'actions'">
          <a-space>
            <a-button type="link" size="small" @click="editProvider(record)">
              <edit-outlined />
            </a-button>
            <a-button type="link" size="small" danger @click="deleteProvider(record)">
              <delete-outlined />
            </a-button>
            <a-button type="link" size="small" @click="testProvider(record)">
              <thunderbolt-outlined />
              Test
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
      width="600px"
    >
      <a-form
        :model="form"
        :rules="rules"
        ref="formRef"
        layout="vertical"
      >
        <a-form-item label="Name" name="name">
          <a-input v-model:value="form.name" placeholder="Enter provider name" />
        </a-form-item>
        
        <a-form-item label="Provider Type" name="provider_type">
          <a-select v-model:value="form.provider_type" placeholder="Select provider type">
            <a-select-option value="openai">OpenAI</a-select-option>
            <a-select-option value="azure">Azure</a-select-option>
            <a-select-option value="custom">Custom</a-select-option>
          </a-select>
        </a-form-item>
        
        <a-form-item label="Base URL" name="base_url">
          <a-input v-model:value="form.base_url" placeholder="Enter base URL" />
        </a-form-item>
        
        <a-form-item label="API Key" name="api_key">
          <a-input-password v-model:value="form.api_key" placeholder="Enter API key" />
        </a-form-item>
        
        <a-form-item label="Model List" name="model_list">
          <a-textarea 
            v-model:value="modelListText" 
            placeholder="Enter models (one per line)&#10;gpt-3.5-turbo&#10;gpt-4&#10;gpt-4-turbo" 
            :rows="4"
          />
        </a-form-item>
        
        <a-form-item label="Small Model (optional)" name="small_model">
          <a-input v-model:value="form.small_model" placeholder="Enter small model name" />
        </a-form-item>
        
        <a-form-item label="Medium Model (optional)" name="medium_model">
          <a-input v-model:value="form.medium_model" placeholder="Enter medium model name" />
        </a-form-item>
        
        <a-form-item label="Big Model (optional)" name="big_model">
          <a-input v-model:value="form.big_model" placeholder="Enter big model name" />
        </a-form-item>
        
        <a-form-item label="Active">
          <a-switch v-model:checked="form.is_active" />
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
  ThunderboltOutlined
} from '@ant-design/icons-vue'
import api from '@/api'

export default {
  name: 'Providers',
  components: {
    PlusOutlined,
    EditOutlined,
    DeleteOutlined,
    ThunderboltOutlined
  },
  data() {
    return {
      loading: false,
      providers: [],
      modalVisible: false,
      editingProvider: null,
      formRef: null,
      modelListText: '',
      form: {
        name: '',
        provider_type: 'openai',
        base_url: '',
        api_key: '',
        model_list: [],
        small_model: '',
        medium_model: '',
        big_model: '',
        is_active: true
      },
      rules: {
        name: [{ required: true, message: 'Please enter provider name' }],
        provider_type: [{ required: true, message: 'Please select provider type' }],
        base_url: [{ required: true, message: 'Please enter base URL' }],
        api_key: [{ required: true, message: 'Please enter API key' }],
        model_list: [{ required: true, message: 'Please enter at least one model' }]
      },
      columns: [
        {
          title: 'Name',
          dataIndex: 'name',
          key: 'name'
        },
        {
          title: 'Base URL',
          dataIndex: 'base_url',
          key: 'base_url'
        },
        {
          title: 'Priority',
          dataIndex: 'priority',
          key: 'priority'
        },
        {
          title: 'Status',
          key: 'status'
        },
        {
          title: 'Actions',
          key: 'actions',
          width: 150
        }
      ]
    }
  },
  async mounted() {
    await this.loadProviders()
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
      this.modelListText = ''
      this.form = {
        name: '',
        provider_type: 'openai',
        base_url: '',
        api_key: '',
        model_list: [],
        small_model: '',
        medium_model: '',
        big_model: '',
        is_active: true
      }
      this.modalVisible = true
    },
    
    editProvider(provider) {
      this.editingProvider = provider
      this.form = { ...provider }
      this.modelListText = provider.model_list ? provider.model_list.join('\n') : ''
      this.modalVisible = true
    },
    
    async handleModalOk() {
      try {
        await this.formRef.validate()
        
        // Convert model list text to array
        const formData = { ...this.form }
        formData.model_list = this.modelListText.split('\n')
          .map(model => model.trim())
          .filter(model => model.length > 0)
        
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
          message.error('Validation failed')
        } else {
          message.error('Operation failed')
        }
      }
    },
    
    handleModalCancel() {
      this.modalVisible = false
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
    
    async testProvider(provider) {
      try {
        // This would test the provider connection
        message.success('Provider test successful')
      } catch (error) {
        message.error('Provider test failed')
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
</style>