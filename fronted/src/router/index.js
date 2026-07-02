import { createRouter, createWebHistory } from 'vue-router'
import BasicLayout from '@/layouts/BasicLayout.vue'
import { userLogin } from '@/api/userManage.js'
import { useUserStore } from '@/stores/user.js'

const routes = [
  {
    path: '/',
    name: '主站',
    component: BasicLayout,
    children: [
      {
        path: '/',
        name: '灵感森林',
        component: () => import('@/views/HomeView.vue'),
      },
      {
        path: 'create',
        name: '创作实验室',
        component: () => import('@/views/creation/CreateLabView.vue'),
      },
    ],
  },
  {
    path: '/user',
    name: '用户中心',
    children: [
      {
        path: 'login',
        name: '✨ 召唤登录',
        component: () => import('@/views/user/LoginView.vue'),
      },
      {
        path: 'register',
        name: '🌱 注册新芽',
        component: () => import('@/views/user/RegisterView.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  if (userStore.loginUser.id === 0) {
    await userStore.fetchLoginUser()
  }

  // 定义哪些页面必须登录才能看（比如创作页和管理页）
  const protectedPaths = ['/create', '/admin', '/gallery']
  const needsLogin = protectedPaths.some(path => to.path.startsWith(path))

  if (needsLogin && userStore.loginUser.id === 0) {
    next(`/user/login?redirect=${to.fullPath}`)
  } else {
    next()
  }
})

export default router
