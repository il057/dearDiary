<template>
  <div class="fixed inset-0 z-50 bg-[#050505] flex flex-col text-zinc-100 select-text overflow-hidden overscroll-contain animate-in fade-in duration-150">
    <!-- 顶栏控制栏 (极简硬朗细线，适配 iOS PWA 灵动岛安全区) -->
    <header class="flex items-center justify-between px-4 sm:px-8 pwa-safe-top pb-3.5 border-b border-[#18181f] bg-[#08080a] select-none shrink-0">
      <div class="flex items-center space-x-3">
        <button
          @click="handleClose"
          class="inline-flex items-center space-x-1.5 px-2.5 py-1 text-xs text-zinc-400 hover:text-zinc-100 hover:bg-[#16161c] rounded-xs border border-neutral-800 transition-colors cursor-pointer"
        >
          <ArrowLeft class="w-3.5 h-3.5" />
          <span>返回</span>
        </button>

        <div class="flex items-center space-x-2">
          <span class="text-[#dc143c] text-xs leading-none">✦</span>
          <span class="text-xs font-semibold text-zinc-200">
            {{ isBackfillMode ? '补记日记' : '写日记' }}
          </span>
          <span class="text-[11px] text-zinc-500 font-mono hidden sm:inline">
            {{ content.trim().length }} 字
          </span>
        </div>
      </div>

      <!-- 补档、引用与保存控制 -->
      <div class="flex items-center space-x-2 sm:space-x-3">
        <!-- 引用过往日记 -->
        <button
          type="button"
          @click="isQuotePickerOpen = !isQuotePickerOpen"
          class="inline-flex items-center space-x-1 px-2.5 py-1 text-xs rounded-xs border transition-colors cursor-pointer"
          :class="isQuotePickerOpen || quotedDiaries.length > 0
            ? 'bg-[#180a0e] text-[#f43f5e] border-[#dc143c]/60'
            : 'text-zinc-400 hover:text-zinc-200 bg-neutral-900 border-neutral-800'"
          title="引用过往日记"
        >
          <Quote class="w-3.5 h-3.5" />
          <span class="hidden sm:inline">{{ quotedDiaries.length > 0 ? `已引用 (${quotedDiaries.length})` : '引用日记' }}</span>
          <span class="sm:hidden">{{ quotedDiaries.length > 0 ? quotedDiaries.length : '引用' }}</span>
        </button>

        <!-- 切换补档模式 -->
        <button
          type="button"
          @click="isBackfillMode = !isBackfillMode"
          class="inline-flex items-center space-x-1 px-2.5 py-1 text-xs rounded-xs border transition-colors cursor-pointer"
          :class="isBackfillMode
            ? 'bg-[#180a0e] text-[#f43f5e] border-[#dc143c]/60'
            : 'text-zinc-400 hover:text-zinc-200 bg-neutral-900 border-neutral-800'"
          title="修改日期"
        >
          <CalendarClock class="w-3.5 h-3.5" />
          <span>{{ isBackfillMode ? '已选日期' : '补记日期' }}</span>
        </button>

        <!-- 提交保存按钮 (Crimson 风格) -->
        <button
          @click="handleSave"
          :disabled="isSubmitting || !content.trim()"
          class="inline-flex items-center space-x-1.5 px-4 py-1.5 bg-[#dc143c] hover:bg-[#e11d48] text-white font-medium text-xs rounded-xs active:scale-95 disabled:opacity-40 disabled:pointer-events-none transition-all cursor-pointer shadow-[0_0_12px_rgba(220,20,60,0.35)]"
        >
          <Check class="w-3.5 h-3.5" />
          <span>保存</span>
        </button>
      </div>
    </header>

    <!-- 补档时间选择条 (展开态) -->
    <div
      v-if="isBackfillMode"
      class="bg-[#0a0a0d] border-b border-[#18181f] px-4 sm:px-8 py-2.5 flex items-center justify-between flex-wrap gap-2 text-xs select-none"
    >
      <div class="flex items-center space-x-2">
        <Calendar class="w-4 h-4 text-[#dc143c]" />
        <span class="text-zinc-400">日期时间:</span>
        <input
          type="datetime-local"
          v-model="backfillTime"
          class="bg-[#050505] border border-neutral-800 text-zinc-100 rounded-xs px-2.5 py-1 text-xs outline-none focus:border-[#dc143c]"
        />
      </div>

      <div class="flex items-center space-x-1.5 text-[11px]">
        <button
          @click="setQuickDate(-1)"
          class="px-2 py-0.5 bg-neutral-900 hover:bg-neutral-800 text-zinc-400 rounded-xs border border-neutral-800 cursor-pointer"
        >
          昨天
        </button>
        <button
          @click="setQuickDate(-2)"
          class="px-2 py-0.5 bg-neutral-900 hover:bg-neutral-800 text-zinc-400 rounded-xs border border-neutral-800 cursor-pointer"
        >
          前天
        </button>
        <button
          @click="setNoonTime"
          class="px-2 py-0.5 bg-neutral-900 hover:bg-neutral-800 text-zinc-400 rounded-xs border border-neutral-800 cursor-pointer"
          title="设为当天"
        >
          全天
        </button>
        <button
          @click="resetToNow"
          class="px-2 py-0.5 text-zinc-500 hover:text-zinc-300 cursor-pointer"
        >
          重置
        </button>
      </div>
    </div>

    <!-- 引用日记选择器 (展开态) -->
    <div
      v-if="isQuotePickerOpen"
      class="bg-[#0a0a0d] border-b border-[#18181f] px-4 sm:px-8 py-3 space-y-2.5 text-xs select-none"
    >
      <div class="flex items-center space-x-2">
        <Search class="w-3.5 h-3.5 text-[#dc143c] shrink-0" />
        <input
          v-model="quoteSearchQuery"
          type="text"
          placeholder="搜索要引用的过往日记（正文、心情、标签或日期）..."
          class="flex-1 bg-[#050505] border border-neutral-800 text-zinc-100 rounded-xs px-2.5 py-1.5 text-xs outline-none focus:border-[#dc143c]"
        />
        <button
          type="button"
          @click="isQuotePickerOpen = false"
          class="px-2 py-1 text-zinc-500 hover:text-zinc-200 cursor-pointer"
        >
          收起
        </button>
      </div>

      <div v-if="filteredQuoteCandidates.length === 0" class="text-[11px] text-zinc-500 font-mono py-1">
        暂无匹配的日记可引用
      </div>
      <div v-else class="max-h-48 overflow-y-auto space-y-1.5 pr-1">
        <div
          v-for="cand in filteredQuoteCandidates"
          :key="cand.id"
          @click="addQuotedDiary(cand)"
          class="flex items-center justify-between gap-3 p-2 bg-[#060609] hover:bg-[#14090c] border border-[#1a1a22] hover:border-[#dc143c]/50 rounded-xs cursor-pointer transition-colors"
        >
          <div class="min-w-0 flex-1 space-y-0.5">
            <div class="flex items-center space-x-2 text-[11px]">
              <span class="text-xs leading-none" :style="{ color: cand.mood_color || '#dc143c' }">✦</span>
              <span class="font-mono text-zinc-400">{{ formatQuoteTime(cand.created_at) }}</span>
              <span v-if="cand.mood" class="px-1.5 py-0.2 bg-[#12080a] text-[#f43f5e] border border-[#dc143c]/30 rounded-xs text-[10px]">
                {{ cand.mood }}
              </span>
            </div>
            <p class="text-xs text-zinc-300 truncate">{{ cand.summary || cand.content }}</p>
          </div>
          <span class="text-[11px] text-[#f43f5e] font-mono shrink-0">+ 引用</span>
        </div>
      </div>
    </div>

    <!-- 沉浸式长文书写主体 -->
    <main class="flex-1 overflow-y-auto px-4 sm:px-12 md:px-20 py-8 flex flex-col space-y-5">
      <!-- 已引用的日记卡片列表 -->
      <div v-if="quotedDiaries.length > 0" class="space-y-2 shrink-0">
        <div
          v-for="q in quotedDiaries"
          :key="q.id"
          class="relative flex items-start justify-between gap-3 p-3 bg-[#09090d] border border-[#1c1c24] border-l-2 border-l-[#dc143c] rounded-xs"
        >
          <div class="min-w-0 flex-1 space-y-1">
            <div class="flex items-center space-x-2 text-[11px] select-none">
              <Quote class="w-3 h-3 text-[#dc143c] shrink-0" />
              <span class="font-mono text-zinc-400">引用 · {{ formatQuoteTime(q.created_at) }}</span>
              <span v-if="q.mood" class="px-1.5 py-0.2 bg-[#12080a] text-[#f43f5e] border border-[#dc143c]/30 rounded-xs text-[10px]">
                {{ q.mood }}
              </span>
            </div>
            <p class="text-xs text-zinc-300 line-clamp-2 leading-relaxed">
              {{ q.content }}
            </p>
          </div>
          <button
            type="button"
            @click="removeQuotedDiary(q.id)"
            class="p-1 text-zinc-500 hover:text-red-400 transition-colors cursor-pointer shrink-0"
            title="取消引用"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <textarea
        ref="textareaRef"
        v-model="content"
        placeholder="写点什么..."
        class="flex-1 w-full bg-transparent text-sm sm:text-base text-zinc-100 placeholder-neutral-600 focus:outline-none resize-none leading-relaxed tracking-wide font-normal"
        autofocus
        @keydown.ctrl.enter="handleSave"
        @keydown.meta.enter="handleSave"
      ></textarea>
    </main>

    <!-- 底栏快捷提示 -->
    <footer class="px-4 sm:px-8 pt-2.5 pb-[max(env(safe-area-inset-bottom),0.625rem)] border-t border-[#18181f] bg-[#08080a] flex items-center justify-between text-[11px] text-zinc-600 select-none font-mono">
      <span><span class="text-[#dc143c] mr-1">✧</span>Ctrl + Enter 快捷保存 · ESC 退出</span>
      <span>{{ content.trim().length }} 字</span>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ArrowLeft, Check, CalendarClock, Calendar, Quote, Search, X } from '@lucide/vue'

const DRAFT_KEY = 'deardiary_composer_draft'

const props = defineProps({
  initialDate: {
    type: String,
    default: null
  },
  initialQuote: {
    type: Object,
    default: null
  },
  allDiaries: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close', 'save'])

const content = ref('')
const isSubmitting = ref(false)
const isBackfillMode = ref(false)
const backfillTime = ref('')
const quotedDiaries = ref([])
const isQuotePickerOpen = ref(false)
const quoteSearchQuery = ref('')
const textareaRef = ref(null)

const clearDraft = () => {
  try {
    localStorage.removeItem(DRAFT_KEY)
  } catch {
    // ignore
  }
}

const handleClose = () => {
  clearDraft()
  emit('close')
}

const getLocalDatetimeString = (dateObj = new Date()) => {
  const pad = (n) => String(n).padStart(2, '0')
  const y = dateObj.getFullYear()
  const m = pad(dateObj.getMonth() + 1)
  const d = pad(dateObj.getDate())
  const hh = pad(dateObj.getHours())
  const mm = pad(dateObj.getMinutes())
  return `${y}-${m}-${d}T${hh}:${mm}`
}

onMounted(() => {
  let restored = false
  try {
    const raw = localStorage.getItem(DRAFT_KEY)
    if (raw) {
      const draft = JSON.parse(raw)
      if (draft && typeof draft === 'object') {
        if (typeof draft.content === 'string') content.value = draft.content
        if (typeof draft.isBackfillMode === 'boolean') isBackfillMode.value = draft.isBackfillMode
        if (Array.isArray(draft.quotedDiaries)) quotedDiaries.value = draft.quotedDiaries
        if (typeof draft.backfillTime === 'string' && draft.backfillTime) {
          backfillTime.value = draft.backfillTime
          restored = true
        }
      }
    }
  } catch {
    // ignore
  }

  if (props.initialQuote) {
    addQuotedDiary(props.initialQuote)
  }

  if (!restored) {
    if (props.initialDate) {
      const d = new Date(props.initialDate)
      d.setHours(12, 0, 0, 0)
      backfillTime.value = getLocalDatetimeString(d)
      isBackfillMode.value = true
    } else {
      backfillTime.value = getLocalDatetimeString()
    }
  }
})

watch([content, isBackfillMode, backfillTime, quotedDiaries], ([c, backfill, time, quotes]) => {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify({
      content: c,
      isBackfillMode: backfill,
      backfillTime: time,
      quotedDiaries: quotes
    }))
  } catch {
    // ignore
  }
}, { deep: true })

const addQuotedDiary = (diary) => {
  if (!diary) return
  const id = diary.id || diary.diary_id
  if (!id || quotedDiaries.value.some(q => q.id === id)) return
  quotedDiaries.value.push({
    id,
    content: diary.content || '',
    summary: diary.summary || '',
    mood: diary.mood || null,
    mood_color: diary.mood_color || '#dc143c',
    created_at: diary.created_at
  })
  isQuotePickerOpen.value = false
  quoteSearchQuery.value = ''
}

const removeQuotedDiary = (id) => {
  quotedDiaries.value = quotedDiaries.value.filter(q => q.id !== id)
}

const filteredQuoteCandidates = computed(() => {
  const attachedIds = new Set(quotedDiaries.value.map(q => q.id))
  const q = quoteSearchQuery.value.trim().toLowerCase()
  return (props.allDiaries || [])
    .filter(d => {
      const id = d.id || d.diary_id
      if (!id || attachedIds.has(id)) return false
      if (!q) return true
      const text = `${d.content || ''} ${d.summary || ''} ${d.mood || ''} ${(d.entities || []).join(' ')} ${formatQuoteTime(d.created_at)}`.toLowerCase()
      return text.includes(q)
    })
    .slice(0, 12)
})

const formatQuoteTime = (timeStr) => {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  if (isNaN(d.getTime())) return timeStr
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const setQuickDate = (offset) => {
  const d = new Date()
  d.setDate(d.getDate() + offset)
  backfillTime.value = getLocalDatetimeString(d)
}

const setNoonTime = () => {
  const cur = backfillTime.value ? new Date(backfillTime.value) : new Date()
  cur.setHours(12, 0, 0, 0)
  backfillTime.value = getLocalDatetimeString(cur)
}

const resetToNow = () => {
  backfillTime.value = getLocalDatetimeString(new Date())
}

const handleSave = () => {
  if (!content.value.trim() || isSubmitting.value) return
  isSubmitting.value = true

  let customCreatedAt = null
  if (isBackfillMode.value && backfillTime.value) {
    const d = new Date(backfillTime.value)
    if (!isNaN(d.getTime())) {
      customCreatedAt = d.toISOString()
    }
  }

  const quoteIds = quotedDiaries.value.map(q => q.id)
  clearDraft()
  emit('save', {
    content: content.value.trim(),
    created_at: customCreatedAt,
    isBackfill: isBackfillMode.value,
    quoted_diary_ids: quoteIds
  })
}
</script>

