<template>
  <div id="app">
    <el-container>
      <el-aside width="200px">
        <el-menu
          :default-active="$route.path"
          router
          background-color="#545c64"
          text-color="#fff"
          active-text-color="#ffd04b"
        >
          <el-menu-item index="/">
            <span>活动管理面板</span>
          </el-menu-item>
          <el-menu-item index="/personnel">
            <span>员工管理面板</span>
          </el-menu-item>
          <el-menu-item index="/equipment">
            <span>设备管理面板</span>
          </el-menu-item>
          <el-menu-item index="/material">
            <span>原料管理面板</span>
          </el-menu-item>
          <el-menu-item index="/dependencies">
            <span>节点关联视图</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
</script>

<style>
#app {
  height: 100vh;
}

.el-container {
  height: 100%;
}

.el-aside {
  background-color: #545c64;
}

.el-main {
  padding: 20px;
}

body {
  margin: 0;
  padding: 0;
}
</style>






