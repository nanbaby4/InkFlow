<template>
  <div class="create-lab">
    <!-- 页面头部 -->
    <div class="lab-header">
      <div class="header-left">
        <h1 class="lab-title">🧪 创作实验室</h1>
        <p class="lab-desc">输入选题，AI 多智能体协作完成一篇配图文章</p>
      </div>
      <div class="header-right">
        <a-button v-if="phase === 'completed'" type="primary" @click="resetLab">
          ✨ 再创作一篇
        </a-button>
      </div>
    </div>

    <!-- 主体区域 -->
    <div class="lab-body" :class="{ 'is-generating': phase === 'generating' }">
      <!-- 左侧：输入面板 -->
      <div class="input-panel" :class="{ collapsed: phase !== 'idle' }">
        <a-card :bordered="false" class="input-card">
          <div class="card-title"><span class="icon">📝</span> 创作灵感</div>

          <a-form :model="formState" layout="vertical" @finish="startGenerate">
            <!-- 选题 -->
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
                :disabled="phase === 'generating'"
              />
            </a-form-item>

            <!-- 风格选择 -->
            <a-form-item label="写作风格" name="style">
              <a-select
                v-model:value="formState.style"
                placeholder="选择写作风格（可选）"
                :disabled="phase === 'generating'"
                allow-clear
              >
                <a-select-option value="tech">🔧 技术干货</a-select-option>
                <a-select-option value="emotional">💭 情感共鸣</a-select-option>
                <a-select-option value="educational">📚 教育科普</a-select-option>
                <a-select-option value="humorous">😄 轻松幽默</a-select-option>
              </a-select>
            </a-form-item>

            <!-- 补充描述 -->
            <a-form-item label="补充描述" name="userDescription">
              <a-textarea
                v-model:value="formState.userDescription"
                placeholder="额外要求：目标读者、篇幅、特定角度等..."
                :auto-size="{ minRows: 2, maxRows: 4 }"
                :maxlength="1000"
                show-count
                :disabled="phase === 'generating'"
              />
            </a-form-item>

            <!-- 提交按钮 -->
            <a-form-item>
              <a-button
                type="primary"
                html-type="submit"
                size="large"
                block
                :loading="phase === 'generating'"
                :disabled="phase === 'generating'"
                class="submit-btn"
              >
                <template v-if="phase === 'generating'">
                  <a-spin size="small" /> 创作中...
                </template>
                <template v-else> 🚀 开始创作 </template>
              </a-button>
            </a-form-item>
          </a-form>
        </a-card>

        <!-- 流水线步骤 -->
        <a-card v-if="phase !== 'idle'" :bordered="false" class="pipeline-card">
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
              <div v-if="step.status === 'active'" class="step-progress">
                <div v-if="step.name === '配图生成' && imageProgress.total > 0" class="image-count">
                  {{ imageProgress.completed }}/{{ imageProgress.total }}
                </div>
              </div>
            </div>
          </div>
          <!-- 取消按钮 -->
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

      <!-- 右侧：主内容区 -->
      <div class="main-panel">
        <!-- 空闲态：引导页 -->
        <div v-if="phase === 'idle'" class="guide-area">
          <div class="guide-content">
            <div class="guide-icon">✨</div>
            <h2>开始你的创作之旅</h2>
            <p>
              输入文章选题，AI 多智能体将协作完成：<br />
              <strong>标题构思</strong> → <strong>大纲规划</strong> → <strong>正文撰写</strong> →
              <strong>智能配图</strong> → <strong>图文合并</strong>
            </p>
            <div class="guide-features">
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

        <!-- 生成态：流式输出 -->
        <div
          v-if="phase === 'generating' || phase === 'completed' || phase === 'error'"
          class="output-area"
        >
          <a-card :bordered="false" class="output-card">
            <!-- 标签页切换 -->
            <a-tabs v-model:activeKey="activeTab" class="output-tabs">
              <!-- 大纲标签 -->
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

              <!-- 正文标签 -->
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

              <!-- 配图标签 -->
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
                    <div class="image-wrapper">
                      <a-spin size="small" />
                    </div>
                    <div class="image-meta">生成中...</div>
                  </div>
                </div>
              </a-tab-pane>

              <!-- 全文预览标签 -->
              <a-tab-pane key="preview" tab="📰 全文预览" :disabled="phase !== 'completed'">
                <div v-if="phase === 'completed'" class="article-preview">
                  <!-- 封面图 -->
                  <div v-if="articleDetail.coverImage" class="cover-image">
                    <img :src="articleDetail.coverImage" alt="封面图" />
                  </div>

                  <!-- 标题区 -->
                  <div class="article-header">
                    <h1 class="article-title">{{ articleDetail.mainTitle || '未命名' }}</h1>
                    <h2 v-if="articleDetail.subTitle" class="article-subtitle">
                      {{ articleDetail.subTitle }}
                    </h2>
                    <div class="article-meta">
                      <a-tag v-if="articleDetail.status" :color="statusColor(articleDetail.status)">
                        {{ articleDetail.status }}
                      </a-tag>
                      <span v-if="articleDetail.createTime"
                        >创建于 {{ articleDetail.createTime }}</span
                      >
                    </div>
                  </div>

                  <!-- 正文内容 -->
                  <div
                    class="article-body markdown-body"
                    v-html="
                      renderMarkdown(articleDetail.fullContent || articleDetail.content || '')
                    "
                  ></div>
                </div>
                <div v-else class="placeholder">创作完成后可查看全文预览</div>
              </a-tab-pane>
            </a-tabs>

            <!-- 导出工具栏 -->
            <div v-if="phase === 'completed'" class="export-toolbar">
              <a-space>
                <a-button @click="copyArticle"> <template #icon>📋</template> 复制全文 </a-button>
                <a-button @click="downloadMarkdown">
                  <template #icon>📥</template> 下载 Markdown
                </a-button>
                <a-button @click="downloadHtml"> <template #icon>🌐</template> 下载 HTML </a-button>
              </a-space>
            </div>
          </a-card>

          <!-- 错误态 -->
          <a-card v-if="phase === 'error'" :bordered="false" class="error-card">
            <div class="error-content">
              <span class="error-icon">⚠️</span>
              <h3>创作过程中出现错误</h3>
              <p>{{ errorMessage }}</p>
              <a-button type="primary" @click="resetLab">重新开始</a-button>
            </div>
          </a-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, watch } from 'vue'
import { message } from 'ant-design-vue'
import { marked } from 'marked'
import { generateArticle, getArticleDetail } from '@/api/articleManage'

// --- 配置 marked ---
marked.setOptions({
  breaks: true,
  gfm: true,
})

// --- 流水线步骤定义 ---
const STEP_DEFS = [
  { name: '标题生成', tag: 'Agent 1', event: 'AGENT1_COMPLETE' },
  { name: '大纲规划', tag: 'Agent 2', event: 'AGENT2_COMPLETE' },
  { name: '正文撰写', tag: 'Agent 3', event: 'AGENT3_COMPLETE' },
  { name: '配图分析', tag: 'Agent 4', event: 'AGENT4_COMPLETE' },
  { name: '配图生成', tag: 'Agent 5', event: 'AGENT5_COMPLETE' },
  { name: '图文合并', tag: 'Merge', event: 'MERGE_COMPLETE' },
]

// --- 状态 ---
const phase = ref('idle') // idle | generating | completed | error
const activeTab = ref('outline')
const errorMessage = ref('')
const outlineRef = ref(null)
const contentRef = ref(null)

// 表单
const formState = reactive({
  topic: '',
  style: '',
  userDescription: '',
})

// 五个智能体流水线步骤状态
const pipelineSteps = reactive(
  STEP_DEFS.map((def) => ({
    ...def,
    status: 'pending', // pending | active | completed | error
  })),
)

// 流式文本
const outlineText = ref('')
const contentText = ref('')

// 图片
const generatedImages = ref([])
const imageProgress = reactive({ total: 0, completed: 0 })

// 文章详情
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

// 取消控制器
let abortController = null

// --- 计算属性 ---
const statusColor = (status) => {
  const map = { COMPLETED: 'green', PROCESSING: 'blue', PENDING: 'orange', FAILED: 'red' }
  return map[status] || 'default'
}

// --- 方法 ---

/** 渲染 Markdown 为 HTML */
function renderMarkdown(text) {
  if (!text) return ''
  return marked.parse(text)
}

/** 重置步骤状态 */
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

/** 开始生成 */
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

        onTitleComplete: (data) => {
          pipelineSteps[0].status = 'completed'
          pipelineSteps[1].status = 'active'
          activeTab.value = 'outline'
        },

        onOutlineStreaming: (chunk) => {
          outlineText.value += chunk
          autoScroll(outlineRef)
        },

        onOutlineComplete: (data) => {
          pipelineSteps[1].status = 'completed'
          pipelineSteps[2].status = 'active'
          activeTab.value = 'content'
        },

        onContentStreaming: (chunk) => {
          contentText.value += chunk
          autoScroll(contentRef)
        },

        onContentComplete: (data) => {
          pipelineSteps[2].status = 'completed'
          pipelineSteps[3].status = 'active'
        },

        onImageAnalysisComplete: (data) => {
          pipelineSteps[3].status = 'completed'
          pipelineSteps[4].status = 'active'
          // data 可能包含图片需求数量
          if (Array.isArray(data)) {
            imageProgress.total = data.length
          }
        },

        onImageComplete: (data) => {
          if (data) {
            generatedImages.value.push(data)
            imageProgress.completed++
          }
        },

        onAllImagesComplete: (data) => {
          pipelineSteps[4].status = 'completed'
          pipelineSteps[5].status = 'active'
        },

        onMergeComplete: (data) => {
          pipelineSteps[5].status = 'completed'
        },

        onAllComplete: async (data) => {
          // 全部完成，获取完整文章
          const taskId = result.taskId
          try {
            const res = await getArticleDetail(taskId)
            if (res.data.code === 0 && res.data.data) {
              console.log('articleDetail', articleDetail)
              Object.assign(articleDetail, res.data.data)
            }
          } catch (err) {
            console.error('获取文章详情失败:', err)
          }
          phase.value = 'completed'
          activeTab.value = 'preview'
          message.success('🎉 文章创作完成！')
        },

        onError: (msg) => {
          // 标记当前活跃步骤为错误
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
    console.error('生成文章失败:', err)
    if (err.name !== 'AbortError') {
      errorMessage.value = err.message || '网络请求失败'
      phase.value = 'error'
      message.error('生成文章失败: ' + err.message)
    }
  }
}

/** 取消生成 */
function cancelGenerate() {
  if (abortController) {
    abortController()
    abortController = null
  }
  phase.value = 'idle'
  resetSteps()
  message.info('已取消创作')
}

/** 重置页面 */
function resetLab() {
  phase.value = 'idle'
  resetSteps()
  activeTab.value = 'outline'
}

/** 自动滚动到内容底部 */
function autoScroll(refEl) {
  nextTick(() => {
    if (refEl.value) {
      refEl.value.scrollTop = refEl.value.scrollHeight
    }
  })
}

/** 复制全文 */
async function copyArticle() {
  const text = articleDetail.fullContent || articleDetail.content || ''
  try {
    await navigator.clipboard.writeText(text)
    message.success('已复制到剪贴板')
  } catch {
    message.error('复制失败，请手动复制')
  }
}

/** 下载为 Markdown 文件 */
function downloadMarkdown() {
  const text = articleDetail.fullContent || articleDetail.content || ''
  const title = articleDetail.mainTitle || 'article'
  downloadFile(`${title}.md`, text, 'text/markdown')
}

/** 下载为 HTML 文件 */
function downloadHtml() {
  const mdText = articleDetail.fullContent || articleDetail.content || ''
  const title = articleDetail.mainTitle || '未命名文章'
  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title}</title>
  <style>
    body { max-width: 800px; margin: 0 auto; padding: 2rem; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.8; color: #333; }
    h1 { font-size: 2rem; border-bottom: 2px solid #eee; padding-bottom: 0.5rem; }
    h2 { font-size: 1.5rem; margin-top: 2rem; }
    h3 { font-size: 1.2rem; }
    img { max-width: 100%; border-radius: 8px; margin: 1rem 0; }
    blockquote { border-left: 4px solid #5b47fb; padding-left: 1rem; color: #666; margin: 1rem 0; }
    code { background: #f5f5f5; padding: 0.2em 0.4em; border-radius: 3px; font-size: 0.9em; }
    pre { background: #f5f5f5; padding: 1rem; border-radius: 8px; overflow-x: auto; }
    pre code { background: none; padding: 0; }
    table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
    th, td { border: 1px solid #ddd; padding: 0.5rem 1rem; text-align: left; }
    th { background: #f5f5f5; }
  </style>
</head>
<body>
  ${marked.parse(mdText)}
</body>
</html>`
  downloadFile(`${title}.html`, htmlContent, 'text/html')
}

/** 通用文件下载 */
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

// 监听大纲/正文更新，自动切换标签
watch(outlineText, (val) => {
  if (val && pipelineSteps[1].status === 'active') {
    activeTab.value = 'outline'
  }
})
watch(contentText, (val) => {
  if (val && pipelineSteps[2].status === 'active') {
    activeTab.value = 'content'
  }
})
</script>

<style scoped>
/* ========== 页面整体布局 ========== */
.create-lab {
  min-height: calc(100vh - 140px);
  display: flex;
  flex-direction: column;
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

/* ========== 头部 ========== */
.lab-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
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

/* ========== 主体两栏布局 ========== */
.lab-body {
  display: flex;
  gap: 24px;
  flex: 1;
  align-items: flex-start;
}

.input-panel {
  width: 380px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  transition: width 0.3s ease;
}

.input-panel.collapsed {
  width: 340px;
}

.main-panel {
  flex: 1;
  min-width: 0;
}

/* ========== 卡片通用 ========== */
.input-card,
.pipeline-card,
.output-card {
  background: var(--card-bg, #fff) !important;
  border-radius: 16px !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06) !important;
}

.card-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-title .icon {
  font-size: 1.2rem;
}

/* ========== 表单 ========== */
.submit-btn {
  height: 48px;
  font-size: 1.05rem;
  border-radius: 12px;
  background: linear-gradient(135deg, #5b47fb 0%, #a764e6 100%);
  border: none;
  transition: all 0.3s ease;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(91, 71, 251, 0.35);
}

/* ========== 流水线步骤 ========== */
.pipeline-steps {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  transition: all 0.3s ease;
  position: relative;
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
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 600;
  flex-shrink: 0;
  background: var(--bg-color, #f5f5f5);
  color: #999;
  transition: all 0.3s ease;
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
  font-size: 1rem;
  font-weight: 700;
}

.step-info {
  flex: 1;
  min-width: 0;
}

.step-name {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-main, #333);
}

.step-tag {
  font-size: 0.75rem;
  color: #999;
  margin-top: 2px;
}

.step-item.active .step-name {
  color: #5b47fb;
  font-weight: 600;
}

.image-count {
  font-size: 0.8rem;
  font-weight: 600;
  color: #5b47fb;
  white-space: nowrap;
}

.cancel-btn {
  margin-top: 12px;
  border-radius: 8px;
}

/* ========== 主内容区 ========== */
.guide-area {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 500px;
}

.guide-content {
  text-align: center;
  max-width: 520px;
}

.guide-icon {
  font-size: 4rem;
  margin-bottom: 16px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.guide-content h2 {
  font-size: 1.5rem;
  margin: 0 0 12px;
  color: var(--text-main, #333);
}

.guide-content p {
  color: #888;
  line-height: 1.8;
  margin: 0 0 24px;
}

.guide-features {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  text-align: left;
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
}

.feature-icon {
  font-size: 1.1rem;
}

/* ========== 输出区域 ========== */
.output-area {
  min-height: 500px;
}

.output-tabs {
  margin-top: -8px;
}

/* ========== 流式内容 ========== */
.stream-content {
  max-height: 55vh;
  overflow-y: auto;
  padding: 8px 0;
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
  font-size: 1.1rem;
  animation: blink 1s step-end infinite;
  margin-left: 2px;
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

/* ========== Markdown 内容样式 ========== */
.markdown-body {
  line-height: 1.9;
  color: var(--text-main, #333);
  word-break: break-all;
  overflow-wrap: break-word;
}

.markdown-body :deep(h1) {
  font-size: 1.6rem;
  margin: 1.5rem 0 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #f0f0f0;
}

.markdown-body :deep(h2) {
  font-size: 1.35rem;
  margin: 1.3rem 0 0.8rem;
}

.markdown-body :deep(h3) {
  font-size: 1.15rem;
  margin: 1.1rem 0 0.6rem;
}

.markdown-body :deep(p) {
  margin: 0.6rem 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 1.5rem;
  margin: 0.5rem 0;
}

.markdown-body :deep(li) {
  margin: 0.3rem 0;
}

.markdown-body :deep(blockquote) {
  border-left: 4px solid #5b47fb;
  padding: 0.5rem 1rem;
  margin: 0.8rem 0;
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
  padding: 1rem;
  border-radius: 10px;
  overflow-x: auto;
  margin: 0.8rem 0;
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 0.8rem 0;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #e8e8e8;
  padding: 0.5rem 0.8rem;
  text-align: left;
}

.markdown-body :deep(th) {
  background: #fafafa;
  font-weight: 600;
}

.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: 10px;
  margin: 0.8rem 0;
}

.markdown-body :deep(strong) {
  font-weight: 600;
  color: #222;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid #eee;
  margin: 1.2rem 0;
}

/* ========== 配图网格 ========== */
.images-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  padding: 8px 0;
}

.image-card {
  background: var(--bg-color, #f9f9f9);
  border-radius: 12px;
  overflow: hidden;
  transition: transform 0.2s ease;
}

.image-card:hover {
  transform: translateY(-2px);
}

.image-wrapper {
  width: 100%;
  aspect-ratio: 16 / 10;
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
  padding: 8px 12px;
  font-size: 0.8rem;
  color: #888;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.image-keywords {
  color: #5b47fb;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.image-card.generating {
  border: 2px dashed #ddd;
}

/* ========== 文章预览 ========== */
.article-preview {
  padding: 8px 0;
}

.cover-image {
  width: 100%;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 24px;
}

.cover-image img {
  width: 100%;
  object-fit: cover;
}

.article-header {
  margin-bottom: 24px;
}

.article-title {
  font-size: 1.8rem;
  font-weight: 700;
  margin: 0 0 8px;
  color: var(--text-main, #222);
}

.article-subtitle {
  font-size: 1.1rem;
  font-weight: 400;
  color: #888;
  margin: 0 0 12px;
}

.article-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.85rem;
  color: #999;
}

/* ========== 导出工具栏 ========== */
.export-toolbar {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: flex-end;
}

/* ========== 错误态 ========== */
.error-card {
  margin-top: 16px;
}

.error-content {
  text-align: center;
  padding: 32px 20px;
}

.error-icon {
  font-size: 3rem;
  display: block;
  margin-bottom: 12px;
}

.error-content h3 {
  margin: 0 0 8px;
  color: #ff4d4f;
}

.error-content p {
  color: #888;
  margin: 0 0 20px;
}

/* ========== 响应式 ========== */
@media (max-width: 900px) {
  .lab-body {
    flex-direction: column;
  }

  .input-panel,
  .input-panel.collapsed {
    width: 100%;
  }

  .guide-features {
    grid-template-columns: 1fr;
  }

  .images-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  }

  .lab-header {
    flex-direction: column;
    gap: 12px;
  }
}
</style>
