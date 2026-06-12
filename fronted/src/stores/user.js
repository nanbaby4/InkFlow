import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getLoginUser, userLogout } from '@/api/userManage.js'

export const useUserStore = defineStore('user', () => {
  const loginUser = ref({ id: 0, userName: '未登录' })

  // 远程获取登录信息
  async function fetchLoginUser() {
    console.log('[fetchLoginUser] 开始获取登录用户信息...')
    try {
      const res = await getLoginUser()
      console.log('[fetchLoginUser] 响应:', res.data)
      if (res.data.code === 0 && res.data.data) {
        loginUser.value = res.data.data
        console.log('[fetchLoginUser] ✅ 已登录:', loginUser.value.userName)
      } else {
        console.warn('[fetchLoginUser] ❌ 未登录, code:', res.data.code)
        loginUser.value = { id: 0, userName: '未登录' }
      }
    } catch (err) {
      console.error('[fetchLoginUser] 请求异常:', err)
      loginUser.value = { id: 0, userName: '未登录' }
    }
  }

  // 退出登录
  async function logout() {
    try {
      await userLogout()
    } catch (err) {
      console.error('[logout] 退出登录请求失败:', err)
    } finally {
      loginUser.value = { id: 0, userName: '未登录' }
    }
  }

  return { loginUser, fetchLoginUser, logout }
})

// 用户角色
export const USER_ROLE_ADMIN = 'admin'
export const USER_ROLE_USER = 'user'

// 默认值
export const DEFAULT_USERNAME = '未登录'
