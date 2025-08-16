<template>
  <div>
    <h1>Dashboard</h1>
    <a-row :gutter="16">
      <a-col :span="6">
        <a-card>
          <a-statistic
            title="Active Providers"
            :value="stats.providers"
            :value-style="{ color: '#3f8600' }"
          >
            <template #prefix>
              <cloud-server-outlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic
            title="Active Strategies"
            :value="stats.strategies"
            :value-style="{ color: '#cf1322' }"
          >
            <template #prefix>
              <branches-outlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic
            title="API Keys"
            :value="stats.apiKeys"
            :value-style="{ color: '#1890ff' }"
          >
            <template #prefix>
              <key-outlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic
            title="Total Requests"
            :value="stats.requests"
            :value-style="{ color: '#722ed1' }"
          >
            <template #prefix>
              <line-chart-outlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>
    
    <a-row :gutter="16" style="margin-top: 24px;">
      <a-col :span="6">
        <a-card>
          <a-statistic
            title="Requests (24h)"
            :value="stats.requests24h"
            :value-style="{ color: '#52c41a' }"
          >
            <template #prefix>
              <bar-chart-outlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic
            title="Avg Response Time"
            :value="stats.avgDuration"
            suffix="ms"
            :value-style="{ color: '#1890ff' }"
          >
            <template #prefix>
              <clock-circle-outlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic
            title="Success Rate"
            :value="stats.successRate"
            suffix="%"
            :value-style="{ color: stats.successRate >= 95 ? '#52c41a' : stats.successRate >= 90 ? '#faad14' : '#f5222d' }"
          >
            <template #prefix>
              <check-circle-outlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic
            title="Active Providers"
            :value="providerStats.length"
            :value-style="{ color: '#722ed1' }"
          >
            <template #prefix>
              <cloud-server-outlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="16" style="margin-top: 24px;">
      <a-col :span="12">
        <a-card title="Recent Activity" style="height: 400px;">
          <a-list :data-source="recentActivity" size="small" :loading="loading.activity">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta>
                  <template #title>
                    <span>{{ item.title }}</span>
                    <a-tag v-if="item.status === 'success'" color="green" size="small" style="margin-left: 8px;">
                      Success
                    </a-tag>
                    <a-tag v-else color="red" size="small" style="margin-left: 8px;">
                      Error
                    </a-tag>
                  </template>
                  <template #description>{{ item.description }}</template>
                </a-list-item-meta>
                <div>
                  <div>{{ item.time }}</div>
                  <div style="font-size: 12px; color: #999;">{{ item.duration }}ms</div>
                </div>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>
      <a-col :span="12">
        <a-card title="Provider Statistics" style="height: 400px;">
          <a-list :data-source="providerStats" size="small" :loading="loading.providers">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta>
                  <template #title>{{ item.provider_name }}</template>
                  <template #description>
                    {{ item.request_count }} requests, {{ item.avg_duration }}ms avg
                  </template>
                </a-list-item-meta>
                <div>
                  <a-progress 
                    :percent="item.success_rate" 
                    size="small" 
                    :stroke-color="item.success_rate >= 95 ? '#52c41a' : item.success_rate >= 90 ? '#faad14' : '#f5222d'"
                  />
                </div>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="16" style="margin-top: 24px;">
      <a-col :span="24">
        <a-card title="Strategy Statistics" style="height: 400px;">
          <a-list :data-source="strategyStats" size="small" :loading="loading.strategies">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta>
                  <template #title>
                    <span>{{ item.strategy_name }}</span>
                    <a-tag :color="item.strategy_type === 'anthropic' ? 'blue' : 'green'" size="small" style="margin-left: 8px;">
                      {{ item.strategy_type }}
                    </a-tag>
                  </template>
                  <template #description>
                    {{ item.request_count }} requests, {{ item.avg_duration }}ms avg response time
                  </template>
                </a-list-item-meta>
                <div style="display: flex; align-items: center; gap: 16px;">
                  <div style="min-width: 100px;">
                    Success Rate: {{ item.success_rate }}%
                  </div>
                  <a-progress 
                    :percent="item.success_rate" 
                    size="small" 
                    :stroke-color="item.success_rate >= 95 ? '#52c41a' : item.success_rate >= 90 ? '#faad14' : '#f5222d'"
                    style="min-width: 100px;"
                  />
                </div>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script>
import {
  CloudServerOutlined,
  BranchesOutlined,
  KeyOutlined,
  LineChartOutlined,
  BarChartOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined
} from '@ant-design/icons-vue'
import axios from 'axios'

export default {
  name: 'Dashboard',
  components: {
    CloudServerOutlined,
    BranchesOutlined,
    KeyOutlined,
    LineChartOutlined,
    BarChartOutlined,
    ClockCircleOutlined,
    CheckCircleOutlined
  },
  data() {
    return {
      stats: {
        providers: 0,
        strategies: 0,
        apiKeys: 0,
        requests: 0,
        requests24h: 0,
        avgDuration: 0,
        successRate: 100
      },
      recentActivity: [],
      providerStats: [],
      strategyStats: [],
      loading: {
        dashboard: false,
        activity: false,
        providers: false,
        strategies: false
      }
    }
  },
  async mounted() {
    await this.loadAllStats()
    // Set up auto-refresh every 30 seconds
    this.refreshInterval = setInterval(() => {
      this.loadAllStats()
    }, 30000)
  },
  beforeUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval)
    }
  },
  methods: {
    async loadAllStats() {
      await Promise.all([
        this.loadDashboardStats(),
        this.loadRecentActivity(),
        this.loadProviderStats(),
        this.loadStrategyStats()
      ])
    },

    async loadDashboardStats() {
      try {
        this.loading.dashboard = true
        const token = localStorage.getItem('token')
        const response = await axios.get('/api/portal/statistics/dashboard', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        this.stats = { ...this.stats, ...response.data }
      } catch (error) {
        console.error('Failed to load dashboard stats:', error)
        this.$message.error('Failed to load dashboard statistics')
      } finally {
        this.loading.dashboard = false
      }
    },

    async loadRecentActivity() {
      try {
        this.loading.activity = true
        const token = localStorage.getItem('token')
        const response = await axios.get('/api/portal/statistics/activity?limit=10', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        this.recentActivity = response.data
      } catch (error) {
        console.error('Failed to load recent activity:', error)
        this.recentActivity = []
      } finally {
        this.loading.activity = false
      }
    },

    async loadProviderStats() {
      try {
        this.loading.providers = true
        const token = localStorage.getItem('token')
        const response = await axios.get('/api/portal/statistics/providers?days=7', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        this.providerStats = response.data
      } catch (error) {
        console.error('Failed to load provider stats:', error)
        this.providerStats = []
      } finally {
        this.loading.providers = false
      }
    },

    async loadStrategyStats() {
      try {
        this.loading.strategies = true
        const token = localStorage.getItem('token')
        const response = await axios.get('/api/portal/statistics/strategies?days=7', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        this.strategyStats = response.data
      } catch (error) {
        console.error('Failed to load strategy stats:', error)
        this.strategyStats = []
      } finally {
        this.loading.strategies = false
      }
    }
  }
}
</script>