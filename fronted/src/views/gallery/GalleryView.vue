<template>
  <div class="gallery-page">
    <!-- 加载中 -->
    <div v-if="loading" class="loading-area">
      <a-spin size="large" />
      <p>正在加载作品...</p>
    </div>

    <!-- 空态 -->
    <div v-else-if="articles.length === 0" class="empty-area">
      <div class="empty-icon">📭</div>
      <h2>还没有作品</h2>
      <p>去创作实验室生成你的第一篇文章吧</p>
      <a-button type="primary" size="large" @click="$router.push('/create')">
        🧪 开始创作
      </a-button>
    </div>

    <!-- 卡片网格 -->
    <template v-else>
      <div class="cards-grid">
        <div
          v-for="article in articles"
          :key="article.id"
          class="article-card"
          @click="openDetail(article)"
        >
          <div class="card-cover">
            <img
              v-if="article.coverImage"
              :src="fixUrl(article.coverImage)"
              :alt="article.mainTitle"
            />
            <div v-else class="card-cover-placeholder">
              <span>📝</span>
            </div>
          </div>
          <div class="card-body">
            <h3 class="card-title">{{ article.mainTitle || article.topic || '未命名' }}</h3>
            <p v-if="article.subTitle" class="card-subtitle">{{ article.subTitle }}</p>
            <div class="card-meta">
              <span class="card-time">{{ formatTime(article.createTime) }}</span>
              <a-tag :color="statusColor(article.status)" size="small">
                {{ article.status === 'COMPLETED' ? '已完成' : article.status }}
              </a-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="total > pageSize" class="pagination-area">
        <a-pagination
          v-model:current="currentPage"
          :total="total"
          :page-size="pageSize"
          :show-total="(t) => `共 ${t} 篇`"
          @change="fetchArticles"
        />
      </div>
    </template>

    <!-- 文章详情抽屉 -->
    <a-drawer
      v-model:open="drawerOpen"
      :title="selectedArticle.mainTitle || '文章详情'"
      placement="right"
      :width="720"
      class="article-drawer"
    >
      <template v-if="drawerLoading">
        <div class="drawer-loading"><a-spin size="large" /></div>
      </template>
      <template v-else-if="drawerArticle">
        <div class="drawer-article">
          <div v-if="drawerArticle.coverImage" class="drawer-cover">
            <img :src="fixUrl(drawerArticle.coverImage)" :alt="drawerArticle.mainTitle" />
          </div>
          <div class="article-header">
            <h1>{{ drawerArticle.mainTitle || '未命名' }}</h1>
            <h2 v-if="drawerArticle.subTitle">{{ drawerArticle.subTitle }}</h2>
            <div class="article-meta">
              <span>选题：{{ drawerArticle.topic }}</span>
              <span>创建于 {{ formatTime(drawerArticle.createTime) }}</span>
              <a-tag :color="statusColor(drawerArticle.status)" size="small">
                {{ drawerArticle.status === 'COMPLETED' ? '已完成' : drawerArticle.status }}
              </a-tag>
            </div>
          </div>
          <div class="drawer-content markdown-body" v-html="renderMarkdown(drawerContent)"></div>
        </div>
      </template>

      <template #extra>
        <a-space>
          <a-button size="small" @click="copyDrawerArticle">📋 复制</a-button>
          <a-button size="small" @click="downloadDrawerMd">📥 下载</a-button>
        </a-space>
      </template>
    </a-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { marked } from 'marked'
import { listArticlePage, getArticleDetail } from '@/api/articleManage'

marked.setOptions({ breaks: true, gfm: true })

// --- 列表状态 ---
const loading = ref(true)
const articles = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(12)

// --- 抽屉状态 ---
const drawerOpen = ref(false)
const drawerLoading = ref(false)
const selectedArticle = reactive({})
const drawerArticle = ref(null)

// --- 抽屉正文（合并替换占位符） ---
const drawerContent = computed(() => {
  if (!drawerArticle.value) return ''
  const fc = drawerArticle.value.fullContent
  const c = drawerArticle.value.content
  const images = parseImages(drawerArticle.value.images)
  return replacePlaceholders(fc || c || '', images)
})

// --- 方法 ---
onMounted(() => fetchArticles())

async function fetchArticles(page = 1) {
  loading.value = true
  try {
    const res = await listArticlePage({ current: page, pageSize: pageSize.value })
    if (res.data.code === 0 && res.data.data) {
      const d = res.data.data
      articles.value = (d.records || []).map(normalizeArticle)
      total.value = d.total || 0
      currentPage.value = d.current || page
    }
  } catch (err) {
    console.error('加载文章列表失败:', err)
    message.error('加载文章列表失败')
  } finally {
    loading.value = false
  }
}

/** 统一字段名（兼容 snake_case / camelCase） */
function normalizeArticle(d) {
  return {
    id: d.id,
    taskId: d.taskId ?? d.task_id ?? '',
    topic: d.topic ?? '',
    mainTitle: d.mainTitle ?? d.main_title ?? '',
    subTitle: d.subTitle ?? d.sub_title ?? '',
    content: d.content ?? '',
    fullContent: d.fullContent ?? d.full_content ?? '',
    coverImage: d.coverImage ?? d.cover_image ?? '',
    images: d.images ?? '',
    status: d.status ?? '',
    createTime: d.createTime ?? d.create_time ?? '',
  }
}

async function openDetail(article) {
  Object.assign(selectedArticle, article)
  drawerOpen.value = true
  drawerLoading.value = true
  drawerArticle.value = null

  try {
    const res = await getArticleDetail(article.taskId)
    if (res.data.code === 0 && res.data.data) {
      drawerArticle.value = normalizeArticle(res.data.data)
    } else {
      // 列表数据已够用，直接用缓存
      drawerArticle.value = { ...article }
    }
  } catch {
    drawerArticle.value = { ...article }
  } finally {
    drawerLoading.value = false
  }
}

// --- 工具函数 ---

function fixUrl(url) {
  if (!url) return ''
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) return url
  return 'https://' + url
}

function formatTime(t) {
  if (!t) return ''
  const d = new Date(t)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function statusColor(s) {
  return { COMPLETED: 'green', PROCESSING: 'blue', PENDING: 'orange', FAILED: 'red' }[s] || 'default'
}

function renderMarkdown(text) {
  return text ? marked.parse(text) : ''
}

function parseImages(raw) {
  try {
    if (!raw) return []
    const arr = typeof raw === 'string' ? JSON.parse(raw) : raw
    return Array.isArray(arr) ? arr.filter((img) => img.url) : []
  } catch { return [] }
}

function replacePlaceholders(text, images) {
  if (!text || !images.length) return text
  const posMap = {}
  for (const img of images) {
    if (img.position > 1 && img.url) posMap[img.position] = img
  }
  let result = text
  result = result.replace(/\{+\s*IMAGE_PLACEHOLDER_(\d+)\s*\}+/gi, (_, n) => {
    const img = posMap[parseInt(n) + 1]
    if (!img) return ''
    const alt = img.sectionTitle || img.keywords || '配图'
    return `\n\n![${alt}](${fixUrl(img.url)})\n\n`
  })
  result = result.replace(/\{+\s*ICON_PLACEHOLDER_(\d+)\s*\}+/gi, (_, n) => {
    const img = posMap[parseInt(n) + 1]
    if (!img) return ''
    return `![](${fixUrl(img.url)})`
  })
  return result
}

function copyDrawerArticle() {
  const text = drawerContent.value
  navigator.clipboard.writeText(text).then(() => message.success('已复制'))
    .catch(() => message.error('复制失败'))
}

function downloadDrawerMd() {
  const text = drawerContent.value
  const title = selectedArticle.mainTitle || 'article'
  const blob = new Blob([text], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `${title}.md`
  document.body.appendChild(a); a.click(); document.body.removeChild(a)
  URL.revokeObjectURL(url)
  message.success('下载中...')
}
</script>

<style scoped>
/* ========== 页面布局 ========== */
.gallery-page {
  padding: 24px;
}

.gallery-header {
  text-align: center;
  margin-bottom: 32px;
}

.gallery-title {
  font-size: 2rem;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(135deg, #5b47fb 0%, #e664a7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.gallery-desc {
  margin: 8px 0 0;
  color: var(--text-main, #888);
  font-size: 0.95rem;
}

/* ========== 加载 / 空态 ========== */
.loading-area, .empty-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  color: #999;
}

.empty-icon { font-size: 4rem; margin-bottom: 12px; }
.empty-area h2 { margin: 0 0 8px; color: var(--text-main, #333); }
.empty-area p { margin: 0 0 20px; color: #999; }

/* ========== 卡片网格 ========== */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.article-card {
  background: var(--card-bg, #fff);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  cursor: pointer;
  transition: all 0.3s ease;
}

.article-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 30px rgba(0,0,0,0.12);
}

.card-cover {
  width: 100%;
  aspect-ratio: 16 / 10;
  background: linear-gradient(135deg, #e8e0ff 0%, #ffe0ed 100%);
  overflow: hidden;
}

.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.card-cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 3rem;
}

.card-body {
  padding: 16px;
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  margin: 0 0 4px;
  color: var(--text-main, #222);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-subtitle {
  font-size: 0.85rem;
  color: #999;
  margin: 0 0 10px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-time {
  font-size: 0.8rem;
  color: #bbb;
}

/* ========== 分页 ========== */
.pagination-area {
  display: flex;
  justify-content: center;
  margin-top: 32px;
}

/* ========== 抽屉 ========== */
.drawer-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

.drawer-cover {
  width: 100%;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 20px;
}

.drawer-cover img {
  width: 100%;
  object-fit: cover;
}

.article-header h1 {
  font-size: 1.5rem;
  margin: 0 0 6px;
  color: var(--text-main, #222);
}

.article-header h2 {
  font-size: 1rem;
  font-weight: 400;
  color: #888;
  margin: 0 0 12px;
}

.article-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 0.8rem;
  color: #999;
  margin-bottom: 20px;
}

/* ========== Markdown 正文 ========== */
.markdown-body {
  line-height: 1.9;
  color: var(--text-main, #333);
  word-break: break-all;
  overflow-wrap: break-word;
}

.markdown-body :deep(h1) { font-size: 1.4rem; margin: 1.2rem 0 0.6rem; }
.markdown-body :deep(h2) { font-size: 1.2rem; margin: 1rem 0 0.5rem; }
.markdown-body :deep(h3) { font-size: 1.05rem; margin: 0.8rem 0 0.4rem; }
.markdown-body :deep(p) { margin: 0.5rem 0; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { padding-left: 1.5rem; margin: 0.4rem 0; }
.markdown-body :deep(blockquote) {
  border-left: 4px solid #5b47fb;
  padding: 0.4rem 0.8rem;
  margin: 0.6rem 0;
  background: rgba(91,71,251,0.04);
  border-radius: 0 8px 8px 0;
  color: #666;
}
.markdown-body :deep(code) {
  background: rgba(91,71,251,0.08);
  padding: 0.15em 0.4em;
  border-radius: 4px;
  font-size: 0.9em;
}
.markdown-body :deep(pre) { background: #f6f8fa; padding: 0.8rem; border-radius: 10px; overflow-x: auto; }
.markdown-body :deep(pre code) { background: none; padding: 0; }
.markdown-body :deep(img) { max-width: 100%; border-radius: 8px; margin: 0.5rem 0; }
.markdown-body :deep(table) { border-collapse: collapse; width: 100%; }
.markdown-body :deep(th), .markdown-body :deep(td) { border: 1px solid #e8e8e8; padding: 0.4rem 0.6rem; }
.markdown-body :deep(th) { background: #fafafa; }
.markdown-body :deep(hr) { border: none; border-top: 1px solid #eee; margin: 1rem 0; }

/* ========== 响应式 ========== */
@media (max-width: 900px) {
  .cards-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 480px) {
  .cards-grid { grid-template-columns: 1fr; }
}
</style>
