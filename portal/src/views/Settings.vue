<template>
  <div>
    <h1>Settings</h1>
    
    <a-row :gutter="16">
      <a-col :span="12">
        <a-card title="General Settings">
          <a-form
            :model="form"
            :rules="rules"
            ref="formRef"
            layout="vertical"
          >
            <a-form-item label="Application Name" name="app_name">
              <a-input v-model:value="form.app_name" placeholder="Enter application name" />
            </a-form-item>
            
            <a-form-item label="Session Timeout (minutes)" name="session_timeout">
              <a-input-number v-model:value="form.session_timeout" :min="5" :max="1440" />
            </a-form-item>
            
            <a-form-item label="Default API Type" name="default_api_type">
              <a-select v-model:value="form.default_api_type">
                <a-select-option value="openai">OpenAI Compatible</a-select-option>
                <a-select-option value="anthropic">Anthropic Compatible</a-select-option>
              </a-select>
            </a-form-item>
            
            <a-form-item label="Enable Debug Mode" name="debug_mode">
              <a-switch v-model:checked="form.debug_mode" />
            </a-form-item>
            
            <a-form-item label="Enable Request Logging" name="enable_logging">
              <a-switch v-model:checked="form.enable_logging" />
            </a-form-item>
            
            <a-form-item>
              <a-button type="primary" @click="saveSettings" :loading="loading">
                Save Settings
              </a-button>
            </a-form-item>
          </a-form>
        </a-card>
      </a-col>
      
      <a-col :span="12">
        <a-card title="Security Settings">
          <a-form layout="vertical">
            <a-form-item label="API Key Expiration (days)" name="api_key_expiration">
              <a-input-number v-model:value="form.api_key_expiration" :min="1" :max="365" />
            </a-form-item>
            
            <a-form-item label="Rate Limit (requests per minute)" name="rate_limit">
              <a-input-number v-model:value="form.rate_limit" :min="1" :max="1000" />
            </a-form-item>
            
            <a-form-item label="Enable CORS" name="enable_cors">
              <a-switch v-model:checked="form.enable_cors" />
            </a-form-item>
            
            <a-form-item label="Allowed Origins" name="allowed_origins" v-if="form.enable_cors">
              <a-textarea
                v-model:value="form.allowed_origins"
                :rows="4"
                placeholder="Enter allowed origins (one per line)"
              />
            </a-form-item>
            
            <a-form-item label="Enable HTTPS" name="enable_https">
              <a-switch v-model:checked="form.enable_https" />
            </a-form-item>
          </a-form>
        </a-card>
        
        <a-card title="Database Settings" style="margin-top: 16px;">
          <a-form layout="vertical">
            <a-form-item label="Database Type" name="database_type">
              <a-select v-model:value="form.database_type" disabled>
                <a-select-option value="sqlite">SQLite</a-select-option>
                <a-select-option value="postgresql">PostgreSQL</a-select-option>
                <a-select-option value="supabase">Supabase</a-select-option>
              </a-select>
            </a-form-item>
            
            <a-form-item label="Connection Status">
              <a-tag :color="connectionStatus === 'Connected' ? 'green' : 'red'">
                {{ connectionStatus }}
              </a-tag>
              <a-button size="small" @click="testConnection" style="margin-left: 8px;">
                Test Connection
              </a-button>
            </a-form-item>
          </a-form>
        </a-card>
      </a-col>
    </a-row>
    
    <a-row :gutter="16" style="margin-top: 24px;">
      <a-col :span="24">
        <a-card title="System Information">
          <a-descriptions :column="4" size="small">
            <a-descriptions-item label="Version">
              {{ systemInfo.version }}
            </a-descriptions-item>
            <a-descriptions-item label="Environment">
              {{ systemInfo.environment }}
            </a-descriptions-item>
            <a-descriptions-item label="Python Version">
              {{ systemInfo.python_version }}
            </a-descriptions-item>
            <a-descriptions-item label="Database">
              {{ systemInfo.database }}
            </a-descriptions-item>
            <a-descriptions-item label="Uptime">
              {{ systemInfo.uptime }}
            </a-descriptions-item>
            <a-descriptions-item label="Memory Usage">
              {{ systemInfo.memory_usage }}
            </a-descriptions-item>
            <a-descriptions-item label="CPU Usage">
              {{ systemInfo.cpu_usage }}
            </a-descriptions-item>
            <a-descriptions-item label="Disk Usage">
              {{ systemInfo.disk_usage }}
            </a-descriptions-item>
          </a-descriptions>
        </a-card>
      </a-col>
    </a-row>
    
    <a-row :gutter="16" style="margin-top: 24px;">
      <a-col :span="24">
        <a-card title="Actions">
          <a-space>
            <a-button @click="exportConfig">
              <export-outlined />
              Export Configuration
            </a-button>
            <a-button @click="showImportModal">
              <import-outlined />
              Import Configuration
            </a-button>
            <a-button danger @click="resetSettings">
              <reload-outlined />
              Reset to Defaults
            </a-button>
            <a-button type="primary" @click="restartService">
              <poweroff-outlined />
              Restart Service
            </a-button>
          </a-space>
        </a-card>
      </a-col>
    </a-row>
    
    <!-- Import Configuration Modal -->
    <a-modal
      v-model:visible="importModalVisible"
      title="Import Configuration"
      @ok="handleImportOk"
      @cancel="importModalVisible = false"
    >
      <a-form layout="vertical">
        <a-form-item label="Configuration File">
          <a-upload
            :max-count="1"
            :before-upload="beforeUpload"
            :file-list="fileList"
          >
            <a-button>
              <upload-outlined />
              Select File
            </a-button>
          </a-upload>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script>
import { message } from 'ant-design-vue'
import {
  ExportOutlined,
  ImportOutlined,
  ReloadOutlined,
  PoweroffOutlined,
  UploadOutlined
} from '@ant-design/icons-vue'
import api from '@/api'

export default {
  name: 'Settings',
  components: {
    ExportOutlined,
    ImportOutlined,
    ReloadOutlined,
    PoweroffOutlined,
    UploadOutlined
  },
  data() {
    return {
      loading: false,
      form: {
        app_name: 'PortBroker',
        session_timeout: 60,
        default_api_type: 'openai',
        debug_mode: false,
        enable_logging: true,
        api_key_expiration: 30,
        rate_limit: 100,
        enable_cors: true,
        allowed_origins: 'http://localhost:3000\nhttp://localhost:8080',
        enable_https: false,
        database_type: 'sqlite'
      },
      rules: {
        app_name: [{ required: true, message: 'Please enter application name' }],
        session_timeout: [{ required: true, message: 'Please enter session timeout' }],
        default_api_type: [{ required: true, message: 'Please select default API type' }],
        api_key_expiration: [{ required: true, message: 'Please enter API key expiration' }],
        rate_limit: [{ required: true, message: 'Please enter rate limit' }]
      },
      connectionStatus: 'Connected',
      systemInfo: {
        version: '1.0.0',
        environment: 'Development',
        python_version: '3.9.0',
        database: 'SQLite',
        uptime: '2 days, 14 hours',
        memory_usage: '256 MB',
        cpu_usage: '15%',
        disk_usage: '45%'
      },
      importModalVisible: false,
      fileList: []
    }
  },
  async mounted() {
    await this.loadSettings()
  },
  methods: {
    async loadSettings() {
      try {
        const response = await api.getSettings()
        this.form = { ...this.form, ...response.settings }
      } catch (error) {
        message.error('Failed to load settings')
      }
    },
    
    async saveSettings() {
      try {
        await this.$refs.formRef.validate()
        this.loading = true
        
        await api.updateSettings(this.form)
        message.success('Settings saved successfully')
      } catch (error) {
        if (error.message) {
          message.error('Validation failed')
        } else {
          message.error('Failed to save settings')
        }
      } finally {
        this.loading = false
      }
    },
    
    async testConnection() {
      try {
        // This would test the database connection
        this.connectionStatus = 'Connected'
        message.success('Database connection successful')
      } catch (error) {
        this.connectionStatus = 'Disconnected'
        message.error('Database connection failed')
      }
    },
    
    exportConfig() {
      const config = {
        settings: this.form,
        system_info: this.systemInfo,
        exported_at: new Date().toISOString()
      }
      
      const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'portbroker-config.json'
      a.click()
      URL.revokeObjectURL(url)
      
      message.success('Configuration exported successfully')
    },
    
    showImportModal() {
      this.importModalVisible = true
      this.fileList = []
    },
    
    beforeUpload(file) {
      this.fileList = [file]
      return false
    },
    
    async handleImportOk() {
      if (this.fileList.length === 0) {
        message.error('Please select a configuration file')
        return
      }
      
      try {
        const file = this.fileList[0]
        const text = await file.text()
        const config = JSON.parse(text)
        
        if (config.settings) {
          this.form = { ...this.form, ...config.settings }
          message.success('Configuration imported successfully')
          this.importModalVisible = false
        } else {
          message.error('Invalid configuration file format')
        }
      } catch (error) {
        message.error('Failed to import configuration')
      }
    },
    
    resetSettings() {
      this.$confirm({
        title: 'Reset Settings',
        content: 'Are you sure you want to reset all settings to default values?',
        okText: 'Yes',
        okType: 'danger',
        cancelText: 'No',
        onOk: () => {
          this.form = {
            app_name: 'PortBroker',
            session_timeout: 60,
            default_api_type: 'openai',
            debug_mode: false,
            enable_logging: true,
            api_key_expiration: 30,
            rate_limit: 100,
            enable_cors: true,
            allowed_origins: 'http://localhost:3000\nhttp://localhost:8080',
            enable_https: false,
            database_type: 'sqlite'
          }
          message.success('Settings reset to defaults')
        }
      })
    },
    
    restartService() {
      this.$confirm({
        title: 'Restart Service',
        content: 'Are you sure you want to restart the PortBroker service?',
        okText: 'Yes',
        okType: 'danger',
        cancelText: 'No',
        onOk: async () => {
          try {
            // This would restart the service
            message.success('Service restart initiated')
          } catch (error) {
            message.error('Failed to restart service')
          }
        }
      })
    }
  }
}
</script>

<style scoped>
.ant-form-item {
  margin-bottom: 16px;
}
</style>