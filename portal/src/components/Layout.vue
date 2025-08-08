<template>
  <a-layout style="min-height: 100vh">
    <a-layout-sider v-model:collapsed="collapsed" collapsible>
      <div class="logo">
        <h3 style="color: white; margin: 0;">PortBroker</h3>
      </div>
      <a-menu
        v-model:selectedKeys="selectedKeys"
        theme="dark"
        mode="inline"
      >
        <a-menu-item key="dashboard">
          <dashboard-outlined />
          <span>Dashboard</span>
          <router-link to="/"></router-link>
        </a-menu-item>
        <a-menu-item key="playground">
          <code-outlined />
          <span>Playground</span>
          <router-link to="/playground"></router-link>
        </a-menu-item>
        <a-menu-item key="providers">
          <cloud-server-outlined />
          <span>Providers</span>
          <router-link to="/providers"></router-link>
        </a-menu-item>
        <a-menu-item key="strategies">
          <branches-outlined />
          <span>Strategies</span>
          <router-link to="/strategies"></router-link>
        </a-menu-item>
        <a-menu-item key="settings">
          <setting-outlined />
          <span>Settings</span>
          <router-link to="/settings"></router-link>
        </a-menu-item>
        <a-menu-item key="api-keys">
          <key-outlined />
          <span>API Keys</span>
          <router-link to="/api-keys"></router-link>
        </a-menu-item>
      </a-menu>
    </a-layout-sider>
    
    <a-layout>
      <a-layout-header style="background: #fff; padding: 0 24px; display: flex; justify-content: space-between; align-items: center;">
        <a-breadcrumb style="margin: 16px 0">
          <a-breadcrumb-item>Home</a-breadcrumb-item>
          <a-breadcrumb-item>{{ $route.name }}</a-breadcrumb-item>
        </a-breadcrumb>
        <a-button type="link" @click="handleLogout">
          <logout-outlined />
          Logout
        </a-button>
      </a-layout-header>
      
      <a-layout-content style="margin: 24px 16px; padding: 24px; background: #fff">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script>
import {
  DashboardOutlined,
  CodeOutlined,
  CloudServerOutlined,
  BranchesOutlined,
  SettingOutlined,
  KeyOutlined,
  LogoutOutlined
} from '@ant-design/icons-vue'

export default {
  name: 'Layout',
  components: {
    DashboardOutlined,
    CodeOutlined,
    CloudServerOutlined,
    BranchesOutlined,
    SettingOutlined,
    KeyOutlined,
    LogoutOutlined
  },
  data() {
    return {
      collapsed: false,
      selectedKeys: ['dashboard']
    }
  },
  watch: {
    $route(to) {
      this.selectedKeys = [to.name?.toLowerCase() || 'dashboard']
    }
  },
  methods: {
    handleLogout() {
      localStorage.removeItem('token')
      this.$router.push('/login')
    }
  }
}
</script>

<style scoped>
.logo {
  height: 32px;
  margin: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>