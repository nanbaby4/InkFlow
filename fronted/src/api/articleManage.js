import request from '@/request'

/**
 * 生成文章（SSE 流式接口）
 * POST /api/article/generate
 * @param {Object} data
 * @param {string} data.topic - 文章主题 (必填, 1-500字符)
 * @param {string} [data.style=''] - 文章风格: tech/emotional/educational/humorous
 * @param {string} [data.userDescription=''] - 用户补充描述 (最多1000字符)
 * @param {Object} [callbacks] - SSE 事件回调
 * @param {Function} [callbacks.onStart] - 生成开始
 * @param {Function} [callbacks.onTitleComplete] - 标题生成完成 (AGENT1_COMPLETE)
 * @param {Function} [callbacks.onOutlineStreaming] - 大纲流式输出中 (AGENT2_STREAMING)
 * @param {Function} [callbacks.onOutlineComplete] - 大纲生成完成 (AGENT2_COMPLETE)
 * @param {Function} [callbacks.onContentStreaming] - 正文流式输出中 (AGENT3_STREAMING)
 * @param {Function} [callbacks.onContentComplete] - 正文生成完成 (AGENT3_COMPLETE)
 * @param {Function} [callbacks.onImageAnalysisComplete] - 图片需求分析完成 (AGENT4_COMPLETE)
 * @param {Function} [callbacks.onImageComplete] - 单张图片生成完成 (IMAGE_COMPLETE), data: ImageResult
 * @param {Function} [callbacks.onAllImagesComplete] - 所有图片生成完成 (AGENT5_COMPLETE)
 * @param {Function} [callbacks.onMergeComplete] - 图文合并完成 (MERGE_COMPLETE)
 * @param {Function} [callbacks.onAllComplete] - 全部完成 (ALL_COMPLETE)
 * @param {Function} [callbacks.onError] - 出错 (ERROR), data: string
 * @returns {Promise<{ taskId: string, abort: Function }>} 返回 taskId 和取消函数
 */
export async function generateArticle(data, callbacks = {}) {
  const controller = new AbortController()
  const baseURL = request.defaults.baseURL

  const response = await fetch(`${baseURL}/article/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({
      topic: data.topic,
      style: Array.isArray(data.style) ? data.style[0] || '' : (data.style || ''),
      userDescription: data.userDescription || '',
    }),
    signal: controller.signal,
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    if (callbacks.onError) {
      callbacks.onError(errorData.message || '请求失败')
    }
    throw new Error(errorData.message || '请求失败')
  }

  // 用对象包装 taskId，确保返回值和流处理共享同一引用
  const taskIdRef = { value: '' }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  async function processStream() {
    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let currentEvent = ''
        let currentData = ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            currentData = line.slice(6).trim()
          } else if (line === '' && currentEvent) {
            // 一个完整的 SSE 消息结束
            if (currentEvent === 'START') {
              const parsed = parseJSON(currentData)
              if (parsed && parsed.taskId) taskIdRef.value = parsed.taskId
            }
            handleEvent(currentEvent, currentData, callbacks)
            currentEvent = ''
            currentData = ''
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError' && callbacks.onError) {
        callbacks.onError(err.message)
      }
    }
  }

  // 不阻塞，返回后由调用方自行 await 或忽略
  processStream()

  return {
    get taskId() { return taskIdRef.value },
    abort: () => controller.abort(),
  }
}

/**
 * 处理 SSE 事件分发
 * @param {string} eventType
 * @param {string} data
 * @param {Object} callbacks
 */
function handleEvent(eventType, data, callbacks) {
  switch (eventType) {
    case 'START':
      callbacks.onStart?.()
      break
    case 'AGENT1_COMPLETE':
      callbacks.onTitleComplete?.(parseJSON(data))
      break
    case 'AGENT2_STREAMING':
      callbacks.onOutlineStreaming?.(data)
      break
    case 'AGENT2_COMPLETE':
      callbacks.onOutlineComplete?.(parseJSON(data))
      break
    case 'AGENT3_STREAMING':
      callbacks.onContentStreaming?.(data)
      break
    case 'AGENT3_COMPLETE':
      callbacks.onContentComplete?.(parseJSON(data))
      break
    case 'AGENT4_COMPLETE':
      callbacks.onImageAnalysisComplete?.(parseJSON(data))
      break
    case 'IMAGE_COMPLETE':
      callbacks.onImageComplete?.(parseJSON(data))
      break
    case 'AGENT5_COMPLETE':
      callbacks.onAllImagesComplete?.(parseJSON(data))
      break
    case 'MERGE_COMPLETE':
      callbacks.onMergeComplete?.(parseJSON(data))
      break
    case 'ALL_COMPLETE':
      callbacks.onAllComplete?.(parseJSON(data))
      break
    case 'ERROR':
      callbacks.onError?.(data)
      break
    default:
      break
  }
}

/**
 * 安全解析 JSON，失败时返回原始值
 * @param {string} str
 * @returns {any}
 */
function parseJSON(str) {
  if (!str) return null
  try {
    return JSON.parse(str)
  } catch {
    return str
  }
}

/**
 * 获取文章详情
 * GET /api/article/detail
 * @param {string} taskId - 文章任务ID
 * @returns {Promise} Axios 响应, res.data.data 结构:
 *   { id, taskId, userId, topic, mainTitle, subTitle, outline, content,
 *     fullContent, coverImage, images, status, errorMessage,
 *     createTime, completedTime, updateTime, isDelete }
 */
export async function getArticleDetail(taskId) {
  return request('/article/detail', {
    method: 'GET',
    params: { taskId },
  })
}

/**
 * 分页查询文章列表（当前用户）
 * POST /api/article/list/page
 * @param {Object} data
 * @param {number} [data.current=1] - 当前页码
 * @param {number} [data.pageSize=10] - 每页条数 (1-50)
 * @returns {Promise} Axios 响应, res.data.data 结构:
 *   { records: Article[], total: number, current: number, pageSize: number }
 */
export async function listArticlePage(data) {
  return request('/article/list/page', {
    method: 'POST',
    data: {
      current: data.current || 1,
      pageSize: data.pageSize || 10,
    },
  })
}

/**
 * 删除文章（软删除，仅作者可删除）
 * POST /api/article/delete
 * @param {number} id - 文章主键ID
 * @returns {Promise} Axios 响应
 */
export async function deleteArticle(id) {
  return request('/article/delete', {
    method: 'POST',
    data: { id },
  })
}
