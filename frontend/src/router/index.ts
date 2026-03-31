import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('@/views/DataDashboard.vue')
    },
    {
      path: '/personnel',
      name: 'Personnel',
      component: () => import('@/views/PersonnelDashboard.vue')
    },
    {
      path: '/dependencies',
      name: 'Dependencies',
      // 支持 query 参数: highlightDomain, focusActivity
      component: () => import('@/views/DependencyManagement.vue')
    }
  ]
})

export default router






