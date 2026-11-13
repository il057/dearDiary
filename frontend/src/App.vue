<template>
  <div
    class="bg-[#050505] text-zinc-100 flex flex-col justify-between selection:bg-[#dc143c] selection:text-white relative"
    :class="activeTab === 'cluster' ? 'h-[100dvh] overflow-hidden overscroll-none' : 'min-h-screen'"
  >
    <!-- 全局 Toast 提示通知 (Crimson 风格) -->
    <div class="fixed top-5 left-0 right-0 z-50 flex justify-center pointer-events-none">
      <Transition name="toast-slide">
        <div
          v-if="toastMessage"
          class="flex items-center space-x-2 px-4 py-2 rounded-xs bg-[#0c0c0f]/95 text-zinc-100 border border-[#24242c] backdrop-blur-md text-xs font-mono"
        >
          <span class="text-xs leading-none" :class="toastType === 'success' ? 'text-[#dc143c]' : 'text-amber-400'">{{ toastType === 'success' ? '✦' : '✧' }}</span>
          <span>{{ toastMessage }}</span>
        </div>
      </Transition>
    </div>

    <!-- 顶部固定导航区 (使用 pwa-safe-top 预留足够缓冲，彻底避开 iOS PWA 灵动岛与顶部模糊) -->
    <header class="sticky top-0 z-30 bg-[#050505]/95 backdrop-blur-md border-b border-[#18181d] px-4 sm:px-8 pwa-safe-top pb-3.5 select-none">
      <div class="w-full flex items-center justify-between gap-3 sm:gap-6">
        <!-- 左侧菜单按钮与 Logo -->
        <div class="flex items-center space-x-2 sm:space-x-3 shrink-0">
          <button
            @click="isSideMenuOpen = true"
            class="p-2 text-zinc-400 hover:text-zinc-100 hover:bg-[#141418] rounded-xs border border-[#1f1f26] cursor-pointer transition-colors"
            title="打开导览日历与菜单"
          >
            <Menu class="w-4 h-4" />
          </button>

          <div class="flex items-center space-x-1.5 cursor-pointer group" @click="activeTab = 'timeline'">
            <span class="text-[#dc143c] text-sm leading-none group-hover:scale-110 transition-transform">✦</span>
            <h1 class="text-sm sm:text-base font-semibold tracking-wider text-white font-mono uppercase">dearDiary</h1>
            <span class="text-zinc-600 text-xs leading-none hidden sm:inline">✧</span>
          </div>
        </div>

        <!-- 右侧全宽搜索框 -->
        <div class="flex-1 max-w-5xl ml-auto">
          <HeaderSearch @search="handleSearch" @clear="handleClearSearch" />
        </div>
      </div>
    </header>

    <!-- 主内容区：全宽展开，无缝贴合 -->
    <main
      class="flex-1 w-full"
      :class="activeTab === 'cluster' ? 'min-h-0 px-3 sm:px-8 py-3 sm:py-4 flex flex-col overflow-hidden' : 'px-4 sm:px-8 py-5 space-y-4'"
    >
      <!-- 搜索状态提示条 (Crimson 风格) -->
      <div v-if="isSearchMode" class="flex items-center justify-between p-3 bg-[#0d0a0b] border border-[#dc143c]/30 rounded-xs text-xs">
        <div class="flex items-center space-x-2 text-zinc-300 flex-wrap gap-y-1">
          <span class="text-[#dc143c] text-xs leading-none">✦</span>
          <span class="text-zinc-500">语义检索:</span>
          <span class="font-medium text-[#f43f5e]">"{{ currentQuery }}"</span>
          <span v-if="expandedList.length" class="text-zinc-500">
            (扩散关联: {{ expandedList.join(', ') }})
          </span>
        </div>
        <button @click="handleClearSearch" class="text-zinc-400 hover:text-white underline text-[11px] ml-2 shrink-0 cursor-pointer">
          退出检索
        </button>
      </div>

      <!-- 时间轴模式 -->
      <div v-show="activeTab === 'timeline'" class="space-y-4">
        <!-- 1. 近一周记录状态打卡条 (Header 下方) -->
        <WeeklyTracker
          :diaries="diaries"
          @jump-to-date="handleJumpToDate"
          @create-for-today="openComposer()"
        />

        <!-- 2. 主页快捷创建新日记按钮/输入卡片 (点击打开新页面独立写作) -->
        <div
          @click="openComposer()"
          class="w-full bg-[#09090c] hover:bg-[#0d0d12] border border-[#1a1a22] hover:border-[#dc143c]/50 rounded-xs p-3.5 sm:p-4 text-xs transition-all duration-200 cursor-pointer flex items-center justify-between group"
        >
          <div class="flex items-center space-x-3 text-zinc-500 group-hover:text-zinc-300">
            <span class="p-1 rounded-xs bg-[#180a0e] text-[#dc143c] border border-[#dc143c]/30">
              <Plus class="w-3.5 h-3.5" />
            </span>
            <span class="font-mono text-zinc-400 group-hover:text-zinc-200">
              记录此时此刻的想法、随笔，或补档往事...
            </span>
          </div>
          <div class="flex items-center space-x-2">
            <span class="text-[10px] text-zinc-600 font-mono hidden sm:inline">✧ 新页面专注撰写</span>
            <span class="text-[#dc143c] text-xs font-mono">✦ 写日记 ➔</span>
          </div>
        </div>

        <!-- 3. 时间轴错落卡片流 -->
        <TimelineView
          ref="timelineRef"
          :items="isSearchMode ? searchResults : diaries"
          :loading="loading"
          :processing-ids="processingIds"
          @select-diary="handleSelectDiary"
        />
      </div>

      <!-- 星系聚类模式 (全宽锁屏展示，禁止 iOS PWA 上下滚动) -->
      <div v-if="activeTab === 'cluster'" class="flex-1 min-h-0 w-full">
        <ClusterView @open-diary="handleOpenDiaryById" />
      </div>
    </main>

    <!-- 侧边菜单抽屉 (包含月历左右滑动、模式切换、认知管理，移除原移动端 footer) -->
    <SideMenu
      :is-open="isSideMenuOpen"
      :active-tab="activeTab"
      :diaries="diaries"
      @close="isSideMenuOpen = false"
      @change-tab="switchTab"
      @scroll-to-top="handleScrollToTop"
      @scroll-to-oldest="handleScrollToOldest"
      @jump-to-date="handleJumpToDate"
      @open-knowledge="isKnowledgeOpen = true"
      @export-json="handleExportJson"
      @export-md="handleExportMarkdown"
      @import-json="handleImportJson"
    />

    <!-- 独立新页面：新建日记与长文写作 (Composer View) -->
    <DiaryComposerView
      v-if="isComposerOpen"
      :initial-date="composerInitialDate"
      @close="isComposerOpen = false"
      @save="handleSaveNewDiary"
    />

    <!-- 独立新页面：查看完整长文详情与编辑 (Detail & Edit View) -->
    <DiaryDetailView
      v-if="selectedDiary"
      :diary="selectedDiary"
      :is-processing="processingIds.has(selectedDiary.id || selectedDiary.diary_id)"
      @close="selectedDiary = null"
      @update="handleUpdateDiary"
      @delete="handleDeleteDiary"
      @reindex="handleReindexSingle"
      @filter-tag="handleFilterTag"
      @update-entities="handleUpdateDiaryEntities"
    />

    <!-- 认知词典与别名对齐弹窗 -->
    <KnowledgeModal
      :is-open="isKnowledgeOpen"
      @close="isKnowledgeOpen = false"
      @updated="handleKnowledgeUpdated"
      @entity-deleted="handleEntityDeleted"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, onBeforeUnmount } from 'vue'
import { Plus, Menu } from '@lucide/vue'
import HeaderSearch from './components/HeaderSearch.vue'
import WeeklyTracker from './components/WeeklyTracker.vue'
import TimelineView from './components/TimelineView.vue'
import ClusterView from './components/ClusterView.vue'
import SideMenu from './components/SideMenu.vue'
import DiaryComposerView from './components/DiaryComposerView.vue'
import DiaryDetailView from './components/DiaryDetailView.vue'
import KnowledgeModal from './components/KnowledgeModal.vue'
import { diaryApi } from './api/diary'

const activeTab = ref('timeline')

watch(activeTab, (tab) => {
  if (tab === 'cluster') {
    window.scrollTo(0, 0)
    document.documentElement.classList.add('cluster-lock')
  } else {
    document.documentElement.classList.remove('cluster-lock')
  }
}, { immediate: true })
const isSideMenuOpen = ref(false)
const isKnowledgeOpen = ref(false)
const isComposerOpen = ref(false)
const composerInitialDate = ref(null)
const selectedDiary = ref(null)

const diaries = ref([])
const searchResults = ref([])
const expandedList = ref([])

const loading = ref(false)
const isSearchMode = ref(false)
const currentQuery = ref('')
const processingIds = reactive(new Set())
const timelineRef = ref(null)

const toastMessage = ref('')
const toastType = ref('success')
let toastTimer = null

const showToast = (msg, type = 'success') => {
  if (toastTimer) clearTimeout(toastTimer)
  toastMessage.value = msg
  toastType.value = type
  toastTimer = setTimeout(() => {
    toastMessage.value = ''
  }, 2200)
}

const switchTab = (tab) => {
  activeTab.value = tab
  isSideMenuOpen.value = false
}

const openComposer = (dateStr = null) => {
  composerInitialDate.value = dateStr
  isComposerOpen.value = true
}

const handleSelectDiary = (diary) => {
  selectedDiary.value = diary
}

const handleOpenDiaryById = async (id) => {
  const existing = diaries.value.find(d => (d.id || d.diary_id) === id)
  if (existing) {
    selectedDiary.value = existing
    return
  }
  try {
    const res = await diaryApi.getSingleDiary(id)
    if (res.data) selectedDiary.value = res.data
  } catch {
    showToast('无法加载该日记详情', 'error')
  }
}

const handleJumpToDate = (dateStr) => {
  activeTab.value = 'timeline'
  if (timelineRef.value) {
    timelineRef.value.scrollToDate(dateStr)
  }
}

const handleScrollToTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const handleScrollToOldest = () => {
  if (timelineRef.value) {
    timelineRef.value.scrollToOldest()
  }
}

const pollDiaryUntilFinished = (id, maxAttempts = 12) => {
  processingIds.add(id)
  let attempts = 0
  const timer = setInterval(async () => {
    attempts++
    try {
      const res = await diaryApi.getSingleDiary(id)
      if (res.data) {
        const hasEntities = res.data.entities && res.data.entities.length > 0
        const hasMood = !!res.data.mood
        if (hasEntities || hasMood || attempts >= maxAttempts) {
          const idx = diaries.value.findIndex(d => (d.id || d.diary_id) === id)
          if (idx !== -1) {
            diaries.value[idx] = res.data
          }
          if (selectedDiary.value && (selectedDiary.value.id || selectedDiary.value.diary_id) === id) {
            selectedDiary.value = res.data
          }
          processingIds.delete(id)
          clearInterval(timer)
        }
      }
    } catch {
      processingIds.delete(id)
      clearInterval(timer)
    }
  }, 1200)
}

const fetchDiaries = async (force = false) => {
  if (!force && diaries.value.length > 0) return
  loading.value = true
  try {
    const res = await diaryApi.getDiaries()
    diaries.value = res.data
  } catch (err) {
    showToast('无法连接后端服务', 'error')
  } finally {
    loading.value = false
  }
}

const handleSaveNewDiary = async (payload) => {
  isComposerOpen.value = false
  const tempId = Date.now()
  const optimisticCreatedAt = payload.created_at || new Date().toISOString()
  const optimisticItem = {
    id: tempId,
    content: payload.content,
    mood_color: '#dc143c',
    created_at: optimisticCreatedAt,
    entities: []
  }

  diaries.value.unshift(optimisticItem)
  diaries.value.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))

  showToast(payload.isBackfill ? '过往日记已补档，正在分析...' : '已记录，正在分析...')

  try {
    const res = await diaryApi.createDiary(payload.content, payload.created_at)
    const idx = diaries.value.findIndex(d => d.id === tempId)
    if (idx !== -1) {
      diaries.value[idx] = res.data
      diaries.value.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    }
    pollDiaryUntilFinished(res.data.id)
  } catch {
    showToast('保存异常，正在自动重试', 'error')
  }
}

const handleUpdateDiary = async (payload) => {
  const targetId = payload.id
  const idx = diaries.value.findIndex(d => (d.id || d.diary_id) === targetId)
  if (idx !== -1) {
    diaries.value[idx].content = payload.content
    if (payload.created_at) {
      diaries.value[idx].created_at = payload.created_at
      diaries.value.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    }
  }

  if (selectedDiary.value && (selectedDiary.value.id || selectedDiary.value.diary_id) === targetId) {
    selectedDiary.value.content = payload.content
    if (payload.created_at) {
      selectedDiary.value.created_at = payload.created_at
    }
  }

  showToast('已保存修改')

  try {
    const res = await diaryApi.updateDiary(targetId, payload.content, payload.created_at)
    if (idx !== -1) {
      diaries.value[idx] = res.data
      diaries.value.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    }
    if (selectedDiary.value && (selectedDiary.value.id || selectedDiary.value.diary_id) === targetId) {
      selectedDiary.value = res.data
    }
    pollDiaryUntilFinished(targetId)
  } catch {
    showToast('网络短暂波动，已自动存盘', 'error')
  }
}

const handleDeleteDiary = async (id) => {
  if (!confirm('确定删除该条记忆吗？')) return
  try {
    await diaryApi.deleteDiary(id)
    diaries.value = diaries.value.filter(d => (d.id || d.diary_id) !== id)
    if (selectedDiary.value && (selectedDiary.value.id || selectedDiary.value.diary_id) === id) {
      selectedDiary.value = null
    }
    showToast('已删除记录')
  } catch {
    showToast('删除失败', 'error')
  }
}

const handleReindexSingle = async (id) => {
  processingIds.add(id)
  showToast('正在重算本篇向量与实体...')
  try {
    const res = await diaryApi.reindexSingle(id)
    const idx = diaries.value.findIndex(d => (d.id || d.diary_id) === id)
    if (idx !== -1) {
      diaries.value[idx] = res.data
    }
    if (selectedDiary.value && (selectedDiary.value.id || selectedDiary.value.diary_id) === id) {
      selectedDiary.value = res.data
    }
    showToast('重算完成')
  } catch (err) {
    const msg = err?.response?.data?.detail || '重算失败（远端模型可能超时）'
    showToast(msg, 'error')
  } finally {
    processingIds.delete(id)
  }
}

const handleUpdateDiaryEntities = async (payload) => {
  try {
    await diaryApi.updateDiaryEntities(payload.id, payload.entities)
    const idx = diaries.value.findIndex(d => (d.id || d.diary_id) === payload.id)
    if (idx !== -1) {
      diaries.value[idx].entities = payload.entities
    }
    if (selectedDiary.value && (selectedDiary.value.id || selectedDiary.value.diary_id) === payload.id) {
      selectedDiary.value.entities = payload.entities
    }
    showToast('标签已更新')
  } catch {
    showToast('修改标签失败', 'error')
  }
}

const handleSearch = async (q) => {
  if (!q) return
  currentQuery.value = q
  isSearchMode.value = true
  activeTab.value = 'timeline'
  loading.value = true
  try {
    const res = await diaryApi.search(q)
    searchResults.value = res.data.results
    expandedList.value = res.data.expanded_entities
  } catch {
    showToast('检索出错', 'error')
  } finally {
    loading.value = false
  }
}

const handleClearSearch = () => {
  isSearchMode.value = false
  currentQuery.value = ''
  searchResults.value = []
  expandedList.value = []
}

const handleFilterTag = (ent) => {
  if (selectedDiary.value) {
    selectedDiary.value = null
  }
  handleSearch(ent)
}

const handleKnowledgeUpdated = async () => {
  showToast('词典关系已对齐，请按需重算日记')
}

const handleEntityDeleted = (name) => {
  diaries.value.forEach(d => {
    if (d.entities) {
      d.entities = d.entities.filter(e => e !== name)
    }
  })
  showToast(`已解绑「${name}」`)
}

// 导出全量 JSON 备份
const handleExportJson = async () => {
  try {
    showToast('正在打包 JSON 备份...')
    const res = await diaryApi.exportDiaries()
    const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const dateStr = new Date().toISOString().slice(0, 10)
    a.href = url
    a.download = `dearDiary_backup_${dateStr}.json`
    a.click()
    URL.revokeObjectURL(url)
    showToast(`已导出 ${res.data.total} 篇日记`)
  } catch {
    showToast('导出 JSON 失败', 'error')
  }
}

// 导出 Markdown 阅读文档
const handleExportMarkdown = async () => {
  try {
    showToast('正在生成 Markdown 手账...')
    const res = await diaryApi.exportDiaries()
    const items = res.data.diaries || []
    let md = `# dearDiary 个人记忆手账\n\n导出时间: ${new Date().toLocaleString()}\n总计: ${items.length} 篇\n\n---\n\n`
    items.forEach(item => {
      const dt = item.created_at ? item.created_at.replace('T', ' ').slice(0, 16) : ''
      const tags = (item.entities || []).map(e => `#${e}`).join(' ')
      const mood = item.mood ? ` · 心境: ${item.mood}` : ''
      md += `### ${dt}${mood}\n\n${item.content}\n\n`
      if (tags) md += `> ${tags}\n\n`
      md += `---\n\n`
    })
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const dateStr = new Date().toISOString().slice(0, 10)
    a.href = url
    a.download = `dearDiary_${dateStr}.md`
    a.click()
    URL.revokeObjectURL(url)
    showToast(`已导出 ${items.length} 篇 Markdown`)
  } catch {
    showToast('导出 Markdown 失败', 'error')
  }
}

// 从 JSON 备份导入日记（自动去重）
const handleImportJson = async (file) => {
  try {
    const text = await file.text()
    const parsed = JSON.parse(text)
    const list = Array.isArray(parsed) ? parsed : (parsed.diaries || [])
    if (!Array.isArray(list) || list.length === 0) {
      showToast('未在文件中发现有效日记数据', 'error')
      return
    }
    showToast(`正在导入 ${list.length} 条记录...`)
    const res = await diaryApi.importDiaries(list)
    await fetchDiaries(true)
    isSideMenuOpen.value = false
    showToast(`导入完成: 新增 ${res.data.imported} 篇，跳过重复 ${res.data.skipped} 篇`)
  } catch (err) {
    showToast('导入失败：请确认 JSON 格式正确', 'error')
  }
}

// 当任何全屏独立页面或侧边栏打开时，锁定底层 body 滚动，彻底消除双滚动条与滚动穿透
watch(
  [isSideMenuOpen, isKnowledgeOpen, isComposerOpen, selectedDiary],
  ([menu, knowledge, composer, detail]) => {
    const hasOverlay = Boolean(menu || knowledge || composer || detail)
    document.body.style.overflow = hasOverlay ? 'hidden' : ''
  }
)

onMounted(() => {
  fetchDiaries()
})

onBeforeUnmount(() => {
  document.body.style.overflow = ''
  document.documentElement.classList.remove('cluster-lock')
})
</script>

<style scoped>
.toast-slide-enter-active,
.toast-slide-leave-active {
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.toast-slide-enter-from,
.toast-slide-leave-to {
  opacity: 0;
  transform: translateY(-16px);
}
</style>
