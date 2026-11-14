<template>
  <div>
    <!-- 暗色遮罩背景 -->
    <Transition name="fade">
      <div
        v-if="isOpen"
        @click="$emit('close')"
        class="fixed inset-0 z-40 bg-black/80 backdrop-blur-xs transition-opacity"
      ></div>
    </Transition>

    <!-- 侧边菜单抽屉主体：从左侧展开 (移动端占约 2/3 宽，Web 端固定 320px) -->
    <div
      class="fixed top-0 bottom-0 left-0 z-50 w-3/4 max-w-sm sm:w-80 bg-[#08080a] border-r border-[#1e1e24] flex flex-col transition-transform duration-300 ease-in-out select-none shadow-2xl"
      :class="isOpen ? 'translate-x-0' : '-translate-x-full'"
    >
      <!-- 顶栏：适配 iOS PWA 灵动岛及状态栏安全区 -->
      <div class="flex items-center justify-between px-4 pb-3.5 pwa-safe-top border-b border-[#18181d] shrink-0">
        <div class="flex items-center space-x-2">
          <span class="text-[#dc143c] text-xs leading-none">✦</span>
          <span class="text-xs font-semibold text-zinc-100 uppercase tracking-widest">菜单</span>
        </div>
        <button
          @click="$emit('close')"
          class="p-1.5 text-zinc-400 hover:text-zinc-100 hover:bg-[#16161b] rounded-xs cursor-pointer transition-colors"
          title="关闭菜单"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- 滚动主体区 -->
      <div class="flex-1 overflow-y-auto p-4 space-y-6 no-scrollbar text-xs">
        <!-- 1. 浏览模式切换 -->
        <div class="space-y-2">
          <div class="text-[11px] text-zinc-500 font-mono uppercase tracking-wider flex items-center justify-between">
            <span><span class="text-[#dc143c] mr-1">✧</span>视图</span>
            <span class="text-[10px] text-zinc-600">VIEW</span>
          </div>
          <div class="grid grid-cols-4 gap-1 bg-[#0c0c10] p-1 border border-[#1a1a20] rounded-xs">
            <button
              @click="$emit('change-tab', 'timeline')"
              class="flex items-center justify-center space-x-1 py-2 px-1 rounded-xs transition-all cursor-pointer text-[11px]"
              :class="activeTab === 'timeline'
                ? 'bg-[#180a0e] text-[#f43f5e] border border-[#dc143c]/50 font-medium'
                : 'text-zinc-400 hover:text-zinc-200 border border-transparent'"
            >
              <List class="w-3.5 h-3.5 shrink-0" />
              <span>列表</span>
            </button>
            <button
              @click="$emit('change-tab', 'book')"
              class="flex items-center justify-center space-x-1 py-2 px-1 rounded-xs transition-all cursor-pointer text-[11px]"
              :class="activeTab === 'book'
                ? 'bg-[#180a0e] text-[#f43f5e] border border-[#dc143c]/50 font-medium'
                : 'text-zinc-400 hover:text-zinc-200 border border-transparent'"
            >
              <BookOpen class="w-3.5 h-3.5 shrink-0" />
              <span>仿真</span>
            </button>
            <button
              @click="$emit('change-tab', 'cluster')"
              class="flex items-center justify-center space-x-1 py-2 px-1 rounded-xs transition-all cursor-pointer text-[11px]"
              :class="activeTab === 'cluster'
                ? 'bg-[#180a0e] text-[#f43f5e] border border-[#dc143c]/50 font-medium'
                : 'text-zinc-400 hover:text-zinc-200 border border-transparent'"
            >
              <Boxes class="w-3.5 h-3.5 shrink-0" />
              <span>星图</span>
            </button>
            <button
              @click="$emit('change-tab', 'analytics')"
              class="flex items-center justify-center space-x-1 py-2 px-1 rounded-xs transition-all cursor-pointer text-[11px]"
              :class="activeTab === 'analytics'
                ? 'bg-[#180a0e] text-[#f43f5e] border border-[#dc143c]/50 font-medium'
                : 'text-zinc-400 hover:text-zinc-200 border border-transparent'"
            >
              <BarChart3 class="w-3.5 h-3.5 shrink-0" />
              <span>洞察</span>
            </button>
          </div>
        </div>

        <!-- 2. 日历与时光穿梭 -->
        <div class="space-y-3">
          <div class="text-[11px] text-zinc-500 font-mono uppercase tracking-wider flex items-center justify-between">
            <span><span class="text-[#dc143c] mr-1">✧</span>日历</span>
            <span class="text-[10px] text-zinc-600">CALENDAR</span>
          </div>

          <!-- 月份切换栏 -->
          <div class="flex items-center justify-between bg-[#0c0c10] border border-[#1a1a20] p-2 rounded-xs text-xs">
            <button
              @click="prevMonth"
              class="p-1 text-zinc-400 hover:text-zinc-100 hover:bg-[#18181f] rounded-xs cursor-pointer"
              title="上一月"
            >
              <ChevronLeft class="w-4 h-4" />
            </button>
            <span class="font-mono font-medium text-zinc-200">
              {{ currentYear }}年 {{ String(currentMonth).padStart(2, '0') }}月
            </span>
            <button
              @click="nextMonth"
              class="p-1 text-zinc-400 hover:text-zinc-100 hover:bg-[#18181f] rounded-xs cursor-pointer"
              title="下一月"
            >
              <ChevronRight class="w-4 h-4" />
            </button>
          </div>

          <!-- 日历网格 (支持左右滑动手势) -->
          <div
            class="bg-[#0b0b0e] border border-[#1a1a20] p-2.5 rounded-xs touch-pan-y"
            @touchstart="onTouchStart"
            @touchend="onTouchEnd"
          >
            <div class="grid grid-cols-7 gap-1 text-center text-[10px] text-zinc-500 font-mono pb-2 border-b border-[#18181d] mb-1.5">
              <span>日</span>
              <span>一</span>
              <span>二</span>
              <span>三</span>
              <span>四</span>
              <span>五</span>
              <span>六</span>
            </div>

            <div class="grid grid-cols-7 gap-1 text-center">
              <div
                v-for="(day, idx) in calendarDays"
                :key="idx"
                @click="day.isCurrentMonth && day.hasDiary && handleDaySelect(day)"
                class="relative h-7 flex items-center justify-center text-xs font-mono rounded-xs transition-colors"
                :class="[
                  !day.isCurrentMonth ? 'text-neutral-700 pointer-events-none' : '',
                  day.isCurrentMonth && day.hasDiary
                    ? 'bg-[#180a0e] text-zinc-100 border border-[#dc143c]/50 hover:border-[#dc143c] cursor-pointer'
                    : 'text-zinc-500',
                  day.isToday ? 'font-bold underline decoration-[#dc143c]' : ''
                ]"
              >
                <span>{{ day.dayNum }}</span>
                <span
                  v-if="day.hasDiary"
                  class="absolute bottom-0 text-[7px] leading-none text-[#dc143c]"
                >✦</span>
              </div>
            </div>
          </div>

          <!-- 年份快速跳跃 -->
          <div class="flex items-center gap-1.5 flex-wrap pt-1">
            <button
              v-for="y in availableYears"
              :key="y"
              @click="jumpToYear(y)"
              class="px-2 py-0.5 bg-[#0e0e12] hover:bg-[#180a0e] text-zinc-400 hover:text-[#f43f5e] border border-[#1e1e24] rounded-xs text-[10px] font-mono transition-colors cursor-pointer"
              :class="currentYear === Number(y) ? 'border-[#dc143c] text-[#f43f5e]' : ''"
            >
              {{ y }}
            </button>
          </div>

          <!-- 极速穿梭按钮 -->
          <div class="grid grid-cols-2 gap-2 pt-1">
            <button
              @click="$emit('scroll-to-top'); $emit('close')"
              class="flex items-center justify-center space-x-1.5 py-1.5 bg-[#0e0e12] hover:bg-[#16161c] border border-[#1e1e24] text-zinc-300 rounded-xs text-[11px] cursor-pointer transition-colors"
            >
              <ArrowUp class="w-3 h-3 text-[#dc143c]" />
              <span>回到最新</span>
            </button>
            <button
              @click="$emit('scroll-to-oldest'); $emit('close')"
              class="flex items-center justify-center space-x-1.5 py-1.5 bg-[#0e0e12] hover:bg-[#16161c] border border-[#1e1e24] text-zinc-300 rounded-xs text-[11px] cursor-pointer transition-colors"
            >
              <ArrowDown class="w-3 h-3 text-zinc-400" />
              <span>最早</span>
            </button>
          </div>
        </div>

        <!-- 3. 管理与备份 -->
        <div class="space-y-2 pt-3 border-t border-[#18181d]">
          <div class="text-[11px] text-zinc-500 font-mono uppercase tracking-wider flex items-center justify-between">
            <span><span class="text-[#dc143c] mr-1">✧</span>管理</span>
            <span class="text-[10px] text-zinc-600">MANAGE</span>
          </div>

          <button
            @click="$emit('open-knowledge'); $emit('close')"
            class="w-full flex items-center justify-between p-2.5 bg-[#0c0c10] hover:bg-[#16161b] border border-[#1a1a20] hover:border-[#2a2a35] rounded-xs text-zinc-200 transition-colors cursor-pointer"
          >
            <div class="flex items-center space-x-2">
              <Sparkles class="w-4 h-4 text-[#dc143c]" />
              <span class="font-medium">标签与别名</span>
            </div>
            <ChevronRight class="w-3.5 h-3.5 text-zinc-500" />
          </button>

          <!-- 数据导入与导出 -->
          <div class="pt-2 space-y-1.5">
            <div class="grid grid-cols-2 gap-2">
              <button
                @click="$emit('export-json')"
                class="flex items-center justify-center space-x-1.5 p-2 bg-[#0c0c10] hover:bg-[#16161b] border border-[#1a1a20] hover:border-[#2a2a35] rounded-xs text-zinc-300 text-[11px] transition-colors cursor-pointer"
                title="导出 JSON 备份"
              >
                <Download class="w-3.5 h-3.5 text-[#dc143c]" />
                <span>导出 JSON</span>
              </button>

              <button
                @click="$emit('export-md')"
                class="flex items-center justify-center space-x-1.5 p-2 bg-[#0c0c10] hover:bg-[#16161b] border border-[#1a1a20] hover:border-[#2a2a35] rounded-xs text-zinc-300 text-[11px] transition-colors cursor-pointer"
                title="导出 Markdown"
              >
                <FileText class="w-3.5 h-3.5 text-zinc-400" />
                <span>导出 MD</span>
              </button>
            </div>

            <button
              @click="triggerFileInput"
              class="w-full flex items-center justify-center space-x-1.5 p-2 bg-[#0c0c10] hover:bg-[#180a0e] border border-dashed border-[#24242e] hover:border-[#dc143c]/60 rounded-xs text-zinc-300 hover:text-[#f43f5e] text-[11px] transition-colors cursor-pointer"
              title="导入 JSON 备份"
            >
              <Upload class="w-3.5 h-3.5" />
              <span>导入 JSON</span>
            </button>
            <input
              ref="fileInputRef"
              type="file"
              accept=".json,application/json"
              class="hidden"
              @change="onFileSelected"
            />
          </div>
        </div>
      </div>

      <!-- 底栏安全区与 ASCII 星图签名 -->
      <div class="px-3 pt-3 pb-[max(env(safe-area-inset-bottom),0.75rem)] border-t border-[#18181d] text-center font-mono select-none space-y-1">
        <pre class="text-[10px] leading-tight text-zinc-600 tracking-widest">✧ ˚｡✧  <span class="text-[#dc143c]">✦</span>  ✧｡˚ ✧</pre>
        <div class="text-[10px] text-zinc-600">dearDiary</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import {
  X, List, BookOpen, Boxes, BarChart3, ChevronLeft, ChevronRight,
  ArrowUp, ArrowDown, Sparkles, Download, Upload, FileText
} from '@lucide/vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  activeTab: {
    type: String,
    default: 'timeline'
  },
  diaries: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits([
  'close', 'change-tab', 'scroll-to-top', 'scroll-to-oldest',
  'jump-to-date', 'open-knowledge', 'export-json', 'export-md', 'import-json'
])

const fileInputRef = ref(null)

const triggerFileInput = () => {
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
    fileInputRef.value.click()
  }
}

const onFileSelected = (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  emit('import-json', file)
}

const currentYear = ref(new Date().getFullYear())
const currentMonth = ref(new Date().getMonth() + 1)

// 触摸左右滑动切换月份
let touchStartX = 0
const onTouchStart = (e) => {
  touchStartX = e.changedTouches[0].clientX
}
const onTouchEnd = (e) => {
  const diff = e.changedTouches[0].clientX - touchStartX
  if (Math.abs(diff) > 45) {
    if (diff > 0) prevMonth()
    else nextMonth()
  }
}

const availableYears = computed(() => {
  const set = new Set()
  props.diaries.forEach(d => {
    if (!d.created_at) return
    const dt = new Date(d.created_at)
    if (!isNaN(dt.getTime())) {
      set.add(dt.getFullYear())
    }
  })
  return Array.from(set).sort((a, b) => b - a)
})

const diaryDatesSet = computed(() => {
  const set = new Set()
  props.diaries.forEach(d => {
    if (!d.created_at) return
    const dt = new Date(d.created_at)
    if (!isNaN(dt.getTime())) {
      const pad = (n) => String(n).padStart(2, '0')
      set.add(`${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}`)
    }
  })
  return set
})

const calendarDays = computed(() => {
  const y = currentYear.value
  const m = currentMonth.value
  const firstDay = new Date(y, m - 1, 1).getDay()
  const lastDate = new Date(y, m, 0).getDate()

  const today = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  const todayStr = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`

  const days = []

  const prevMonthLastDate = new Date(y, m - 1, 0).getDate()
  for (let i = firstDay - 1; i >= 0; i--) {
    days.push({
      dayNum: prevMonthLastDate - i,
      isCurrentMonth: false,
      hasDiary: false,
      isToday: false,
      dateStr: ''
    })
  }

  for (let d = 1; d <= lastDate; d++) {
    const dateStr = `${y}-${pad(m)}-${pad(d)}`
    days.push({
      dayNum: d,
      isCurrentMonth: true,
      hasDiary: diaryDatesSet.value.has(dateStr),
      isToday: dateStr === todayStr,
      dateStr
    })
  }

  const remaining = 7 - (days.length % 7)
  if (remaining < 7) {
    for (let i = 1; i <= remaining; i++) {
      days.push({
        dayNum: i,
        isCurrentMonth: false,
        hasDiary: false,
        isToday: false,
        dateStr: ''
      })
    }
  }

  return days
})

const prevMonth = () => {
  if (currentMonth.value === 1) {
    currentYear.value--
    currentMonth.value = 12
  } else {
    currentMonth.value--
  }
}

const nextMonth = () => {
  if (currentMonth.value === 12) {
    currentYear.value++
    currentMonth.value = 1
  } else {
    currentMonth.value++
  }
}

const jumpToYear = (y) => {
  currentYear.value = Number(y)
}

const handleDaySelect = (day) => {
  emit('jump-to-date', day.dateStr)
  emit('close')
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
