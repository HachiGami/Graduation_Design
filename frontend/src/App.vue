<template>
  <div id="app">
    <el-container>
      <el-aside width="256px" class="bg-white border-r border-slate-100 shadow-sm">
        <div class="logo-area">
          <div class="w-8 h-8 bg-blue-50 border border-blue-100 rounded-lg flex items-center justify-center mr-3 shrink-0 transition-colors hover:bg-blue-100 cursor-default">
            <el-icon :size="18" class="text-blue-600"><Platform /></el-icon>
          </div>
          <span class="logo-text">乳业生产与调度系统</span>
        </div>
        <el-menu
          :default-active="$route.path"
          router
          class="sidebar-menu"
        >
          <el-menu-item index="/dependencies">
            <span>生产链路拓扑图</span>
          </el-menu-item>
          <el-menu-item index="/">
            <span>生产活动管理</span>
          </el-menu-item>
          <el-menu-item index="/personnel">
            <span>员工管理</span>
          </el-menu-item>
          <el-menu-item index="/equipment">
            <span>生产设备管理</span>
          </el-menu-item>
          <el-menu-item index="/material">
            <span>原料库存调度</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-main class="bg-slate-50">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { Platform } from '@element-plus/icons-vue'
</script>

<style>
#app {
  height: 100vh;
}

.el-container {
  height: 100%;
}

.el-aside {
  background-color: #ffffff;
  border-right: 1px solid #f1f5f9;
  box-shadow: 1px 0 2px 0 rgba(0, 0, 0, 0.05);
}

.logo-area {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 12px;
  border-bottom: 1px solid #f1f5f9;
}

.logo-text {
  font-weight: 700;
  font-size: 16px;
  color: #1e293b;
}

.sidebar-menu {
  border-right: none !important;
}

.sidebar-menu .el-menu-item {
  color: #64748b;
  margin: 4px 12px;
  border-radius: 6px;
  height: 44px;
  line-height: 44px;
}

.sidebar-menu .el-menu-item.is-active {
  background-color: #eff6ff !important;
  color: #1d4ed8 !important;
  font-weight: 600;
  position: relative;
}

.sidebar-menu .el-menu-item.is-active::before {
  content: '';
  position: absolute;
  left: -12px;
  top: 0;
  bottom: 0;
  width: 4px;
  background-color: #3b82f6;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
}

.el-main {
  padding: 24px;
  background-color: #f8fafc;
}

body {
  margin: 0;
  padding: 0;
}
</style>






