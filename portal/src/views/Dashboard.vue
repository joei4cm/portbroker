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
      <a-col :span="12">
        <a-card title="Recent Activity" style="height: 400px;">
          <a-list :data-source="recentActivity" size="small">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta>
                  <template #title>{{ item.title }}</template>
                  <template #description>{{ item.description }}</template>
                </a-list-item-meta>
                <div>{{ item.time }}</div>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>
      <a-col :span="12">
        <a-card title="System Status" style="height: 400px;">
          <a-list :data-source="systemStatus" size="small">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta>
                  <template #title>{{ item.name }}</template>
                  <template #description>{{ item.status }}</template>
                </a-list-item-meta>
                <a-tag :color="item.status === 'Online' ? 'green' : 'red'">
                  {{ item.status }}
                </a-tag>
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
  LineChartOutlined
} from '@ant-design/icons-vue'

export default {
  name: 'Dashboard',
  components: {
    CloudServerOutlined,
    BranchesOutlined,
    KeyOutlined,
    LineChartOutlined
  },
  data() {
    return {
      stats: {
        providers: 0,
        strategies: 0,
        apiKeys: 0,
        requests: 0
      },
      recentActivity: [
        { title: 'Provider Added', description: 'OpenAI provider configured', time: '2 min ago' },
        { title: 'Strategy Updated', description: 'OpenAI strategy modified', time: '5 min ago' },
        { title: 'API Key Generated', description: 'New API key created', time: '1 hour ago' },
        { title: 'System Restart', description: 'PortBroker service restarted', time: '2 hours ago' }
      ],
      systemStatus: [
        { name: 'PortBroker API', status: 'Online' },
        { name: 'Database', status: 'Online' },
        { name: 'Provider Services', status: 'Online' },
        { name: 'Authentication', status: 'Online' }
      ]
    }
  },
  async mounted() {
    await this.loadStats()
  },
  methods: {
    async loadStats() {
      // This would load real stats from the API
      // For now, using placeholder data
      this.stats = {
        providers: 3,
        strategies: 2,
        apiKeys: 5,
        requests: 1250
      }
    }
  }
}
</script>