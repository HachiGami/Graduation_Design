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
            <span>数据面板</span>
          </el-menu-item>
          <el-menu-item index="/resources">
            <span>资源管理</span>
          </el-menu-item>
          <el-menu-item index="/personnel">
            <span>人员管理</span>
          </el-menu-item>
          <el-menu-item index="/dependencies">
            <span>依赖关系</span>
          </el-menu-item>
          <el-menu-item index="/activities">
            <span>生产活动</span>
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






