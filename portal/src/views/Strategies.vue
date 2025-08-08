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
          <div class="models-container">
            <div v-if="record.strategy_type === 'openai'">
              <div v-for="mapping in record.provider_mappings" :key="mapping.id" class="provider-models">
                <div class="provider-name">{{ mapping.provider?.name }}</div>
                <div class="model-list">
                  <a-tag v-for="model in mapping.selected_models" :key="model" class="model-tag">
                    {{ model }}
                  </a-tag>
                </div>
              </div>
            </div>
            <div v-else>
              <div v-for="mapping in record.provider_mappings" :key="mapping.id" class="provider-models">
                <div class="provider-name">{{ mapping.provider?.name }}</div>
                <div class="anthropic-models">
                  <div v-if="mapping.large_models?.length" class="model-tier">
                    <span class="tier-label">Big:</span>
                    <a-tag v-for="model in mapping.large_models" :key="model" color="red" class="model-tag">
                      {{ model }}
                    </a-tag>
                  </div>
                  <div v-if="mapping.medium_models?.length" class="model-tier">
                    <span class="tier-label">Medium:</span>
                    <a-tag v-for="model in mapping.medium_models" :key="model" color="orange" class="model-tag">
                      {{ model }}
                    </a-tag>
                  </div>
                  <div v-if="mapping.small_models?.length" class="model-tier">
                    <span class="tier-label">Small:</span>
                    <a-tag v-for="model in mapping.small_models" :key="model" color="blue" class="model-tag">
                      {{ model }}
                    </a-tag>
                  </div>
                </div>
              </div>
            </div>
            <a-tooltip v-if="getModelOrderInfo(record)" :title="getModelOrderInfo(record)">
              <info-circle-outlined class="info-icon" />
            </a-tooltip>
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
      @ok="handleModalOk"
      @cancel="handleModalCancel"
      width="1000px"
      :ok-button-props="{ disabled: !isFormValid }"
    >
      <a-form
        :model="form"
        :rules="rules"
        ref="formRef"
        layout="vertical"
      >
        <!-- Strategy Type Selection -->
        <a-form-item label="Strategy Type" name="strategy_type">
          <a-radio-group v-model:value="form.strategy_type" @change="handleTypeChange">
            <a-radio value="openai">
              <a-card hoverable style="width: 300px; margin-right: 16px;">
                <template #title>
                  <span style="color: #1890ff;">OpenAI</span>
                </template>
                <p>For OpenAI-compatible models with single model list</p>
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
                  <li>Big/Medium/Small tier organization</li>
                  <li>Advanced model routing</li>
                </ul>
              </a-card>
            </a-radio>
          </a-radio-group>
        </a-form-item>
        
        <!-- Strategy Name -->
        <a-form-item label="Strategy Name" name="name">
          <a-input v-model:value="form.name" placeholder="Enter strategy name" />
        </a-form-item>
        
        <!-- Description -->
        <a-form-item label="Description">
          <a-textarea v-model:value="form.description" placeholder="Enter strategy description (optional)" :rows="3" />
        </a-form-item>
        
        <!-- Model Selection -->
        <a-form-item :label="form.strategy_type === 'openai' ? 'Models' : 'Model Configuration'">
          <!-- OpenAI Strategy Model Selection -->
          <div v-if="form.strategy_type === 'openai'">
            <a-row :gutter="16">
              <a-col :span="12">
                <a-select
                  v-model:value="selectedModel"
                  placeholder="Search and select models"
                  show-search
                  :filter-option="filterOption"
                  :options="availableModels"
                  style="width: 100%"
                />
              </a-col>
              <a-col :span="12">
                <a-button @click="addModel" :disabled="!selectedModel" type="primary">
                  Add Model
                </a-button>
              </a-col>
            </a-row>
            
            <div class="selected-models">
              <div class="model-list-header">
                <span>Selected Models (in order of priority):</span>
                <span class="model-count">{{ form.models.length }} selected</span>
              </div>
              <div class="model-list">
                <div
                  v-for="(model, index) in form.models"
                  :key="model.id"
                  class="model-item"
                >
                  <div class="model-info">
                    <span class="model-name">{{ model.label }}</span>
                    <span class="model-provider">{{ model.providerName }}</span>
                  </div>
                  <div class="model-controls">
                    <a-button 
                      type="link" 
                      size="small" 
                      @click="moveModel(index, -1)"
                      :disabled="index === 0"
                      title="Move up"
                    >
                      <up-outlined />
                    </a-button>
                    <a-button 
                      type="link" 
                      size="small" 
                      @click="moveModel(index, 1)"
                      :disabled="index === form.models.length - 1"
                      title="Move down"
                    >
                      <down-outlined />
                    </a-button>
                    <a-button type="link" size="small" @click="removeModel(index)" title="Remove">
                      <close-outlined />
                    </a-button>
                  </div>
                </div>
                <div v-if="form.models.length === 0" class="empty-models">
                  No models selected. Add models from the dropdown above.
                </div>
              </div>
            </div>
          </div>
          
          <!-- Anthropic Strategy Model Selection -->
          <div v-else-if="form.strategy_type === 'anthropic'">
            <a-row :gutter="16">
              <a-col :span="8">
                <div class="anthropic-tier">
                  <h4>Big Models</h4>
                  <a-select
                    v-model:value="selectedBigModel"
                    placeholder="Search big models"
                    show-search
                    :filter-option="filterOption"
                    :options="availableBigModels"
                    style="width: 100%; margin-bottom: 8px;"
                  />
                  <a-button 
                    @click="addAnthropicModel('big')" 
                    :disabled="!selectedBigModel"
                    type="primary"
                    size="small"
                    style="width: 100%"
                  >
                    Add Big Model
                  </a-button>
                  
                  <div class="model-list" style="margin-top: 8px;">
                    <div
                      v-for="(model, index) in form.big_models"
                      :key="model.id"
                      class="model-item"
                    >
                      <div class="model-info">
                        <span class="model-name">{{ model.label }}</span>
                        <span class="model-provider">{{ model.providerName }}</span>
                      </div>
                      <div class="model-controls">
                        <a-button 
                          type="link" 
                          size="small" 
                          @click="moveAnthropicModel('big', index, -1)"
                          :disabled="index === 0"
                          title="Move up"
                        >
                          <up-outlined />
                        </a-button>
                        <a-button 
                          type="link" 
                          size="small" 
                          @click="moveAnthropicModel('big', index, 1)"
                          :disabled="index === form.big_models.length - 1"
                          title="Move down"
                        >
                          <down-outlined />
                        </a-button>
                        <a-button type="link" size="small" @click="removeAnthropicModel('big', index)" title="Remove">
                          <close-outlined />
                        </a-button>
                      </div>
                    </div>
                    <div v-if="form.big_models.length === 0" class="empty-models">
                      No big models selected
                    </div>
                  </div>
                </div>
              </a-col>
              <a-col :span="8">
                <div class="anthropic-tier">
                  <h4>Medium Models</h4>
                  <a-select
                    v-model:value="selectedMediumModel"
                    placeholder="Search medium models"
                    show-search
                    :filter-option="filterOption"
                    :options="availableMediumModels"
                    style="width: 100%; margin-bottom: 8px;"
                  />
                  <a-button 
                    @click="addAnthropicModel('medium')" 
                    :disabled="!selectedMediumModel"
                    type="primary"
                    size="small"
                    style="width: 100%"
                  >
                    Add Medium Model
                  </a-button>
                  
                  <div class="model-list" style="margin-top: 8px;">
                    <div
                      v-for="(model, index) in form.medium_models"
                      :key="model.id"
                      class="model-item"
                    >
                      <div class="model-info">
                        <span class="model-name">{{ model.label }}</span>
                        <span class="model-provider">{{ model.providerName }}</span>
                      </div>
                      <div class="model-controls">
                        <a-button 
                          type="link" 
                          size="small" 
                          @click="moveAnthropicModel('medium', index, -1)"
                          :disabled="index === 0"
                          title="Move up"
                        >
                          <up-outlined />
                        </a-button>
                        <a-button 
                          type="link" 
                          size="small" 
                          @click="moveAnthropicModel('medium', index, 1)"
                          :disabled="index === form.medium_models.length - 1"
                          title="Move down"
                        >
                          <down-outlined />
                        </a-button>
                        <a-button type="link" size="small" @click="removeAnthropicModel('medium', index)" title="Remove">
                          <close-outlined />
                        </a-button>
                      </div>
                    </div>
                    <div v-if="form.medium_models.length === 0" class="empty-models">
                      No medium models selected
                    </div>
                  </div>
                </div>
              </a-col>
              <a-col :span="8">
                <div class="anthropic-tier">
                  <h4>Small Models</h4>
                  <a-select
                    v-model:value="selectedSmallModel"
                    placeholder="Search small models"
                    show-search
                    :filter-option="filterOption"
                    :options="availableSmallModels"
                    style="width: 100%; margin-bottom: 8px;"
                  />
                  <a-button 
                    @click="addAnthropicModel('small')" 
                    :disabled="!selectedSmallModel"
                    type="primary"
                    size="small"
                    style="width: 100%"
                  >
                    Add Small Model
                  </a-button>
                  
                  <div class="model-list" style="margin-top: 8px;">
                    <div
                      v-for="(model, index) in form.small_models"
                      :key="model.id"
                      class="model-item"
                    >
                      <div class="model-info">
                        <span class="model-name">{{ model.label }}</span>
                        <span class="model-provider">{{ model.providerName }}</span>
                      </div>
                      <div class="model-controls">
                        <a-button 
                          type="link" 
                          size="small" 
                          @click="moveAnthropicModel('small', index, -1)"
                          :disabled="index === 0"
                          title="Move up"
                        >
                          <up-outlined />
                        </a-button>
                        <a-button 
                          type="link" 
                          size="small" 
                          @click="moveAnthropicModel('small', index, 1)"
                          :disabled="index === form.small_models.length - 1"
                          title="Move down"
                        >
                          <down-outlined />
                        </a-button>
                        <a-button type="link" size="small" @click="removeAnthropicModel('small', index)" title="Remove">
                          <close-outlined />
                        </a-button>
                      </div>
                    </div>
                    <div v-if="form.small_models.length === 0" class="empty-models">
                      No small models selected
                    </div>
                  </div>
                </div>
              </a-col>
            </a-row>
          </div>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script>
import { message } from 'ant-design-vue'
import { ref, computed, watch } from 'vue'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CloseOutlined,
  UpOutlined,
  DownOutlined,
  InfoCircleOutlined
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
    DownOutlined,
    InfoCircleOutlined
  },
  data() {
    return {
      loading: false,
      strategies: [],
      modalVisible: false,
      editingStrategy: null,
      form: {
        strategy_type: 'openai',
        name: '',
        description: '',
        models: [],
        big_models: [],
        medium_models: [],
        small_models: []
      },
      selectedModel: null,
      selectedBigModel: null,
      selectedMediumModel: null,
      selectedSmallModel: null,
      availableModelsData: [],
      rules: {
        strategy_type: [{ required: true, message: 'Please select strategy type' }],
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
    availableModels() {
      const usedModelIds = this.form.models.map(m => m.id)
      return this.availableModelsData
        .filter(model => !usedModelIds.includes(model.id))
        .map(model => ({ label: model.label, value: model.id }))
    },
    
    availableBigModels() {
      const usedModelIds = this.form.big_models.map(m => m.id)
      return this.availableModelsData
        .filter(model => !usedModelIds.includes(model.id))
        .map(model => ({ label: model.label, value: model.id }))
    },
    
    availableMediumModels() {
      const usedModelIds = this.form.medium_models.map(m => m.id)
      return this.availableModelsData
        .filter(model => !usedModelIds.includes(model.id))
        .map(model => ({ label: model.label, value: model.id }))
    },
    
    availableSmallModels() {
      const usedModelIds = this.form.small_models.map(m => m.id)
      return this.availableModelsData
        .filter(model => !usedModelIds.includes(model.id))
        .map(model => ({ label: model.label, value: model.id }))
    },
    
    isFormValid() {
      return this.form.strategy_type && 
             this.form.name && 
             this.hasSelectedModels
    },
    
    hasSelectedModels() {
      if (this.form.strategy_type === 'openai') {
        return this.form.models.length > 0
      } else {
        return this.form.big_models.length > 0 || 
               this.form.medium_models.length > 0 || 
               this.form.small_models.length > 0
      }
    }
  },
  watch: {
    'form.strategy_type'() {
      this.loadAvailableModels()
    },
    modalVisible(newVal) {
      if (newVal) {
        this.$nextTick(() => {
          if (this.$refs.formRef) {
            this.$refs.formRef.clearValidate()
          }
        })
      }
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
    
    async loadAvailableModels() {
      if (!this.form.strategy_type) return
      
      try {
        const response = await api.getStrategyModels(this.form.strategy_type)
        const models = response.models || []
        // Transform the models to include label field with proper format
        this.availableModelsData = models.map(model => ({
          id: model.id,
          name: model.name,
          provider_id: model.provider_id,
          provider_name: model.provider_name,
          label: `${model.provider_name} - ${model.name}`,
          modelName: model.name,
          providerName: model.provider_name
        }))
      } catch (error) {
        message.error('Failed to load available models')
        this.availableModelsData = []
      }
    },
    
    showAddModal() {
      this.editingStrategy = null
      this.form = {
        strategy_type: 'openai',
        name: '',
        description: '',
        models: [],
        big_models: [],
        medium_models: [],
        small_models: []
      }
      this.selectedModel = null
      this.selectedBigModel = null
      this.selectedMediumModel = null
      this.selectedSmallModel = null
      this.modalVisible = true
      this.loadAvailableModels()
    },
    
    editStrategy(strategy) {
      this.editingStrategy = strategy
      this.form = {
        strategy_type: strategy.strategy_type,
        name: strategy.name,
        description: strategy.description || '',
        models: [],
        big_models: [],
        medium_models: [],
        small_models: []
      }
      
      // Extract models from provider mappings
      if (strategy.provider_mappings && strategy.provider_mappings.length > 0) {
        const mapping = strategy.provider_mappings[0]
        if (strategy.strategy_type === 'openai') {
          this.form.models = (mapping.selected_models || []).map(modelName => ({
            id: `${mapping.provider.id}-${modelName}`,
            label: `${mapping.provider.name} - ${modelName}`,
            value: modelName,
            provider_id: mapping.provider.id,
            providerName: mapping.provider.name,
            modelName: modelName
          }))
        } else {
          this.form.big_models = (mapping.large_models || []).map(modelName => ({
            id: `${mapping.provider.id}-${modelName}`,
            label: `${mapping.provider.name} - ${modelName}`,
            value: modelName,
            provider_id: mapping.provider.id,
            providerName: mapping.provider.name,
            modelName: modelName
          }))
          this.form.medium_models = (mapping.medium_models || []).map(modelName => ({
            id: `${mapping.provider.id}-${modelName}`,
            label: `${mapping.provider.name} - ${modelName}`,
            value: modelName,
            provider_id: mapping.provider.id,
            providerName: mapping.provider.name,
            modelName: modelName
          }))
          this.form.small_models = (mapping.small_models || []).map(modelName => ({
            id: `${mapping.provider.id}-${modelName}`,
            label: `${mapping.provider.name} - ${modelName}`,
            value: modelName,
            provider_id: mapping.provider.id,
            providerName: mapping.provider.name,
            modelName: modelName
          }))
        }
      }
      
      this.selectedModel = null
      this.selectedBigModel = null
      this.selectedMediumModel = null
      this.selectedSmallModel = null
      this.modalVisible = true
      this.loadAvailableModels()
    },
    
    handleTypeChange() {
      // Clear all model selections when type changes
      this.form.models = []
      this.form.big_models = []
      this.form.medium_models = []
      this.form.small_models = []
      this.selectedModel = null
      this.selectedBigModel = null
      this.selectedMediumModel = null
      this.selectedSmallModel = null
    },
    
    filterOption(input, option) {
      return option.label.toLowerCase().indexOf(input.toLowerCase()) >= 0
    },
    
    addModel() {
      if (this.selectedModel) {
        const model = this.availableModelsData.find(m => m.id === this.selectedModel)
        if (model && !this.form.models.find(m => m.id === model.id)) {
          this.form.models.push(model)
          this.selectedModel = null
        }
      }
    },
    
    removeModel(index) {
      this.form.models.splice(index, 1)
    },
    
    moveModel(index, direction) {
      const newIndex = index + direction
      if (newIndex >= 0 && newIndex < this.form.models.length) {
        const models = [...this.form.models]
        const temp = models[index]
        models[index] = models[newIndex]
        models[newIndex] = temp
        this.form.models = models
      }
    },
    
    addAnthropicModel(size) {
      let selectedModel, targetArray
      
      switch (size) {
        case 'big':
          selectedModel = this.selectedBigModel
          targetArray = this.form.big_models
          this.selectedBigModel = null
          break
        case 'medium':
          selectedModel = this.selectedMediumModel
          targetArray = this.form.medium_models
          this.selectedMediumModel = null
          break
        case 'small':
          selectedModel = this.selectedSmallModel
          targetArray = this.form.small_models
          this.selectedSmallModel = null
          break
      }
      
      if (selectedModel) {
        const model = this.availableModelsData.find(m => m.id === selectedModel)
        if (model && !targetArray.find(m => m.id === model.id)) {
          targetArray.push(model)
        }
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
    },
    
    async handleModalOk() {
      try {
        await this.$refs.formRef.validate()
        
        const strategyData = {
          name: this.form.name,
          strategy_type: this.form.strategy_type,
          description: this.form.description || '',
          fallback_enabled: false, // Always false as per requirements
          fallback_order: ['large', 'medium', 'small'], // Default order
          is_active: false, // Always false initially
          provider_mappings: []
        }
        
        // Group models by provider
        const providerModels = {}
        
        if (this.form.strategy_type === 'openai') {
          this.form.models.forEach(model => {
            if (!providerModels[model.provider_id]) {
              providerModels[model.provider_id] = {
                provider_id: model.provider_id,
                selected_models: [],
                large_models: [],
                medium_models: [],
                small_models: []
              }
            }
            providerModels[model.provider_id].selected_models.push(model.modelName)
          })
        } else {
          this.form.big_models.forEach(model => {
            if (!providerModels[model.provider_id]) {
              providerModels[model.provider_id] = {
                provider_id: model.provider_id,
                selected_models: [],
                large_models: [],
                medium_models: [],
                small_models: []
              }
            }
            providerModels[model.provider_id].large_models.push(model.modelName)
          })
          
          this.form.medium_models.forEach(model => {
            if (!providerModels[model.provider_id]) {
              providerModels[model.provider_id] = {
                provider_id: model.provider_id,
                selected_models: [],
                large_models: [],
                medium_models: [],
                small_models: []
              }
            }
            providerModels[model.provider_id].medium_models.push(model.modelName)
          })
          
          this.form.small_models.forEach(model => {
            if (!providerModels[model.provider_id]) {
              providerModels[model.provider_id] = {
                provider_id: model.provider_id,
                selected_models: [],
                large_models: [],
                medium_models: [],
                small_models: []
              }
            }
            providerModels[model.provider_id].small_models.push(model.modelName)
          })
        }
        
        // Create provider mappings
        Object.values(providerModels).forEach((providerModel, index) => {
          strategyData.provider_mappings.push({
            provider_id: providerModel.provider_id,
            selected_models: providerModel.selected_models,
            large_models: providerModel.large_models,
            medium_models: providerModel.medium_models,
            small_models: providerModel.small_models,
            priority: index + 1,
            is_active: true
          })
        })
        
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
        console.error('Strategy operation error:', error)
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
        if (enabled) {
          await api.activateStrategy(strategy.id)
          message.success('Strategy activated successfully')
        } else {
          await api.deactivateStrategy(strategy.id)
          message.success('Strategy deactivated successfully')
        }
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
    
    getModelOrderInfo(strategy) {
      const models = []
      
      if (strategy.strategy_type === 'openai') {
        strategy.provider_mappings?.forEach(mapping => {
          mapping.selected_models?.forEach(model => {
            models.push(`${mapping.provider?.name} - ${model}`)
          })
        })
      } else {
        const tiers = [
          { name: 'Big', models: [] },
          { name: 'Medium', models: [] },
          { name: 'Small', models: [] }
        ]
        
        strategy.provider_mappings?.forEach(mapping => {
          mapping.large_models?.forEach(model => {
            tiers[0].models.push(`${mapping.provider?.name} - ${model}`)
          })
          mapping.medium_models?.forEach(model => {
            tiers[1].models.push(`${mapping.provider?.name} - ${model}`)
          })
          mapping.small_models?.forEach(model => {
            tiers[2].models.push(`${mapping.provider?.name} - ${model}`)
          })
        })
        
        tiers.forEach(tier => {
          if (tier.models.length > 0) {
            models.push(`${tier.name}: ${tier.models.join(', ')}`)
          }
        })
      }
      
      return models.length > 0 ? models.join('\n') : null
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

.models-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.provider-models {
  margin-bottom: 8px;
}

.provider-name {
  font-weight: bold;
  margin-bottom: 4px;
}

.model-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.anthropic-models {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.model-tier {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.tier-label {
  font-weight: bold;
  color: #666;
}

.model-tag {
  margin: 0;
}

.info-icon {
  color: #1890ff;
  cursor: pointer;
  margin-left: 8px;
}

.selected-models {
  margin-top: 16px;
}

.model-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-weight: bold;
}

.model-count {
  color: #666;
  font-size: 12px;
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

.model-info {
  display: flex;
  flex-direction: column;
}

.model-name {
  font-weight: bold;
}

.model-provider {
  font-size: 12px;
  color: #666;
}

.model-controls {
  display: flex;
  gap: 4px;
}

.empty-models {
  text-align: center;
  color: #999;
  padding: 16px;
  font-style: italic;
}

.anthropic-tier {
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 12px;
  height: 100%;
}

.anthropic-tier h4 {
  margin: 0 0 12px 0;
  color: #333;
}
</style>