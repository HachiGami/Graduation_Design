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
      path: '/dependencies',
      name: 'Dependencies',
      component: () => import('@/views/DependencyManagement.vue')
    }
  ]
})

export default router






