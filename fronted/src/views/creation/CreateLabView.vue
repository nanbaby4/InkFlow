<template>
  <div class="create-lab">
    <!-- ==================== 空闲态：纯输入页 ==================== -->
    <div v-if="phase === 'idle'" class="idle-layout">
      <div class="idle-card">
        <div class="idle-header">
          <h1 class="lab-title">🧪 创作实验室</h1>
          <p class="lab-desc">输入选题，AI 多智能体协作完成一篇配图文章</p>
        </div>

        <a-card :bordered="false" class="input-card">
          <a-form :model="formState" layout="vertical" @finish="startGenerate">
            <a-form-item
              label="文章选题"
              name="topic"
              :rules="[{ required: true, message: '请输入文章选题' }]"
            >
              <a-textarea
                v-model:value="formState.topic"
                placeholder="例如：人工智能如何改变教育行业..."
                :auto-size="{ minRows: 3, maxRows: 5 }"
                :maxlength="500"
                show-count
              />
            </a-form-item>

            <a-form-item label="写作风格" name="style">
              <a-select
                v-model:value="formState.style"
                placeholder="选择写作风格（可选）"
                allow-clear
              >
                <a-select-option value="tech">🔧 技术干货</a-select-option>
                <a-select-option value="emotional">💭 情感共鸣</a-select-option>
                <a-select-option value="educational">📚 教育科普</a-select-option>
                <a-select-option value="humorous">😄 轻松幽默</a-select-option>
              </a-select>
            </a-form-item>

            <a-form-item label="补充描述" name="userDescription">
              <a-textarea
                v-model:value="formState.userDescription"
                placeholder="额外要求：目标读者、篇幅、特定角度等..."
                :auto-size="{ minRows: 2, maxRows: 4 }"
                :maxlength="1000"
                show-count
              />
            </a-form-item>

            <a-form-item>
              <a-button type="primary" html-type="submit" size="large" block class="submit-btn">
                🚀 开始创作
              </a-button>
            </a-form-item>
          </a-form>
        </a-card>

        <div class="idle-features">
          <div class="feature-item">
            <span class="feature-icon">🤖</span>
            <span>6个 AI 智能体协作</span>
          </div>
          <div class="feature-item">
            <span class="feature-icon">⚡</span>
            <span>实时流式输出</span>
          </div>
          <div class="feature-item">
            <span class="feature-icon">🎨</span>
            <span>自动配图</span>
          </div>
          <div class="feature-item">
            <span class="feature-icon">📦</span>
            <span>一键导出</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== 非空闲态：左流水线 + 右输出 ==================== -->
    <template v-else>
      <!-- 顶部栏 -->
      <div class="work-header">
        <div class="header-left">
          <h1 class="lab-title">🧪 创作实验室</h1>
          <a-tag v-if="phase === 'generating'" color="processing">创作中</a-tag>
          <a-tag v-else-if="phase === 'completed'" color="success">已完成</a-tag>
          <a-tag v-else-if="phase === 'error'" color="error">出错了</a-tag>
        </div>
        <div class="header-right">
          <a-button v-if="phase === 'completed'" type="primary" size="small" @click="resetLab">
            ✨ 再创作一篇
          </a-button>
          <a-button v-if="phase === 'error'" size="small" @click="resetLab"> 重新开始 </a-button>
        </div>
      </div>

      <div class="work-body">
        <!-- 左侧：流水线 -->
        <div class="pipeline-panel">
          <a-card :bordered="false" class="pipeline-card">
            <div class="card-title"><span class="icon">⚙️</span> 创作流水线</div>
            <div class="pipeline-steps">
              <div
                v-for="(step, idx) in pipelineSteps"
                :key="idx"
                class="step-item"
                :class="{
                  active: step.status === 'active',
                  completed: step.status === 'completed',
                  error: step.status === 'error',
                }"
              >
                <div class="step-indicator">
                  <span v-if="step.status === 'completed'" class="check">✓</span>
                  <a-spin v-else-if="step.status === 'active'" size="small" />
                  <span v-else-if="step.status === 'error'" class="cross">✗</span>
                  <span v-else class="dot">{{ idx + 1 }}</span>
                </div>
                <div class="step-info">
                  <div class="step-name">{{ step.name }}</div>
                  <div class="step-tag">{{ step.tag }}</div>
                </div>
                <div
                  v-if="
                    step.status === 'active' && step.name === '配图生成' && imageProgress.total > 0
                  "
                  class="step-progress"
                >
                  {{ imageProgress.completed }}/{{ imageProgress.total }}
                </div>
              </div>
            </div>
            <a-button
              v-if="phase === 'generating'"
              danger
              block
              size="small"
              class="cancel-btn"
              @click="cancelGenerate"
            >
              取消创作
            </a-button>
          </a-card>
        </div>

        <!-- 右侧：输出 -->
        <div class="output-panel">
          <a-card :bordered="false" class="output-card">
            <a-tabs v-model:activeKey="activeTab" class="output-tabs">
              <!-- 大纲 -->
              <a-tab-pane key="outline" tab="📋 大纲">
                <div class="stream-content" ref="outlineRef">
                  <div
                    v-if="!outlineText && pipelineSteps[1].status === 'pending'"
                    class="placeholder"
                  >
                    等待大纲生成...
                  </div>
                  <div
                    v-else
                    class="markdown-body"
                    v-html="renderMarkdown(outlineText || '')"
                  ></div>
                  <div v-if="pipelineSteps[1].status === 'active'" class="stream-cursor">▊</div>
                </div>
              </a-tab-pane>

              <!-- 正文 -->
              <a-tab-pane key="content" tab="📄 正文">
                <div class="stream-content" ref="contentRef">
                  <div
                    v-if="!contentText && pipelineSteps[2].status === 'pending'"
                    class="placeholder"
                  >
                    等待正文生成...
                  </div>
                  <div
                    v-else
                    class="markdown-body"
                    v-html="renderMarkdown(contentText || '')"
                  ></div>
                  <div v-if="pipelineSteps[2].status === 'active'" class="stream-cursor">▊</div>
                </div>
              </a-tab-pane>

              <!-- 配图 -->
              <a-tab-pane key="images" tab="🖼️ 配图" :badge="imageProgress.total || undefined">
                <div class="images-grid">
                  <div
                    v-if="generatedImages.length === 0 && pipelineSteps[4].status === 'pending'"
                    class="placeholder"
                  >
                    等待配图生成...
                  </div>
                  <div v-for="(img, idx) in generatedImages" :key="idx" class="image-card">
                    <div class="image-wrapper">
                      <img v-if="img.url" :src="img.url" :alt="img.description || '配图'" />
                      <a-spin v-else size="small" />
                    </div>
                    <div class="image-meta">
                      <span class="image-position">位置 #{{ img.position }}</span>
                      <span v-if="img.keywords" class="image-keywords">{{ img.keywords }}</span>
                    </div>
                  </div>
                  <div v-if="pipelineSteps[4].status === 'active'" class="image-card generating">
                    <div class="image-wrapper"><a-spin size="small" /></div>
                    <div class="image-meta">生成中...</div>
                  </div>
                </div>
              </a-tab-pane>

              <!-- 全文预览 -->
              <a-tab-pane key="preview" tab="📰 全文预览" :disabled="phase !== 'completed'">
                <template v-if="phase === 'completed'">
                  <div class="article-preview">
                    <div v-if="articleDetail.coverImage" class="cover-image">
                      <img :src="articleDetail.coverImage" alt="封面图" />
                    </div>
                    <div class="article-header">
                      <h1 class="article-title">{{ articleDetail.mainTitle || '未命名' }}</h1>
                      <h2 v-if="articleDetail.subTitle" class="article-subtitle">
                        {{ articleDetail.subTitle }}
                      </h2>
                      <div class="article-meta">
                        <a-tag
                          v-if="articleDetail.status"
                          :color="statusColor(articleDetail.status)"
                        >
                          {{ articleDetail.status }}
                        </a-tag>
                        <span v-if="articleDetail.createTime"
                          >创建于 {{ articleDetail.createTime }}</span
                        >
                      </div>
                    </div>
                    <div
                      class="article-body markdown-body"
                      v-html="renderMarkdown(mergedContent)"
                    ></div>
                  </div>
                  <div class="export-toolbar">
                    <a-space>
                      <a-button size="small" @click="copyArticle"
                        ><template #icon>📋</template>复制全文</a-button
                      >
                      <a-button size="small" @click="downloadMarkdown"
                        ><template #icon>📥</template>下载 MD</a-button
                      >
                      <a-button size="small" @click="downloadHtml"
                        ><template #icon>🌐</template>下载 HTML</a-button
                      >
                    </a-space>
                  </div>
                </template>
                <div v-else class="placeholder">创作完成后可查看全文预览</div>
              </a-tab-pane>
            </a-tabs>
          </a-card>

          <!-- 错误提示 -->
          <a-card v-if="phase === 'error'" :bordered="false" class="error-card">
            <div class="error-content">
              <span class="error-icon">⚠️</span>
              <h3>创作过程中出现错误</h3>
              <p>{{ errorMessage }}</p>
            </div>
          </a-card>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, watch } from 'vue'
import { message } from 'ant-design-vue'
import { marked } from 'marked'
import { generateArticle, getArticleDetail } from '@/api/articleManage'

marked.setOptions({ breaks: true, gfm: true })

const STEP_DEFS = [
  { name: '标题生成', tag: 'Agent 1', event: 'AGENT1_COMPLETE' },
  { name: '大纲规划', tag: 'Agent 2', event: 'AGENT2_COMPLETE' },
  { name: '正文撰写', tag: 'Agent 3', event: 'AGENT3_COMPLETE' },
  { name: '配图分析', tag: 'Agent 4', event: 'AGENT4_COMPLETE' },
  { name: '配图生成', tag: 'Agent 5', event: 'AGENT5_COMPLETE' },
  { name: '图文合并', tag: 'Merge', event: 'MERGE_COMPLETE' },
]

// --- 状态 ---
const phase = ref('idle')
const activeTab = ref('outline')
const errorMessage = ref('')
const outlineRef = ref(null)
const contentRef = ref(null)

const formState = reactive({ topic: '', style: '', userDescription: '' })

const pipelineSteps = reactive(STEP_DEFS.map((def) => ({ ...def, status: 'pending' })))

const outlineText = ref('')
const contentText = ref('')
const generatedImages = ref([])
const imageProgress = reactive({ total: 0, completed: 0 })

const articleDetail = reactive({
  id: null,
  taskId: '',
  topic: '',
  mainTitle: '',
  subTitle: '',
  outline: '',
  content: '',
  fullContent: '',
  coverImage: '',
  images: '',
  status: '',
  errorMessage: '',
  createTime: '',
  completedTime: '',
  updateTime: '',
})

// 解析 images JSON 字符串 → 图片数组
const parsedImages = computed(() => {
  try {
    const raw = articleDetail.images
    if (!raw) return []
    const arr = typeof raw === 'string' ? JSON.parse(raw) : raw
    return Array.isArray(arr) ? arr.filter((img) => img.url) : []
  } catch {
    return []
  }
})

/**
 * 将正文中的 {IMAGE_PLACEHOLDER_N} / {ICON_PLACEHOLDER_N} 替换为实际图片
 * 兼容单/双花括号、有无空格等变体
 * 后端映射规则：position 2 → PLACEHOLDER_1, position 3 → PLACEHOLDER_2, ...
 */
function replacePlaceholdersWithImages(text, images) {
  if (!text || !images.length) return text

  let result = text

  // 构建 position → ImageResult 映射（排除封面 position=1）
  const posMap = {}
  for (const img of images) {
    if (img.position > 1 && img.url) {
      posMap[img.position] = img
    }
  }

  // 修复缺少协议的 URL
  function fixUrl(url) {
    if (!url || url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:'))
      return url
    return 'https://' + url
  }

  // 兼容单花括号和双花括号的占位符
  result = result.replace(/\{+\s*IMAGE_PLACEHOLDER_(\d+)\s*\}+/gi, (match, n) => {
    const position = parseInt(n) + 1 // PLACEHOLDER_1 → position 2
    const img = posMap[position]
    if (!img) return ''
    const alt = img.sectionTitle || img.keywords || '配图'
    return `\n\n![${alt}](${fixUrl(img.url)})\n\n`
  })

  result = result.replace(/\{+\s*ICON_PLACEHOLDER_(\d+)\s*\}+/gi, (match, n) => {
    const position = parseInt(n) + 1
    const img = posMap[position]
    if (!img) return ''
    return `![](${fixUrl(img.url)})`
  })

  return result
}

// 合并后的正文：优先 fullContent，并用 images 数据替换残留占位符
const mergedContent = computed(() => {
  const fc = articleDetail.fullContent
  const c = articleDetail.content
  const images = parsedImages.value

  if (fc) return replacePlaceholdersWithImages(fc, images)
  if (c) return replacePlaceholdersWithImages(c, images)
  return ''
})

let abortController = null

// --- 方法 ---
const statusColor = (s) =>
  ({ COMPLETED: 'green', PROCESSING: 'blue', PENDING: 'orange', FAILED: 'red' })[s] || 'default'

function renderMarkdown(text) {
  return text ? marked.parse(text) : ''
}

function resetSteps() {
  pipelineSteps.forEach((s) => (s.status = 'pending'))
  generatedImages.value = []
  imageProgress.total = 0
  imageProgress.completed = 0
  outlineText.value = ''
  contentText.value = ''
  Object.keys(articleDetail).forEach((k) => (articleDetail[k] = ''))
  articleDetail.id = null
  activeTab.value = 'outline'
  errorMessage.value = ''
}

function autoScroll(refEl) {
  nextTick(() => {
    if (refEl.value) refEl.value.scrollTop = refEl.value.scrollHeight
  })
}

async function startGenerate() {
  if (!formState.topic.trim()) return

  resetSteps()
  phase.value = 'generating'
  pipelineSteps[0].status = 'active'

  try {
    const result = await generateArticle(
      {
        topic: formState.topic,
        style: formState.style,
        userDescription: formState.userDescription,
      },
      {
        onStart: () => {
          phase.value = 'generating'
        },
        onTitleComplete: () => {
          pipelineSteps[0].status = 'completed'
          pipelineSteps[1].status = 'active'
          activeTab.value = 'outline'
        },
        onOutlineStreaming: (chunk) => {
          outlineText.value += chunk
          autoScroll(outlineRef)
        },
        onOutlineComplete: () => {
          pipelineSteps[1].status = 'completed'
          pipelineSteps[2].status = 'active'
          activeTab.value = 'content'
        },
        onContentStreaming: (chunk) => {
          contentText.value += chunk
          autoScroll(contentRef)
        },
        onContentComplete: () => {
          pipelineSteps[2].status = 'completed'
          pipelineSteps[3].status = 'active'
        },
        onImageAnalysisComplete: (data) => {
          pipelineSteps[3].status = 'completed'
          pipelineSteps[4].status = 'active'
          if (Array.isArray(data)) imageProgress.total = data.length
        },
        onImageComplete: (data) => {
          if (data) {
            generatedImages.value.push(data)
            imageProgress.completed++
          }
        },
        onAllImagesComplete: () => {
          pipelineSteps[4].status = 'completed'
          pipelineSteps[5].status = 'active'
        },
        onMergeComplete: () => {
          pipelineSteps[5].status = 'completed'
        },
        onAllComplete: async () => {
          try {
            const res = await getArticleDetail(result.taskId)
            if (res.data.code === 0 && res.data.data) {
              const d = res.data.data
              // 后端 databases 库返回 ORM 属性名（snake_case），需映射到前端 camelCase
              articleDetail.id = d.id
              articleDetail.taskId = d.taskId ?? d.task_id ?? ''
              articleDetail.topic = d.topic ?? ''
              articleDetail.mainTitle = d.mainTitle ?? d.main_title ?? ''
              articleDetail.subTitle = d.subTitle ?? d.sub_title ?? ''
              articleDetail.outline = d.outline ?? ''
              articleDetail.content = d.content ?? ''
              articleDetail.fullContent = d.fullContent ?? d.full_content ?? ''
              articleDetail.coverImage = d.coverImage ?? d.cover_image ?? ''
              articleDetail.images = d.images ?? ''
              articleDetail.status = d.status ?? ''
              articleDetail.errorMessage = d.errorMessage ?? d.error_message ?? ''
              articleDetail.createTime = d.createTime ?? d.create_time ?? ''
              articleDetail.completedTime = d.completedTime ?? d.completed_time ?? ''
              articleDetail.updateTime = d.updateTime ?? d.update_time ?? ''
              console.log('[CreateLab] fullContent:', articleDetail.fullContent?.substring(0, 200))
            }
          } catch (err) {
            console.error('获取文章详情失败:', err)
          }
          phase.value = 'completed'
          activeTab.value = 'preview'
          message.success('🎉 文章创作完成！')
        },
        onError: (msg) => {
          const activeStep = pipelineSteps.find((s) => s.status === 'active')
          if (activeStep) activeStep.status = 'error'
          errorMessage.value = msg || '未知错误'
          phase.value = 'error'
          message.error(msg || '创作过程中出现错误')
        },
      },
    )
    abortController = result.abort
  } catch (err) {
    if (err.name !== 'AbortError') {
      errorMessage.value = err.message || '网络请求失败'
      phase.value = 'error'
      message.error('生成文章失败: ' + err.message)
    }
  }
}

function cancelGenerate() {
  if (abortController) {
    abortController()
    abortController = null
  }
  phase.value = 'idle'
  resetSteps()
  message.info('已取消创作')
}

function resetLab() {
  phase.value = 'idle'
  resetSteps()
}

async function copyArticle() {
  const text = mergedContent.value
  try {
    await navigator.clipboard.writeText(text)
    message.success('已复制到剪贴板')
  } catch {
    message.error('复制失败，请手动复制')
  }
}

function downloadMarkdown() {
  const text = mergedContent.value
  const title = articleDetail.mainTitle || 'article'
  downloadFile(`${title}.md`, text, 'text/markdown')
}

function downloadHtml() {
  const mdText = mergedContent.value
  const title = articleDetail.mainTitle || '未命名文章'
  const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>${title}</title>
<style>body{max-width:800px;margin:0 auto;padding:2rem;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;line-height:1.8;color:#333}h1{font-size:2rem;border-bottom:2px solid #eee;padding-bottom:.5rem}h2{font-size:1.5rem;margin-top:2rem}h3{font-size:1.2rem}img{max-width:100%;border-radius:8px;margin:1rem 0}blockquote{border-left:4px solid #5b47fb;padding-left:1rem;color:#666;margin:1rem 0}code{background:#f5f5f5;padding:.2em .4em;border-radius:3px;font-size:.9em}pre{background:#f5f5f5;padding:1rem;border-radius:8px;overflow-x:auto}pre code{background:none;padding:0}table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{border:1px solid #ddd;padding:.5rem 1rem;text-align:left}th{background:#f5f5f5}</style>
</head><body>${marked.parse(mdText)}</body></html>`
  downloadFile(`${title}.html`, html, 'text/html')
}

function downloadFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  message.success(`文件 ${filename} 下载中...`)
}

watch(outlineText, (val) => {
  if (val && pipelineSteps[1].status === 'active') activeTab.value = 'outline'
})
watch(contentText, (val) => {
  if (val && pipelineSteps[2].status === 'active') activeTab.value = 'content'
})
</script>

<style scoped>
/* ==================== 空闲态 ==================== */
.idle-layout {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 140px);
}

.idle-card {
  width: 100%;
  max-width: 600px;
}

.idle-header {
  text-align: center;
  margin-bottom: 24px;
}

.lab-title {
  font-size: 2rem;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(135deg, #5b47fb 0%, #a764e6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.lab-desc {
  margin: 8px 0 0;
  color: var(--text-main, #666);
  font-size: 0.95rem;
}

.input-card {
  border-radius: 16px !important;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08) !important;
}

.submit-btn {
  height: 48px;
  font-size: 1.05rem;
  border-radius: 12px;
  background: linear-gradient(135deg, #5b47fb 0%, #a764e6 100%);
  border: none;
  transition: all 0.3s ease;
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(91, 71, 251, 0.35);
}

.idle-features {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 24px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--bg-color, #f9f9f9);
  border-radius: 10px;
  font-size: 0.9rem;
  color: #666;
  justify-content: center;
}

/* ==================== 工作态头部 ==================== */
.work-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.work-header .lab-title {
  font-size: 1.3rem;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* ==================== 工作态主体：左流水线 + 右输出 ==================== */
.work-body {
  display: flex;
  gap: 20px;
  flex: 1;
  min-height: 0;
}

.pipeline-panel {
  width: 260px;
  flex-shrink: 0;
}

.output-panel {
  flex: 1;
  min-width: 0;
}

/* ==================== 流水线卡片 ==================== */
.pipeline-card {
  border-radius: 12px !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06) !important;
  background: var(--card-bg, #fff) !important;
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.pipeline-steps {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.step-item.active {
  background: rgba(91, 71, 251, 0.08);
}
.step-item.completed {
  opacity: 0.7;
}
.step-item.error {
  background: rgba(255, 77, 79, 0.08);
}

.step-indicator {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
  flex-shrink: 0;
  background: var(--bg-color, #f5f5f5);
  color: #999;
}

.step-item.active .step-indicator {
  background: linear-gradient(135deg, #5b47fb, #a764e6);
  color: #fff;
}
.step-item.completed .step-indicator {
  background: #52c41a;
  color: #fff;
}
.step-item.error .step-indicator {
  background: #ff4d4f;
  color: #fff;
}

.check,
.cross {
  font-size: 0.9rem;
  font-weight: 700;
}

.step-info {
  flex: 1;
  min-width: 0;
}
.step-name {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-main, #333);
}
.step-tag {
  font-size: 0.7rem;
  color: #999;
}
.step-item.active .step-name {
  color: #5b47fb;
  font-weight: 600;
}
.step-progress {
  font-size: 0.75rem;
  font-weight: 600;
  color: #5b47fb;
  white-space: nowrap;
}

.cancel-btn {
  margin-top: 10px;
  border-radius: 8px;
}

/* ==================== 输出卡片 ==================== */
.output-card {
  border-radius: 12px !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06) !important;
  background: var(--card-bg, #fff) !important;
  min-height: 500px;
}

.output-tabs {
  margin-top: -8px;
}

/* ==================== 流式内容 ==================== */
.stream-content {
  max-height: calc(100vh - 280px);
  overflow-y: auto;
  padding: 4px 0;
  scroll-behavior: smooth;
}

.stream-content::-webkit-scrollbar {
  width: 6px;
}
.stream-content::-webkit-scrollbar-thumb {
  background: #ddd;
  border-radius: 3px;
}

.placeholder {
  text-align: center;
  color: #bbb;
  padding: 60px 20px;
  font-size: 0.95rem;
}

.stream-cursor {
  display: inline-block;
  color: #5b47fb;
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}

/* ==================== Markdown ==================== */
.markdown-body {
  line-height: 1.9;
  color: var(--text-main, #333);
  word-break: break-all;
  overflow-wrap: break-word;
}
.markdown-body :deep(h1) {
  font-size: 1.5rem;
  margin: 1.2rem 0 0.8rem;
  padding-bottom: 0.4rem;
  border-bottom: 2px solid #f0f0f0;
}
.markdown-body :deep(h2) {
  font-size: 1.25rem;
  margin: 1rem 0 0.6rem;
}
.markdown-body :deep(h3) {
  font-size: 1.1rem;
  margin: 0.8rem 0 0.5rem;
}
.markdown-body :deep(p) {
  margin: 0.5rem 0;
}
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 1.5rem;
  margin: 0.4rem 0;
}
.markdown-body :deep(li) {
  margin: 0.2rem 0;
}
.markdown-body :deep(blockquote) {
  border-left: 4px solid #5b47fb;
  padding: 0.4rem 0.8rem;
  margin: 0.6rem 0;
  background: rgba(91, 71, 251, 0.04);
  border-radius: 0 8px 8px 0;
  color: #666;
}
.markdown-body :deep(code) {
  background: rgba(91, 71, 251, 0.08);
  padding: 0.15em 0.4em;
  border-radius: 4px;
  font-size: 0.9em;
  font-family: 'SFMono-Regular', Consolas, monospace;
}
.markdown-body :deep(pre) {
  background: #f6f8fa;
  padding: 0.8rem;
  border-radius: 10px;
  overflow-x: auto;
  margin: 0.6rem 0;
}
.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 0.6rem 0;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #e8e8e8;
  padding: 0.4rem 0.6rem;
  text-align: left;
}
.markdown-body :deep(th) {
  background: #fafafa;
  font-weight: 600;
}
.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: 10px;
  margin: 0.6rem 0;
}
.markdown-body :deep(strong) {
  font-weight: 600;
  color: #222;
}
.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid #eee;
  margin: 1rem 0;
}

/* ==================== 配图 ==================== */
.images-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  padding: 4px 0;
}
.image-card {
  background: var(--bg-color, #f9f9f9);
  border-radius: 12px;
  overflow: hidden;
}
.image-card.generating {
  border: 2px dashed #ddd;
}
.image-wrapper {
  width: 100%;
  aspect-ratio: 16/10;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.image-wrapper img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.image-meta {
  padding: 6px 10px;
  font-size: 0.75rem;
  color: #888;
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.image-keywords {
  color: #5b47fb;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ==================== 文章预览 ==================== */
.article-preview {
  padding: 4px 0;
}
.cover-image {
  width: 100%;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 20px;
}
.cover-image img {
  width: 100%;
  object-fit: cover;
}
.article-header {
  margin-bottom: 20px;
}
.article-title {
  font-size: 1.6rem;
  font-weight: 700;
  margin: 0 0 6px;
  color: var(--text-main, #222);
}
.article-subtitle {
  font-size: 1rem;
  font-weight: 400;
  color: #888;
  margin: 0 0 10px;
}
.article-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.8rem;
  color: #999;
}
.export-toolbar {
  margin-top: 20px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: flex-end;
}

/* ==================== 错误 ==================== */
.error-card {
  margin-top: 12px;
}
.error-content {
  text-align: center;
  padding: 24px 16px;
}
.error-icon {
  font-size: 2.5rem;
  display: block;
  margin-bottom: 8px;
}
.error-content h3 {
  margin: 0 0 6px;
  color: #ff4d4f;
}
.error-content p {
  color: #888;
  margin: 0;
}

/* ==================== 响应式 ==================== */
@media (max-width: 768px) {
  .work-body {
    flex-direction: column;
  }
  .pipeline-panel {
    width: 100%;
  }
  .pipeline-steps {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 4px;
  }
  .step-item {
    flex-direction: column;
    text-align: center;
    gap: 4px;
    padding: 8px 4px;
  }
  .idle-features {
    grid-template-columns: 1fr;
  }
}
</style>
