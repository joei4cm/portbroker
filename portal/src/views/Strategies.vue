<template>
  <div>
    <div class="page-header">
      <h1>Strategies</h1>
      <a-button type="primary" @click="showAddModal">
        <plus-outlined />
        Add Strategy
      </a-button>
    </div>
    
    <a-table
      :columns="columns"
      :data-source="strategies"
      :loading="loading"
      row-key="id"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'type'">
          <a-tag :color="record.strategy_type === 'openai' ? 'blue' : 'green'">
            {{ record.strategy_type.toUpperCase() }}
          </a-tag>
        </template>
        
        <template v-if="column.key === 'status'">
          <a-switch
            :checked="record.is_active"
            @change="(checked) => toggleStrategy(record, checked)"
            :disabled="isToggleDisabled(record)"
          />
        </template>
        
        <template v-if="column.key === 'models'">
          <div v-if="record.strategy_type === 'openai'">
            <a-tag v-for="mapping in record.provider_mappings" :key="mapping.id" style="margin: 2px;">
              <div style="font-weight: bold;">{{ mapping.provider?.name }}</div>
              <div v-for="model in mapping.selected_models" :key="model" style="margin: 1px;">
                {{ model }}
              </div>
            </a-tag>
          </div>
          <div v-else>
            <div v-for="mapping in record.provider_mappings" :key="mapping.id" style="margin-bottom: 8px;">
              <div style="font-weight: bold;">{{ mapping.provider?.name }}</div>
              <div v-if="mapping.large_models?.length">
                <small>Big:</small>
                <a-tag v-for="model in mapping.large_models" :key="model" color="red" style="margin: 2px;">
                  {{ model }}
                </a-tag>
              </div>
              <div v-if="mapping.medium_models?.length">
                <small>Medium:</small>
                <a-tag v-for="model in mapping.medium_models" :key="model" color="orange" style="margin: 2px;">
                  {{ model }}
                </a-tag>
              </div>
              <div v-if="mapping.small_models?.length">
                <small>Small:</small>
                <a-tag v-for="model in mapping.small_models" :key="model" color="blue" style="margin: 2px;">
                  {{ model }}
                </a-tag>
              </div>
            </div>
          </div>
        </template>
        
        <template v-if="column.key === 'actions'">
          <a-space>
            <a-button type="link" size="small" @click="editStrategy(record)">
              <edit-outlined />
            </a-button>
            <a-button type="link" size="small" danger @click="deleteStrategy(record)">
              <delete-outlined />
            </a-button>
          </a-space>
        </template>
      </template>
    </a-table>
    
    <!-- Strategy Modal -->
    <a-modal
      v-model:open="modalVisible"
      :title="editingStrategy ? 'Edit Strategy' : 'Add Strategy'"
      @ok="handleModalStep"
      @cancel="handleModalCancel"
      width="1200px"
      :ok-button-props="{ disabled: !isStepValid }"
      :ok-text="currentStep === 2 ? 'Create Strategy' : 'Next'"
    >
      <a-steps :current="currentStep" style="margin-bottom: 24px;">
        <a-step title="Strategy Type" description="Choose OpenAI or Anthropic" />
        <a-step title="Strategy Details" description="Name and configuration" />
        <a-step title="Model Selection" description="Configure model ordering" />
      </a-steps>

      <!-- Step 1: Strategy Type Selection -->
      <div v-if="currentStep === 0">
        <a-form
          :model="form"
          :rules="rules"
          ref="formRefStep1"
          layout="vertical"
          @finish="handleFormFinish"
        >
          <a-form-item label="Strategy Type" name="type">
            <a-radio-group v-model:value="form.type" @change="handleTypeChange">
              <a-radio value="openai">
                <a-card hoverable style="width: 300px; margin-right: 16px;">
                  <template #title>
                    <span style="color: #1890ff;">OpenAI</span>
                  </template>
                  <p>For OpenAI-compatible models with single model list ordering</p>
                  <ul>
                    <li>GPT-3.5, GPT-4, and compatible models</li>
                    <li>Simple model priority ordering</li>
                    <li>Easy configuration</li>
                  </ul>
                </a-card>
              </a-radio>
              <a-radio value="anthropic">
                <a-card hoverable style="width: 300px;">
                  <template #title>
                    <span style="color: #52c41a;">Anthropic</span>
                  </template>
                  <p>For Anthropic models with tiered model selection</p>
                  <ul>
                    <li>Claude 3 Haiku, Sonnet, Opus</li>
                    <li>High/Middle/Low tier organization</li>
                    <li>Advanced fallback strategy</li>
                  </ul>
                </a-card>
              </a-radio>
            </a-radio-group>
          </a-form-item>
        </a-form>
      </div>

      <!-- Step 2: Strategy Details -->
      <div v-if="currentStep === 1">
        <a-form
          :model="form"
          :rules="rules"
          ref="formRefStep2"
          layout="vertical"
          @finish="handleFormFinish"
        >
          <a-form-item label="Strategy Name" name="name">
            <a-input v-model:value="form.name" placeholder="Enter strategy name" />
          </a-form-item>
          
          <a-form-item label="Description">
            <a-textarea v-model:value="form.description" placeholder="Enter strategy description (optional)" :rows="3" />
          </a-form-item>
          
          <a-form-item label="Fallback Configuration">
            <a-checkbox v-model:checked="form.fallback_enabled">
              Enable fallback to smaller models if larger models fail
            </a-checkbox>
            <div v-if="form.fallback_enabled" style="margin-top: 8px;">
              <span style="margin-right: 8px;">Fallback order:</span>
              <a-select v-model:value="form.fallback_order" mode="multiple" style="width: 300px;">
                <a-select-option value="large">Large Models</a-select-option>
                <a-select-option value="medium">Medium Models</a-select-option>
                <a-select-option value="small">Small Models</a-select-option>
              </a-select>
            </div>
          </a-form-item>
        </a-form>
      </div>

      <!-- Step 3: Model Selection -->
      <div v-if="currentStep === 2">
        <a-form
          :model="form"
          :rules="rules"
          ref="formRefStep3"
          layout="vertical"
          @finish="handleFormFinish"
        >
          <!-- OpenAI Strategy Form -->
          <div v-if="form.type === 'openai'">
            <a-form-item label="Available Models">
              <a-row :gutter="16">
                <a-col :span="12">
                  <a-select
                    v-model:value="selectedOpenAIModel"
                    placeholder="Search and select models"
                    show-search
                    :filter-option="filterOption"
                    :options="availableOpenAIModels"
                  />
                </a-col>
                <a-col :span="12">
                  <a-button @click="addOpenAIModel" :disabled="!selectedOpenAIModel">
                    Add Model
                  </a-button>
                </a-col>
              </a-row>
            </a-form-item>
            
            <a-form-item label="Model Priority Order">
              <div class="model-list">
                <div
                  v-for="(model, index) in form.models"
                  :key="model"
                  class="model-item"
                >
                  <span>{{ model }}</span>
                  <div class="model-controls">
                    <a-button 
                      type="link" 
                      size="small" 
                      @click="moveOpenAIModel(index, -1)"
                      :disabled="index === 0"
                    >
                      <up-outlined />
                    </a-button>
                    <a-button 
                      type="link" 
                      size="small" 
                      @click="moveOpenAIModel(index, 1)"
                      :disabled="index === form.models.length - 1"
                    >
                      <down-outlined />
                    </a-button>
                    <a-button type="link" size="small" @click="removeOpenAIModel(index)">
                      <close-outlined />
                    </a-button>
                  </div>
                </div>
              </div>
            </a-form-item>
          </div>
          
          <!-- Anthropic Strategy Form -->
          <div v-else-if="form.type === 'anthropic'">
            <a-row :gutter="16">
              <a-col :span="8">
                <a-form-item label="High Priority Models">
                  <a-select
                    v-model:value="selectedAnthropicBigModel"
                    placeholder="Search high priority models"
                    show-search
                    :filter-option="filterOption"
                    :options="availableAnthropicBigModels"
                  />
                  <a-button
                    @click="addAnthropicModel('big')"
                    :disabled="!selectedAnthropicBigModel"
                    style="margin-top: 8px; width: 100%"
                  >
                    Add High Priority Model
                  </a-button>
                  
                  <div class="model-list" style="margin-top: 8px;">
                    <div
                      v-for="(model, index) in form.big_models"
                      :key="model"
                      class="model-item"
                    >
                      <span>{{ model }}</span>
                      <div class="model-controls">
                        <a-button 
                          type="link" 
                          size="small" 
                          @click="moveAnthropicModel('big', index, -1)"
                          :disabled="index === 0"
                        >
                          <up-outlined />
                        </a-button>
                        <a-button 
                          type="link" 
                          size="small" 
                          @click="moveAnthropicModel('big', index, 1)"
                          :disabled="index === form.big_models.length - 1"
                        >
                          <down-outlined />
                        </a-button>
                        <a-button type="link" size="small" @click="removeAnthropicModel('big', index)">
                          <close-outlined />
                        </a-button>
                      </div>
                    </div>
                  </div>
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="Medium Priority Models">
                  <a-select
                    v-model:value="selectedAnthropicMediumModel"
                    placeholder="Search medium priority models"
                    show-search
                    :filter-option="filterOption"
                    :options="availableAnthropicMediumModels"
                  />
                  <a-button
                    @click="addAnthropicModel('medium')"
                    :disabled="!selectedAnthropicMediumModel"
                    style="margin-top: 8px; width: 100%"
                  >
                    Add Medium Priority Model
                  </a-button>
                  
                  <div class="model-list" style="margin-top: 8px;">
                    <div
                      v-for="(model, index) in form.medium_models"
                      :key="model"
                      class="model-item"
                    >
                      <span>{{ model }}</span>
                      <div class="model-controls">
                        <a-button 
                          type="link" 
                          size="small" 
                          @click="moveAnthropicModel('medium', index, -1)"
                          :disabled="index === 0"
                        >
                          <up-outlined />
                        </a-button>
                        <a-button 
                          type="link" 
                          size="small" 
                          @click="moveAnthropicModel('medium', index, 1)"
                          :disabled="index === form.medium_models.length - 1"
                        >
                          <down-outlined />
                        </a-button>
                        <a-button type="link" size="small" @click="removeAnthropicModel('medium', index)">
                          <close-outlined />
                        </a-button>
                      </div>
                    </div>
                  </div>
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="Low Priority Models">
                  <a-select
                    v-model:value="selectedAnthropicSmallModel"
                    placeholder="Search low priority models"
                    show-search
                    :filter-option="filterOption"
                    :options="availableAnthropicSmallModels"
                  />
                  <a-button
                    @click="addAnthropicModel('small')"
                    :disabled="!selectedAnthropicSmallModel"
                    style="margin-top: 8px; width: 100%"
                  >
                    Add Low Priority Model
                  </a-button>
                  
                  <div class="model-list" style="margin-top: 8px;">
                    <div
                      v-for="(model, index) in form.small_models"
                      :key="model"
                      class="model-item"
                    >
                      <span>{{ model }}</span>
                      <div class="model-controls">
                        <a-button 
                          type="link" 
                          size="small" 
                          @click="moveAnthropicModel('small', index, -1)"
                          :disabled="index === 0"
                        >
                          <up-outlined />
                        </a-button>
                        <a-button 
                          type="link" 
                          size="small" 
                          @click="moveAnthropicModel('small', index, 1)"
                          :disabled="index === form.small_models.length - 1"
                        >
                          <down-outlined />
                        </a-button>
                        <a-button type="link" size="small" @click="removeAnthropicModel('small', index)">
                          <close-outlined />
                        </a-button>
                      </div>
                    </div>
                  </div>
                </a-form-item>
              </a-col>
            </a-row>
          </div>
          
          <a-form-item label="Enabled">
            <a-switch v-model:checked="form.is_enabled" />
          </a-form-item>
        </a-form>
      </div>
    </a-modal>
  </div>
</template>

<script>
import { message } from 'ant-design-vue'
import { ref } from 'vue'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CloseOutlined,
  UpOutlined,
  DownOutlined
} from '@ant-design/icons-vue'
import api from '@/api'

export default {
  name: 'Strategies',
  components: {
    PlusOutlined,
    EditOutlined,
    DeleteOutlined,
    CloseOutlined,
    UpOutlined,
    DownOutlined
  },
  data() {
    return {
      loading: false,
      strategies: [],
      modalVisible: false,
      editingStrategy: null,
      currentStep: 0,
      form: {
        type: 'openai',
        name: '',
        description: '',
        fallback_enabled: true,
        fallback_order: ['large', 'medium', 'small'],
        models: [],
        big_models: [],
        medium_models: [],
        small_models: [],
        is_enabled: true
      },
      selectedOpenAIModel: null,
      selectedAnthropicBigModel: null,
      selectedAnthropicMediumModel: null,
      selectedAnthropicSmallModel: null,
      allModels: [
        { label: 'OpenAI - gpt-3.5-turbo', value: 'gpt-3.5-turbo', type: 'openai', size: 'medium' },
        { label: 'OpenAI - gpt-4', value: 'gpt-4', type: 'openai', size: 'big' },
        { label: 'Anthropic - claude-3-haiku', value: 'claude-3-haiku', type: 'anthropic', size: 'small' },
        { label: 'Anthropic - claude-3-sonnet', value: 'claude-3-sonnet', type: 'anthropic', size: 'medium' },
        { label: 'Anthropic - claude-3-opus', value: 'claude-3-opus', type: 'anthropic', size: 'big' }
      ],
      rules: {
        type: [{ required: true, message: 'Please select strategy type' }],
        name: [{ required: true, message: 'Please enter strategy name' }]
      },
      columns: [
        {
          title: 'Name',
          dataIndex: 'name',
          key: 'name'
        },
        {
          title: 'Type',
          key: 'type'
        },
        {
          title: 'Status',
          key: 'status'
        },
        {
          title: 'Models',
          key: 'models',
          width: 400
        },
        {
          title: 'Actions',
          key: 'actions',
          width: 120
        }
      ]
    }
  },
  computed: {
    availableOpenAIModels() {
      const usedModels = this.form.models || []
      return this.allModels
        .filter(model => model.type === 'openai' && !usedModels.includes(model.value))
        .map(model => ({ label: model.label, value: model.value }))
    },
    
    availableAnthropicBigModels() {
      const usedModels = this.form.big_models || []
      return this.allModels
        .filter(model => model.type === 'anthropic' && model.size === 'big' && !usedModels.includes(model.value))
        .map(model => ({ label: model.label, value: model.value }))
    },
    
    availableAnthropicMediumModels() {
      const usedModels = this.form.medium_models || []
      return this.allModels
        .filter(model => model.type === 'anthropic' && model.size === 'medium' && !usedModels.includes(model.value))
        .map(model => ({ label: model.label, value: model.value }))
    },
    
    availableAnthropicSmallModels() {
      const usedModels = this.form.small_models || []
      return this.allModels
        .filter(model => model.type === 'anthropic' && model.size === 'small' && !usedModels.includes(model.value))
        .map(model => ({ label: model.label, value: model.value }))
    },
    
    isStepValid() {
      switch (this.currentStep) {
        case 0:
          return !!this.form.type
        case 1:
          return !!this.form.name
        case 2:
          if (this.form.type === 'openai') {
            return this.form.models && this.form.models.length > 0
          } else if (this.form.type === 'anthropic') {
            return (this.form.big_models && this.form.big_models.length > 0) ||
                   (this.form.medium_models && this.form.medium_models.length > 0) ||
                   (this.form.small_models && this.form.small_models.length > 0)
          }
          return false
        default:
          return false
      }
    },
    
    isFormValid() {
      return this.isStepValid
    }
  },
  watch: {
    modalVisible(newVal) {
      if (newVal) {
        // When modal becomes visible, wait for DOM to update
        this.$nextTick(() => {
          // Form references should be available now
          console.log('Modal opened, form refs:', {
            formRefStep1: this.$refs.formRefStep1,
            formRefStep2: this.$refs.formRefStep2,
            formRefStep3: this.$refs.formRefStep3
          })
        })
      }
    },
    currentStep(newStep, oldStep) {
      // Use nextTick to wait for DOM to update after step change
      this.$nextTick(() => {
        // Clear form validation errors when switching steps
        if (this.$refs.formRefStep1) this.$refs.formRefStep1.clearValidate()
        if (this.$refs.formRefStep2) this.$refs.formRefStep2.clearValidate()
        if (this.$refs.formRefStep3) this.$refs.formRefStep3.clearValidate()
      })
    }
  },
  async mounted() {
    await this.loadStrategies()
  },
  methods: {
    async loadStrategies() {
      this.loading = true
      try {
        const response = await api.getStrategies()
        this.strategies = response || []
      } catch (error) {
        message.error('Failed to load strategies')
      } finally {
        this.loading = false
      }
    },
    
    showAddModal() {
      this.editingStrategy = null
      this.currentStep = 0
      this.form = {
        type: 'openai',
        name: '',
        description: '',
        fallback_enabled: true,
        fallback_order: ['large', 'medium', 'small'],
        models: [],
        big_models: [],
        medium_models: [],
        small_models: [],
        is_enabled: true
      }
      this.selectedOpenAIModel = null
      this.selectedAnthropicBigModel = null
      this.selectedAnthropicMediumModel = null
      this.selectedAnthropicSmallModel = null
      
      // Use nextTick to ensure modal is visible before resetting form refs
      this.$nextTick(() => {
        this.modalVisible = true
      })
    },
    
    editStrategy(strategy) {
      this.editingStrategy = strategy
      this.currentStep = 0
      
      // Map the strategy data to form format
      this.form = {
        type: strategy.strategy_type,
        name: strategy.name,
        description: strategy.description || '',
        fallback_enabled: strategy.fallback_enabled,
        fallback_order: strategy.fallback_order || ['large', 'medium', 'small'],
        models: [],
        big_models: [],
        medium_models: [],
        small_models: [],
        is_enabled: strategy.is_active
      }
      
      // Extract models from provider mappings
      if (strategy.provider_mappings && strategy.provider_mappings.length > 0) {
        const mapping = strategy.provider_mappings[0] // Use first mapping for now
        if (strategy.strategy_type === 'openai') {
          this.form.models = mapping.selected_models || []
        } else {
          this.form.big_models = mapping.large_models || []
          this.form.medium_models = mapping.medium_models || []
          this.form.small_models = mapping.small_models || []
        }
      }
      
      this.selectedOpenAIModel = null
      this.selectedAnthropicBigModel = null
      this.selectedAnthropicMediumModel = null
      this.selectedAnthropicSmallModel = null
      
      // Use nextTick to ensure modal is visible before resetting form refs
      this.$nextTick(() => {
        this.modalVisible = true
      })
    },
    
    handleTypeChange() {
      this.form.models = []
      this.form.big_models = []
      this.form.medium_models = []
      this.form.small_models = []
      this.selectedOpenAIModel = null
      this.selectedAnthropicBigModel = null
      this.selectedAnthropicMediumModel = null
      this.selectedAnthropicSmallModel = null
      
      // Use nextTick to wait for DOM to update after type change
      this.$nextTick(() => {
        // Clear form validation errors for all forms
        if (this.$refs.formRefStep1) this.$refs.formRefStep1.clearValidate()
        if (this.$refs.formRefStep2) this.$refs.formRefStep2.clearValidate()
        if (this.$refs.formRefStep3) this.$refs.formRefStep3.clearValidate()
      })
    },
    
    filterOption(input, option) {
      return option.label.toLowerCase().indexOf(input.toLowerCase()) >= 0
    },
    
    handleModalStep() {
      // Use nextTick to ensure DOM is updated before validation
      this.$nextTick(() => {
        let currentFormRef
        switch (this.currentStep) {
          case 0:
            currentFormRef = this.$refs.formRefStep1
            break
          case 1:
            currentFormRef = this.$refs.formRefStep2
            break
          case 2:
            currentFormRef = this.$refs.formRefStep3
            break
          default:
            console.error('Invalid step:', this.currentStep)
            return
        }
        
        console.log('Attempting validation for step:', this.currentStep, 'Form ref:', currentFormRef)
        
        if (currentFormRef) {
          currentFormRef.validate().then(() => {
            console.log('Validation successful for step:', this.currentStep)
            if (this.currentStep < 2) {
              this.currentStep++
            } else {
              this.handleModalOk()
            }
          }).catch(error => {
            console.error('Form validation failed:', error)
          })
        } else {
          console.error('Form reference is null for step:', this.currentStep)
          // Try one more time with a longer delay
          setTimeout(() => {
            let retryFormRef
            switch (this.currentStep) {
              case 0:
                retryFormRef = this.$refs.formRefStep1
                break
              case 1:
                retryFormRef = this.$refs.formRefStep2
                break
              case 2:
                retryFormRef = this.$refs.formRefStep3
                break
            }
            
            if (retryFormRef) {
              retryFormRef.validate().then(() => {
                if (this.currentStep < 2) {
                  this.currentStep++
                } else {
                  this.handleModalOk()
                }
              }).catch(error => {
                console.error('Form validation failed on retry:', error)
              })
            } else {
              console.error('Form reference still null after retry for step:', this.currentStep)
            }
          }, 200) // Increased delay
        }
      })
    },
    
    addOpenAIModel() {
      if (this.selectedOpenAIModel && !this.form.models.includes(this.selectedOpenAIModel)) {
        this.form.models.push(this.selectedOpenAIModel)
        this.selectedOpenAIModel = null
      }
    },
    
    removeOpenAIModel(index) {
      this.form.models.splice(index, 1)
    },
    
    addAnthropicModel(size) {
      let selectedModel, targetArray
      
      switch (size) {
        case 'big':
          selectedModel = this.selectedAnthropicBigModel
          targetArray = this.form.big_models
          this.selectedAnthropicBigModel = null
          break
        case 'medium':
          selectedModel = this.selectedAnthropicMediumModel
          targetArray = this.form.medium_models
          this.selectedAnthropicMediumModel = null
          break
        case 'small':
          selectedModel = this.selectedAnthropicSmallModel
          targetArray = this.form.small_models
          this.selectedAnthropicSmallModel = null
          break
      }
      
      if (selectedModel && !targetArray.includes(selectedModel)) {
        targetArray.push(selectedModel)
      }
    },
    
    removeAnthropicModel(size, index) {
      switch (size) {
        case 'big':
          this.form.big_models.splice(index, 1)
          break
        case 'medium':
          this.form.medium_models.splice(index, 1)
          break
        case 'small':
          this.form.small_models.splice(index, 1)
          break
      }
    },
    
    handleFormFinish() {
      // Form validation successful
      if (this.currentStep < 2) {
        this.currentStep++
      } else {
        this.handleModalOk()
      }
    },

    async handleModalOk() {
      // Validate all forms based on the strategy type
      const validationPromises = []
      
      // Always validate step 1 and 2
      if (this.$refs.formRefStep1) validationPromises.push(this.$refs.formRefStep1.validate())
      if (this.$refs.formRefStep2) validationPromises.push(this.$refs.formRefStep2.validate())
      
      // Validate step 3 if needed
      if (this.$refs.formRefStep3) validationPromises.push(this.$refs.formRefStep3.validate())
      
      try {
        await Promise.all(validationPromises)
        
        const strategyData = {
          name: this.form.name,
          strategy_type: this.form.type,
          description: this.form.description || '',
          fallback_enabled: this.form.fallback_enabled,
          fallback_order: this.form.fallback_order || ['large', 'medium', 'small'],
          is_active: this.form.is_enabled,
          provider_mappings: []
        }
        
        // Add provider mapping based on strategy type
        if (this.form.type === 'openai') {
          strategyData.provider_mappings.push({
            provider_id: 1, // Default to first provider for now
            selected_models: this.form.models || [],
            large_models: [],
            medium_models: [],
            small_models: [],
            priority: 1,
            is_active: true
          })
        } else if (this.form.type === 'anthropic') {
          strategyData.provider_mappings.push({
            provider_id: 1, // Default to first provider for now
            selected_models: [],
            large_models: this.form.big_models || [],
            medium_models: this.form.medium_models || [],
            small_models: this.form.small_models || [],
            priority: 1,
            is_active: true
          })
        }
        
        if (this.editingStrategy) {
          await api.updateStrategy(this.editingStrategy.id, strategyData)
          message.success('Strategy updated successfully')
        } else {
          await api.createStrategy(strategyData)
          message.success('Strategy created successfully')
        }
        
        this.modalVisible = false
        await this.loadStrategies()
      } catch (error) {
        console.error('Strategy creation error:', error)
        if (error.response?.data) {
          message.error('Validation failed: ' + JSON.stringify(error.response.data))
        } else if (error.message) {
          message.error('Validation failed: ' + error.message)
        } else {
          message.error('Operation failed')
        }
      }
    },
    
    handleModalCancel() {
      this.modalVisible = false
    },
    
    async deleteStrategy(strategy) {
      try {
        await api.deleteStrategy(strategy.id)
        message.success('Strategy deleted successfully')
        await this.loadStrategies()
      } catch (error) {
        message.error('Failed to delete strategy')
      }
    },
    
    async toggleStrategy(strategy, enabled) {
      try {
        await api.updateStrategy(strategy.id, { ...strategy, is_active: enabled })
        message.success(`Strategy ${enabled ? 'enabled' : 'disabled'} successfully`)
        await this.loadStrategies()
      } catch (error) {
        message.error('Failed to toggle strategy')
      }
    },
    
    isToggleDisabled(strategy) {
      if (!strategy.is_active) return false
      
      // Check if there's already an enabled strategy of the same type
      const existingEnabled = this.strategies.find(s => 
        s.strategy_type === strategy.strategy_type && 
        s.is_active && 
        s.id !== strategy.id
      )
      
      return !!existingEnabled
    },
    
    moveOpenAIModel(index, direction) {
      const newIndex = index + direction
      if (newIndex >= 0 && newIndex < this.form.models.length) {
        const models = [...this.form.models]
        const temp = models[index]
        models[index] = models[newIndex]
        models[newIndex] = temp
        this.form.models = models
      }
    },
    
    moveAnthropicModel(size, index, direction) {
      let targetArray
      switch (size) {
        case 'big':
          targetArray = this.form.big_models
          break
        case 'medium':
          targetArray = this.form.medium_models
          break
        case 'small':
          targetArray = this.form.small_models
          break
      }
      
      const newIndex = index + direction
      if (newIndex >= 0 && newIndex < targetArray.length) {
        const models = [...targetArray]
        const temp = models[index]
        models[index] = models[newIndex]
        models[newIndex] = temp
        this.form[size + '_models'] = models
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

.model-list {
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 8px;
  min-height: 60px;
  max-height: 200px;
  overflow-y: auto;
}

.model-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 8px;
  margin: 2px 0;
  background: #f5f5f5;
  border-radius: 4px;
}

.model-item:hover {
  background: #e6f7ff;
}
</style>