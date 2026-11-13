<template>
  <div class="w-full py-2 px-1 sm:px-2 select-none">
    <!-- 极简顶部元数据行 -->
    <div class="flex items-center justify-between mb-3 text-[11px] font-mono">
      <div class="flex items-center space-x-2 text-zinc-400">
        <span class="text-[#dc143c] text-xs leading-none">✦</span>
        <span class="tracking-wider">近七日足迹</span>
        <span class="text-zinc-600 hidden sm:inline">· {{ weekRangeText }}</span>
      </div>

      <div class="text-zinc-500">
        <span>已录 </span>
        <span class="text-[#f43f5e]">{{ writtenDaysCount }}</span>
        <span class="text-zinc-600"> / 7 ✧</span>
      </div>
    </div>

    <!-- 优雅水平时间刻度线与 7 个日期节点 -->
    <div class="relative flex items-center justify-between pt-1 pb-1">
      <!-- 贯穿背后的极细基准横线 -->
      <div class="absolute left-4 right-4 top-1/2 -translate-y-1/2 h-px bg-[#1a1a22] pointer-events-none"></div>

      <button
        v-for="day in pastSevenDays"
        :key="day.dateStr"
        type="button"
        @click="handleDayClick(day)"
        class="group relative z-10 flex flex-col items-center space-y-2 px-2 py-1 transition-all cursor-pointer focus:outline-none"
        :title="day.hasDiary ? `${day.dateStr} · 共 ${day.count} 篇，点击定位` : (day.isToday ? '今天还未记录，点击立即撰写' : `${day.dateStr} · 无记录`)"
      >
        <!-- 周几 -->
        <span
          class="text-[10px] font-mono transition-colors"
          :class="day.isToday ? 'text-[#f43f5e]' : 'text-zinc-600 group-hover:text-zinc-400'"
        >
          {{ day.isToday ? '今日' : day.dayOfWeek }}
        </span>

        <!-- 时间线星点节点 -->
        <div class="relative flex items-center justify-center w-5 h-5 bg-[#050505]">
          <!-- 有日记：绯红实心星 ✦ -->
          <span
            v-if="day.hasDiary"
            class="text-[#dc143c] text-sm leading-none group-hover:scale-125 transition-transform"
          >✦</span>
          <!-- 今日未写：绯红空心星 ✧ -->
          <span
            v-else-if="day.isToday"
            class="text-[#dc143c] text-sm leading-none animate-pulse group-hover:scale-125 transition-transform"
          >✧</span>
          <!-- 过往空白：低调暗星 ✧ -->
          <span
            v-else
            class="text-zinc-700 text-xs leading-none group-hover:text-zinc-400 transition-colors"
          >✧</span>
        </div>

        <!-- 日期数字 -->
        <span
          class="text-[11px] font-mono transition-colors"
          :class="[
            day.hasDiary ? 'text-zinc-200 font-medium' : 'text-zinc-600 group-hover:text-zinc-400',
            day.isToday ? 'underline decoration-[#dc143c] underline-offset-4 text-zinc-100' : ''
          ]"
        >
          {{ String(day.dayNum).padStart(2, '0') }}
        </span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  diaries: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['jump-to-date', 'create-for-today'])

const dayNames = ['日', '一', '二', '三', '四', '五', '六']

const pastSevenDays = computed(() => {
  const result = []
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const diaryDateCounts = {}
  props.diaries.forEach(d => {
    if (!d.created_at) return
    const dt = new Date(d.created_at)
    if (isNaN(dt.getTime())) return
    const pad = (n) => String(n).padStart(2, '0')
    const key = `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}`
    diaryDateCounts[key] = (diaryDateCounts[key] || 0) + 1
  })

  for (let i = 6; i >= 0; i--) {
    const cur = new Date(today)
    cur.setDate(today.getDate() - i)

    const pad = (n) => String(n).padStart(2, '0')
    const dateStr = `${cur.getFullYear()}-${pad(cur.getMonth() + 1)}-${pad(cur.getDate())}`
    const isToday = i === 0
    const count = diaryDateCounts[dateStr] || 0

    result.push({
      dateStr,
      dayNum: cur.getDate(),
      dayOfWeek: dayNames[cur.getDay()],
      isToday,
      hasDiary: count > 0,
      count
    })
  }

  return result
})

const writtenDaysCount = computed(() => {
  return pastSevenDays.value.filter(d => d.hasDiary).length
})

const weekRangeText = computed(() => {
  if (pastSevenDays.value.length === 0) return ''
  const first = pastSevenDays.value[0]
  const last = pastSevenDays.value[pastSevenDays.value.length - 1]
  const fD = first.dateStr.slice(5).replace('-', '.')
  const lD = last.dateStr.slice(5).replace('-', '.')
  return `${fD} — ${lD}`
})

const handleDayClick = (day) => {
  if (day.hasDiary) {
    emit('jump-to-date', day.dateStr)
  } else if (day.isToday) {
    emit('create-for-today')
  }
}
</script>
