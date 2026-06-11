// @ts-ignore
/* eslint-disable */
import request from '@/request'

/** Health Check 健康检查 GET /api/health */
export async function healthCheckApiHealthGet(options) {
  return request('/api/health', {
    method: 'GET',
    ...(options || {}),
  })
}
