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
      path: '/resources',
      name: 'Resources',
      component: () => import('@/views/ResourceManagement.vue')
    },
    {
      path: '/personnel',
      name: 'Personnel',
      component: () => import('@/views/PersonnelManagement.vue')
    },
    {
      path: '/dependencies',
      name: 'Dependencies',
      component: () => import('@/views/DependencyManagement.vue')
    },
    {
      path: '/activities',
      name: 'Activities',
      component: () => import('@/views/ActivityManagement.vue')
    }
  ]
})

export default router





