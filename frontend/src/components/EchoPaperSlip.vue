<template>
  <div
    v-if="echoes && echoes.length > 0"
    @click.stop="$emit('open-detail')"
    class="absolute bottom-1.5 left-1 right-1 sm:left-2 sm:right-2 z-20 cursor-pointer group select-text"
    title="点击查看或补充回响"
  >
    <div
      class="relative bg-[#151218]/95 border border-[#2d2229] group-hover:border-[#dc143c]/50 rounded-xs px-3.5 py-2.5 shadow-[0_8px_22px_rgba(0,0,0,0.78)] -rotate-[0.55deg] group-hover:rotate-0 transition-all duration-200"
    >
      <!-- 顶部半透明绯红和纸胶带 -->
      <div
        class="pointer-events-none absolute -top-2 left-1/2 -translate-x-1/2 w-12 h-3.5 bg-[#dc143c]/25 border border-[#f43f5e]/20 backdrop-blur-[1px] -rotate-1 shadow-xs"
      ></div>

      <!-- 纸片正文列表：正文 -> 右下角时间戳 -->
      <div class="max-h-28 sm:max-h-36 overflow-y-auto space-y-2 pr-1 diary-paper-font">
        <div
          v-for="(echo, idx) in echoes"
          :key="echo.id"
          :class="idx > 0 ? 'pt-2 border-t border-dashed border-[#2b2128]' : ''"
        >
          <p class="text-[13px] leading-[22px] text-zinc-200 whitespace-pre-wrap break-words">
            <template v-if="highlightTerms.length > 0">
              <template v-for="(seg, sIdx) in splitHighlightSegments(echo.content, highlightTerms)" :key="sIdx">
                <mark v-if="seg.match" class="px-0.5 rounded-xs bg-[#dc143c]/30 text-[#fda4af]">{{ seg.text }}</mark>
                <template v-else>{{ seg.text }}</template>
              </template>
            </template>
            <template v-else>{{ echo.content }}</template>
          </p>
          <div class="text-right text-[10px] font-mono text-zinc-500 mt-1 select-none">
            — {{ formatEchoTime(echo.created_at) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { splitHighlightSegments } from '../utils/highlight'

defineProps({
  echoes: {
    type: Array,
    default: () => []
  },
  highlightTerms: {
    type: Array,
    default: () => []
  }
})

defineEmits(['open-detail'])

const formatEchoTime = (timeStr) => {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  if (isNaN(d.getTime())) return timeStr
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.diary-paper-font,
.diary-paper-font * {
  font-family: 'PoZhenTypewriter', 'UnifontJP', monospace !important;
}
</style>
