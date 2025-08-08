<template>
  <a-modal
    v-model:visible="visible"
    :title="isEdit ? 'Edit API Key' : 'Generate API Key'"
    :width="600"
    @ok="handleSubmit"
    @cancel="handleCancel"
  >
    <a-form
      :model="formState"
      :rules="rules"
      ref="formRef"
      layout="vertical"
    >
      <a-form-item label="Key Name" name="key_name">
        <a-input
          v-model:value="formState.key_name"
          placeholder="Enter key name"
          :disabled="isEdit"
        />
      </a-form-item>

      <a-form-item label="Description" name="description">
        <a-textarea
          v-model:value="formState.description"
          placeholder="Enter description"
          :rows="3"
        />
      </a-form-item>

      <a-form-item label="Expiration (days)" name="expires_in_days">
        <a-input-number
          v-model:value="formState.expires_in_days"
          placeholder="Leave blank for unlimited"
          :min="1"
          style="width: 100%"
        />
      </a-form-item>

      <a-form-item label="Admin Key" name="is_admin">
        <a-switch
          v-model:checked="formState.is_admin"
          :checked-children="'Admin'"
          :un-checked-children="'User'"
        />
      </a-form-item>

      <a-form-item label="Active" name="is_active">
        <a-switch
          v-model:checked="formState.is_active"
          :checked-children="'Active'"
          :un-checked-children="'Inactive'"
        />
      </a-form-item>
    </a-form>

    <template #footer>
      <a-button @click="handleCancel">Cancel</a-button>
      <a-button type="primary" @click="handleSubmit" :loading="loading">
        {{ isEdit ? 'Update' : 'Generate' }}
      </a-button>
    </template>
  </a-modal>
</template>

<script>
import { message } from 'ant-design-vue'
import api from '@/api'

export default {
  name: 'ApiKeyModal',
  data() {
    return {
      visible: false,
      loading: false,
      isEdit: false,
      editId: null,
      formState: {
        key_name: '',
        description: '',
        expires_in_days: null,
        is_admin: false,
        is_active: true
      },
      rules: {
        key_name: [
          { required: true, message: 'Please enter key name', trigger: 'blur' }
        ]
      }
    }
  },
  methods: {
    show(data = null) {
      this.visible = true
      this.isEdit = !!data
      
      if (data) {
        this.editId = data.id
        this.formState = {
          key_name: data.key_name,
          description: data.description,
          expires_in_days: data.expires_in_days,
          is_admin: data.is_admin,
          is_active: data.is_active
        }
      } else {
        this.editId = null
        this.formState = {
          key_name: '',
          description: '',
          expires_in_days: null,
          is_admin: false,
          is_active: true
        }
      }
      
      this.$nextTick(() => {
        this.$refs.formRef?.clearValidate()
      })
    },

    async handleSubmit() {
      try {
        await this.$refs.formRef.validate()
        this.loading = true

        const formData = { ...this.formState }
        
        if (this.isEdit) {
          await api.updateApiKey(this.editId, formData)
          message.success('API key updated successfully')
        } else {
          const result = await api.createApiKey(formData)
          message.success('API key generated successfully')
          
          // Show the generated key
          this.$emit('created', result)
        }

        this.visible = false
        this.$emit('success')
      } catch (error) {
        console.error('Error saving API key:', error)
        message.error(error.response?.data?.detail || 'Failed to save API key')
      } finally {
        this.loading = false
      }
    },

    handleCancel() {
      this.visible = false
    }
  }
}
</script>

<style scoped>
.ant-form-item {
  margin-bottom: 16px;
}
</style>