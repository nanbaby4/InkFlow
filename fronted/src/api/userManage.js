import request from '@/request'

export async function userLogin(data) {
  return request('/user/login', {
    method: 'POST',
    data,
  })
}

export async function getLoginUser() {
  return request('/user/getLoginUser', {
    method: 'GET',
  })
}
