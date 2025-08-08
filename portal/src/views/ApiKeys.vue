<template>
  <div>
    <div class="page-header">
      <h1>API Keys</h1>
      <a-button type="primary" @click="showCreateModal">
        <plus-outlined />
        Generate API Key
      </a-button>
    </div>

    <a-table
      :columns="columns"
      :data-source="apiKeys"
      :loading="loading"
      :pagination="{ pageSize: 10 }"
      row-key="id"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'key_name'">
          <div>
            <div>{{ record.key_name }}</div>
            <div v-if="record.description" class="description">
              {{ record.description }}
            </div>
          </div>
        </template>

        <template v-if="column.key === 'api_key'">
          <div class="api-key-container">
            <span class="masked-key">{{ maskApiKey(record.api_key) }}</span>
            <a-button
              type="link"
              size="small"
              @click="copyApiKey(record.api_key)"
              class="copy-btn"
            >
              <copy-outlined />
            </a-button>
          </div>
        </template>

        <template v-if="column.key === 'expires_at'">
          <span v-if="record.expires_at" :class="{ 'expired': isExpired(record.expires_at) }">
            {{ formatDate(record.expires_at) }}
          </span>
          <span v-else class="unlimited">Unlimited</span>
        </template>

        <template v-if="column.key === 'is_admin'">
          <a-tag :color="record.is_admin ? 'red' : 'blue'">
            {{ record.is_admin ? 'Admin' : 'User' }}
          </a-tag>
        </template>

        <template v-if="column.key === 'is_active'">
          <a-switch
            :checked="record.is_active"
            :loading="togglingStatus[record.id] || false"
            @change="toggleKeyStatus(record)"
            :disabled="!currentUser?.is_admin"
            :checked-children="'Active'"
            :un-checked-children="'Inactive'"
          />
        </template>

        <template v-if="column.key === 'actions'">
          <a-space>
            <a-tooltip title="Edit API Key">
              <a-button
                type="link"
                size="small"
                @click="showEditModal(record)"
                :disabled="!currentUser?.is_admin"
              >
                <edit-outlined />
              </a-button>
            </a-tooltip>
            <a-tooltip title="Regenerate API Key">
              <a-popconfirm
                title="Are you sure you want to regenerate this API key? The old key will no longer work."
                @confirm="regenerateKey(record)"
                ok-text="Yes"
                cancel-text="No"
                :disabled="!currentUser?.is_admin"
              >
                <a-button
                  type="link"
                  size="small"
                  :disabled="!currentUser?.is_admin"
                  :loading="regeneratingKeys[record.id] || false"
                >
                  <reload-outlined />
                </a-button>
              </a-popconfirm>
            </a-tooltip>
            <a-tooltip title="Delete API Key">
              <a-popconfirm
                title="Are you sure you want to delete this API key? This action cannot be undone."
                @confirm="deleteApiKey(record.id)"
                ok-text="Yes"
                cancel-text="No"
                :disabled="!currentUser?.is_admin"
              >
                <a-button
                  type="link"
                  size="small"
                  danger
                  :disabled="!currentUser?.is_admin"
                  :loading="deletingKeys[record.id] || false"
                >
                  <delete-outlined />
                </a-button>
              </a-popconfirm>
            </a-tooltip>
          </a-space>
        </template>
      </template>
    </a-table>

    <ApiKeyModal
      ref="apiKeyModalRef"
      @success="loadApiKeys"
      @created="handleKeyCreated"
    />

    <!-- Modal to show newly created API key -->
    <a-modal
      v-model:visible="showKeyModal"
      title="API Key Generated"
      :width="600"
      :footer="null"
      @cancel="showKeyModal = false"
    >
      <div class="key-display">
        <p><strong>Key Name:</strong> {{ newKey?.key_name }}</p>
        <p><strong>API Key:</strong></p>
        <div class="api-key-box">
          <code>{{ newKey?.api_key }}</code>
          <a-button type="primary" @click="copyApiKey(newKey?.api_key)">
            <copy-outlined />
            Copy
          </a-button>
        </div>
        <p class="warning">
          <warning-outlined />
          Please save this API key now. You won't be able to see it again!
        </p>
      </div>
    </a-modal>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { message } from 'ant-design-vue'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CopyOutlined,
  ReloadOutlined,
  WarningOutlined
} from '@ant-design/icons-vue'
import api from '@/api'
import ApiKeyModal from '@/components/ApiKeyModal.vue'

export default {
  name: 'ApiKeys',
  components: {
    PlusOutlined,
    EditOutlined,
    DeleteOutlined,
    CopyOutlined,
    ReloadOutlined,
    WarningOutlined,
    ApiKeyModal
  },
  setup() {
    const loading = ref(false)
    const apiKeys = ref([])
    const apiKeyModalRef = ref()
    const showKeyModal = ref(false)
    const newKey = ref(null)
    const togglingStatus = ref({})
    const regeneratingKeys = ref({})
    const deletingKeys = ref({})
    
    const currentUser = computed(() => {
      const userStr = localStorage.getItem('user')
      return userStr ? JSON.parse(userStr) : null
    })

    const columns = [
      {
        title: 'Name',
        key: 'key_name',
        dataIndex: 'key_name'
      },
      {
        title: 'API Key',
        key: 'api_key',
        dataIndex: 'api_key'
      },
      {
        title: 'Expires',
        key: 'expires_at',
        dataIndex: 'expires_at'
      },
      {
        title: 'Type',
        key: 'is_admin',
        dataIndex: 'is_admin'
      },
      {
        title: 'Status',
        key: 'is_active',
        dataIndex: 'is_active'
      },
      {
        title: 'Actions',
        key: 'actions',
        width: 150
      }
    ]

    const loadApiKeys = async () => {
      try {
        loading.value = true
        apiKeys.value = await api.getApiKeys()
      } catch (error) {
        console.error('Error loading API keys:', error)
        message.error('Failed to load API keys')
      } finally {
        loading.value = false
      }
    }

    const showCreateModal = () => {
      apiKeyModalRef.value.show()
    }

    const showEditModal = (record) => {
      apiKeyModalRef.value.show(record)
    }

    const deleteApiKey = async (id) => {
      try {
        deletingKeys.value[id] = true
        await api.deleteApiKey(id)
        message.success('API key deleted successfully')
        loadApiKeys()
      } catch (error) {
        console.error('Error deleting API key:', error)
        message.error('Failed to delete API key')
      } finally {
        deletingKeys.value[id] = false
      }
    }

    const regenerateKey = async (record) => {
      try {
        regeneratingKeys.value[record.id] = true
        const response = await api.updateApiKey(record.id, { regenerate: true })
        message.success('API key regenerated successfully')
        // Show the new key to the user
        newKey.value = response
        showKeyModal.value = true
        loadApiKeys()
      } catch (error) {
        console.error('Error regenerating API key:', error)
        message.error('Failed to regenerate API key')
      } finally {
        regeneratingKeys.value[record.id] = false
      }
    }

    const toggleKeyStatus = async (record) => {
      try {
        togglingStatus.value[record.id] = true
        await api.updateApiKey(record.id, { is_active: !record.is_active })
        message.success(`API key ${record.is_active ? 'deactivated' : 'activated'} successfully`)
        loadApiKeys()
      } catch (error) {
        console.error('Error toggling API key status:', error)
        message.error('Failed to update API key status')
      } finally {
        togglingStatus.value[record.id] = false
      }
    }

    const handleKeyCreated = (key) => {
      newKey.value = key
      showKeyModal.value = true
      loadApiKeys()
    }

    const maskApiKey = (key) => {
      if (!key) return ''
      return key.slice(0, 8) + '...' + key.slice(-4)
    }

    const copyApiKey = async (key) => {
      try {
        await navigator.clipboard.writeText(key)
        message.success('API key copied to clipboard')
      } catch (error) {
        console.error('Error copying API key:', error)
        message.error('Failed to copy API key')
      }
    }

    const formatDate = (dateString) => {
      return new Date(dateString).toLocaleDateString()
    }

    const isExpired = (dateString) => {
      return new Date(dateString) < new Date()
    }

    onMounted(() => {
      loadApiKeys()
    })

    return {
      loading,
      apiKeys,
      columns,
      apiKeyModalRef,
      showKeyModal,
      newKey,
      currentUser,
      togglingStatus,
      regeneratingKeys,
      deletingKeys,
      loadApiKeys,
      showCreateModal,
      showEditModal,
      deleteApiKey,
      regenerateKey,
      toggleKeyStatus,
      handleKeyCreated,
      maskApiKey,
      copyApiKey,
      formatDate,
      isExpired
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

.description {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.api-key-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.masked-key {
  font-family: monospace;
  font-size: 12px;
  color: #666;
}

.copy-btn {
  padding: 0;
  height: auto;
}

.expired {
  color: #ff4d4f;
  font-weight: bold;
}

.unlimited {
  color: #52c41a;
  font-weight: bold;
}

.key-display {
  text-align: center;
}

.api-key-box {
  background: #f5f5f5;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 12px;
  margin: 12px 0;
  font-family: monospace;
  font-size: 14px;
  word-break: break-all;
}

.api-key-box code {
  display: block;
  margin-bottom: 12px;
}

.warning {
  color: #faad14;
  margin-top: 16px;
  font-size: 14px;
}

.warning .anticon {
  margin-right: 4px;
}
</style>