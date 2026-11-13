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

      <!-- 补档与保存控制 -->
      <div class="flex items-center space-x-2 sm:space-x-3">
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

    <!-- 沉浸式长文书写主体 -->
    <main class="flex-1 overflow-y-auto px-4 sm:px-12 md:px-20 py-8 flex flex-col">
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
import { ref, watch, onMounted } from 'vue'
import { ArrowLeft, Check, CalendarClock, Calendar } from '@lucide/vue'

const DRAFT_KEY = 'deardiary_composer_draft'

const props = defineProps({
  initialDate: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['close', 'save'])

const content = ref('')
const isSubmitting = ref(false)
const isBackfillMode = ref(false)
const backfillTime = ref('')
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
        if (typeof draft.backfillTime === 'string' && draft.backfillTime) {
          backfillTime.value = draft.backfillTime
          restored = true
        }
      }
    }
  } catch {
    // ignore
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

watch([content, isBackfillMode, backfillTime], ([c, backfill, time]) => {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify({
      content: c,
      isBackfillMode: backfill,
      backfillTime: time
    }))
  } catch {
    // ignore
  }
})

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

  clearDraft()
  emit('save', {
    content: content.value.trim(),
    created_at: customCreatedAt,
    isBackfill: isBackfillMode.value
  })
}
</script>

