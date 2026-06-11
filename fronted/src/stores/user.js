import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getLoginUser } from '@/api/userManage.js'

export const useUserStore = defineStore('user', () => {
  const loginUser = ref({ id: 0, userName: '未登录' })

  // 远程获取登录信息
  async function fetchLoginUser() {
    console.log('fetchLoginUser')
    try {
      const res = await getLoginUser()
      if (res.data.code === 0 && res.data.data) {
        loginUser.value = res.data.data
      } else {
        loginUser.value = { id: 0 }
      }
    } catch (err) {
      loginUser.value = { id: 0 }
    }
  }

  return { loginUser, fetchLoginUser }
})

// 用户角色
export const USER_ROLE_ADMIN = 'admin'
export const USER_ROLE_USER = 'user'

// 默认值
export const DEFAULT_USERNAME = '未登录'
