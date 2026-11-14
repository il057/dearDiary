<template>
  <div class="space-y-5 relative w-full">
    <!-- 极简年份索引栏 (水平紧凑滚动，不吸顶，避免移动端重叠) -->
    <div
      v-if="!loading && items.length > 0"
      class="w-full bg-[#09090c] border border-[#1a1a20] rounded-xs p-2 sm:p-2.5 flex items-center justify-between gap-2 sm:gap-3 text-xs select-none"
    >
      <div class="flex items-center space-x-2 shrink-0">
        <span class="text-[#dc143c] text-xs leading-none">✦</span>
        <span class="text-zinc-400 font-medium font-mono text-[11px] hidden sm:inline">年份</span>
      </div>

      <!-- 年份胶囊 -->
      <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-0.5">
        <button
          v-for="yObj in yearGroups"
          :key="yObj.year"
          @click="scrollToYear(yObj.year)"
          class="shrink-0 px-2.5 py-0.5 rounded-xs text-xs font-mono transition-colors border cursor-pointer"
          :class="activeYear === yObj.year
            ? 'bg-[#180a0e] text-[#f43f5e] border-[#dc143c]/60'
            : 'bg-[#050505] text-zinc-400 hover:text-zinc-200 border-[#1c1c22]'"
        >
          <span>{{ yObj.year }}</span>
          <span class="text-[10px] ml-1 text-zinc-600">({{ yObj.count }})</span>
        </button>
      </div>

      <!-- 快捷回顶与穿梭至最初 -->
      <div class="flex items-center space-x-1.5 shrink-0">
        <button
          @click="scrollToOldest"
          class="px-2 py-0.5 bg-[#050505] hover:bg-[#141418] text-zinc-400 hover:text-zinc-200 border border-[#1c1c22] rounded-xs text-[11px] cursor-pointer"
          title="直达最早记录"
        >
          最初
        </button>
        <button
          @click="scrollToTop"
          class="px-2 py-0.5 bg-[#050505] hover:bg-[#141418] text-[#f43f5e] border border-[#1c1c22] rounded-xs text-[11px] cursor-pointer"
          title="回到最新"
        >
          最新
        </button>
      </div>
    </div>

    <!-- 加载中动画 -->
    <div v-if="loading" class="py-24 text-center text-zinc-500 text-xs font-mono flex flex-col items-center justify-center space-y-2.5 select-none">
      <div class="flex items-center space-x-2 text-xs">
        <span class="text-zinc-600">✧</span>
        <span class="text-[#dc143c] animate-pulse">✦</span>
        <span class="text-zinc-600">✧</span>
      </div>
      <span>加载中...</span>
    </div>

    <!-- 空数据提示 (ASCII 星图艺术) -->
    <div v-else-if="items.length === 0" class="py-20 text-center select-none flex flex-col items-center justify-center space-y-4">
      <pre class="text-[11px] leading-relaxed font-mono text-zinc-700">    .   *   ˚   .
  *   <span class="text-[#dc143c]">✦</span>   .   ✧
    ˚   ✧   *   .
  ✧   .   <span class="text-[#dc143c]">✦</span>   *</pre>
      <p class="text-zinc-500 text-xs font-mono">✧ 暂无日记 ✧</p>
    </div>

    <!-- 垂直时间线轴 + 按年月分组的有序卡片流 -->
    <div v-else class="relative pl-4 sm:pl-7 ml-1 sm:ml-2 border-l border-[#1c1c24] space-y-8 pb-8">
      <div
        v-for="group in timelineGroups"
        :key="group.key"
        :id="'month-anchor-' + group.key"
        class="relative scroll-mt-28"
      >
        <!-- 年/月切换提醒节点：直接锚定在左侧时间轴线上 -->
        <div class="flex items-center space-x-3 mb-3.5 select-none">
          <!-- 时间线上的星点标志：跨年为高亮 Crimson 实心星 ✦，跨月为空心星 ✧ -->
          <span
            v-if="group.isNewYear"
            class="absolute -left-[22px] sm:-left-[34px] text-[#dc143c] text-xs leading-none bg-[#050505] py-0.5"
          >✦</span>
          <span
            v-else
            class="absolute -left-[22px] sm:-left-[34px] text-[#dc143c]/80 text-xs leading-none bg-[#050505] py-0.5"
          >✧</span>

          <!-- 年份 & 月份提醒标签 -->
          <div class="flex items-baseline space-x-2">
            <span
              v-if="group.isNewYear"
              class="text-base sm:text-lg font-bold font-mono text-zinc-100 tracking-tight"
            >
              {{ group.year }}<span class="text-[#dc143c] ml-0.5">.</span>
            </span>
            <span
              class="text-xs sm:text-sm font-mono font-medium"
              :class="group.isNewYear ? 'text-[#f43f5e]' : 'text-zinc-300'"
            >
              {{ group.month }}月
            </span>
            <span class="text-[10px] text-zinc-600 font-mono">
              · {{ group.items.length }} 篇
            </span>
          </div>

          <!-- 柔和的时间跨度分割延伸线 -->
          <div class="flex-1 h-px bg-gradient-to-r from-[#1e1e26] via-[#14141a] to-transparent"></div>
        </div>

        <!-- 该月份内的日记卡片：严格按时间顺序铺开（Grid 多列铺满 Web 宽屏，移动端单列） -->
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          <div
            v-for="item in group.items"
            :key="item.id || item.diary_id"
            :id="'diary-card-' + (item.id || item.diary_id)"
            @click="$emit('select-diary', item)"
            class="group flex flex-col justify-between bg-[#09090c] hover:bg-[#0d0d12] border border-[#19191f] hover:border-[#dc143c]/50 rounded-xs p-3.5 transition-all duration-200 cursor-pointer scroll-mt-28"
            :class="[
              highlightedId === (item.id || item.diary_id)
                ? 'border-[#dc143c] ring-1 ring-[#dc143c]/60 bg-[#14080a]'
                : ''
            ]"
          >
            <div>
              <!-- 卡片头部：星标情绪色、具体日期时间、心境 -->
              <div class="flex items-center justify-between text-xs text-zinc-500 mb-2 pb-1.5 border-b border-[#141418]">
                <div class="flex items-center space-x-2">
                  <span
                    class="text-xs leading-none shrink-0"
                    :style="{
                      color: item.mood_color || '#dc143c'
                    }"
                  >✦</span>
                  <span class="font-mono text-zinc-400 text-[11px]">
                    {{ formatCardTime(item.created_at) }}
                  </span>
                </div>

                <div class="flex items-center space-x-1">
                  <span
                    v-if="processingIds.has(item.id || item.diary_id)"
                    class="w-10 h-4 bg-[#180c10] border border-[#dc143c]/25 rounded-xs animate-pulse"
                  ></span>
                  <span v-else-if="item.mood" class="px-1.5 py-0.5 bg-[#16090c] text-[#f43f5e] border border-[#dc143c]/25 rounded-xs text-[10px]">
                    {{ item.mood }}
                  </span>
                </div>
              </div>

              <!-- 语义检索命中指示 (如有) -->
              <div v-if="item.matched_reason" class="mb-2 text-[10px] text-[#f43f5e] bg-[#16090c] px-1.5 py-0.5 rounded-xs border border-[#dc143c]/20 inline-flex items-center space-x-1">
                <span class="text-[#dc143c] text-[10px] leading-none">✦</span>
                <span class="truncate">{{ item.matched_reason }}</span>
              </div>

              <!-- 引用过往日记提示条 (如有) -->
              <div
                v-if="item.quoted_diaries && item.quoted_diaries.length > 0"
                class="mb-2 px-2 py-1 bg-[#0b0b10] border border-[#1a1a22] border-l-2 border-l-[#dc143c]/80 rounded-xs text-[11px] text-zinc-400 flex items-center space-x-1.5"
              >
                <Quote class="w-3 h-3 text-[#dc143c] shrink-0" />
                <span class="font-mono text-zinc-500 shrink-0">{{ formatCardTime(item.quoted_diaries[0].created_at) }}</span>
                <span class="truncate text-zinc-400">{{ item.quoted_diaries[0].summary || item.quoted_diaries[0].content }}</span>
                <span v-if="item.quoted_diaries.length > 1" class="text-[10px] text-zinc-600 font-mono shrink-0">+{{ item.quoted_diaries.length - 1 }}</span>
              </div>

              <!-- 正文缩略展示：2-3行截断（支持搜索关键词/实体高亮） -->
              <p class="text-zinc-300 text-xs sm:text-[13px] leading-relaxed line-clamp-3 font-normal select-none">
                <template v-if="highlightTerms.length > 0">
                  <template v-for="(seg, sIdx) in splitHighlightSegments(item.content, highlightTerms)" :key="sIdx">
                    <mark v-if="seg.match" class="bg-[#dc143c]/25 text-[#fda4af] px-0.5 rounded-xs">{{ seg.text }}</mark>
                    <template v-else>{{ seg.text }}</template>
                  </template>
                </template>
                <template v-else>{{ item.content }}</template>
              </p>

              <!-- 命中回响时的紧凑预览条 -->
              <div
                v-if="getMatchedEchoPreview(item)"
                class="mt-2 px-2 py-1.5 bg-[#0e0b10] border border-[#241b22] border-l-2 border-l-[#dc143c]/65 rounded-xs text-[11px] text-zinc-300 flex items-start space-x-1.5"
              >
                <StickyNote class="w-3 h-3 text-[#dc143c] shrink-0 mt-0.5" />
                <p class="line-clamp-2 leading-relaxed break-words">
                  <template v-if="highlightTerms.length > 0">
                    <template v-for="(seg, sIdx) in splitHighlightSegments(getMatchedEchoPreview(item).content, highlightTerms)" :key="sIdx">
                      <mark v-if="seg.match" class="bg-[#dc143c]/30 text-[#fda4af] px-0.5 rounded-xs">{{ seg.text }}</mark>
                      <template v-else>{{ seg.text }}</template>
                    </template>
                  </template>
                  <template v-else>{{ getMatchedEchoPreview(item).content }}</template>
                </p>
              </div>
            </div>

            <!-- 底部语义实体标签栏 -->
            <div class="mt-3 pt-2 border-t border-[#141418] flex items-center justify-between text-[11px] text-zinc-500">
              <div v-if="processingIds.has(item.id || item.diary_id)" class="flex items-center gap-1.5">
                <span class="w-10 h-4 bg-[#0d0d12] border border-[#1d1d26] rounded-xs animate-pulse"></span>
                <span class="w-14 h-4 bg-[#0d0d12] border border-[#1d1d26] rounded-xs animate-pulse"></span>
                <span class="w-12 h-4 bg-[#0d0d12] border border-[#1d1d26] rounded-xs animate-pulse"></span>
              </div>
              <div v-else class="flex flex-wrap items-center gap-1 overflow-hidden max-h-5">
                <span
                  v-for="ent in (item.entities || item.related_entities || []).slice(0, 3)"
                  :key="ent"
                  class="px-1.5 py-0.2 rounded-xs border text-[10px]"
                  :class="isEntityHighlighted(ent, highlightTerms)
                    ? 'bg-[#180a0e] text-[#fda4af] border-[#dc143c]/60 font-medium'
                    : 'bg-[#060608] text-zinc-400 border-[#1a1a20]'"
                >
                  #{{ ent }}
                </span>
                <span
                  v-if="(item.entities || item.related_entities || []).length > 3"
                  class="text-[9px] text-zinc-600 font-mono"
                >
                  +{{ (item.entities || item.related_entities || []).length - 3 }}
                </span>
              </div>

              <div class="flex items-center space-x-2 shrink-0 ml-2">
                <span
                  v-if="item.echoes && item.echoes.length > 0"
                  class="inline-flex items-center space-x-0.5 text-[10px] text-zinc-400 group-hover:text-[#fda4af] font-mono transition-colors"
                  :title="`${item.echoes.length} 条回响批注`"
                >
                  <StickyNote class="w-2.5 h-2.5 text-[#dc143c]/80" />
                  <span>{{ item.echoes.length }}</span>
                </span>
                <span
                  v-if="item.quoted_by && item.quoted_by.length > 0"
                  class="inline-flex items-center space-x-0.5 text-[10px] text-[#f43f5e]/80 font-mono"
                  :title="`被 ${item.quoted_by.length} 篇后续日记引用`"
                >
                  <Quote class="w-2.5 h-2.5" />
                  <span>{{ item.quoted_by.length }}</span>
                </span>
                <span class="text-[10px] text-zinc-600 group-hover:text-[#f43f5e] transition-colors font-mono">
                  全文 →
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右下角快速置顶悬浮按钮 (仅 Web 端显示，移动端点击顶部灵动岛/状态栏即可回顶) -->
    <div class="hidden sm:block fixed bottom-[max(env(safe-area-inset-bottom),1.5rem)] right-5 sm:right-8 z-30 pointer-events-auto">
      <button
        @click="scrollToTop"
        class="p-2.5 bg-[#09090c]/90 hover:bg-[#180a0e] text-zinc-400 hover:text-[#f43f5e] rounded-xs border border-[#1e1e26] hover:border-[#dc143c]/50 shadow-xl backdrop-blur-md transition-all cursor-pointer"
        title="返回顶部"
      >
        <ArrowUp class="w-4 h-4" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ArrowUp, Quote, StickyNote } from '@lucide/vue'
import { splitHighlightSegments, isEntityHighlighted } from '../utils/highlight'

const props = defineProps({
  items: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  processingIds: {
    type: Set,
    default: () => new Set()
  },
  highlightTerms: {
    type: Array,
    default: () => []
  }
})

defineEmits(['select-diary'])

const highlightedId = ref(null)
const activeYear = ref('')

// 年份统计（用于顶部索引）
const yearGroups = computed(() => {
  const map = {}
  props.items.forEach(d => {
    if (!d.created_at) return
    const dt = new Date(d.created_at)
    if (isNaN(dt.getTime())) return
    const y = String(dt.getFullYear())
    map[y] = (map[y] || 0) + 1
  })

  return Object.keys(map)
    .sort((a, b) => Number(b) - Number(a))
    .map(y => ({
      year: y,
      count: map[y]
    }))
})

// 按连续的年月顺序分段，同时精准标记跨年切换
const timelineGroups = computed(() => {
  const groups = []
  let lastKey = null
  let lastYear = null

  props.items.forEach(item => {
    let y = '未知'
    let m = '00'
    if (item.created_at) {
      const dt = new Date(item.created_at)
      if (!isNaN(dt.getTime())) {
        y = String(dt.getFullYear())
        m = String(dt.getMonth() + 1).padStart(2, '0')
      }
    }
    const key = `${y}-${m}`

    if (key !== lastKey) {
      const isNewYear = y !== lastYear
      groups.push({
        key,
        year: y,
        month: m,
        isNewYear,
        items: [item]
      })
      lastKey = key
      lastYear = y
    } else {
      groups[groups.length - 1].items.push(item)
    }
  })

  return groups
})

const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const scrollToOldest = () => {
  if (props.items.length === 0) return
  const oldest = props.items[props.items.length - 1]
  scrollToItem(oldest.id || oldest.diary_id)
}

const scrollToYear = (y) => {
  activeYear.value = y
  const group = timelineGroups.value.find(g => g.year === y)
  if (group) {
    const el = document.getElementById('month-anchor-' + group.key)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }
}

const scrollToItem = (id) => {
  const el = document.getElementById('diary-card-' + id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    highlightedId.value = id
    setTimeout(() => {
      highlightedId.value = null
    }, 2500)
  }
}

defineExpose({
  scrollToItem,
  scrollToOldest,
  scrollToDate: (dateStr) => {
    if (!dateStr || props.items.length === 0) return
    const targetTime = new Date(dateStr).getTime()
    let closestItem = props.items[0]
    let minDiff = Infinity

    props.items.forEach(item => {
      if (!item.created_at) return
      const t = new Date(item.created_at).getTime()
      const diff = Math.abs(t - targetTime)
      if (diff < minDiff) {
        minDiff = diff
        closestItem = item
      }
    })

    if (closestItem) {
      scrollToItem(closestItem.id || closestItem.diary_id)
    }
  }
})

const formatCardTime = (timeStr) => {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  if (isNaN(d.getTime())) return timeStr
  const isDefaultNoon = d.getHours() === 12 && d.getMinutes() === 0 && d.getSeconds() === 0
  
  if (isDefaultNoon) {
    return `${d.getMonth() + 1}月${d.getDate()}日`
  }
  return `${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const getMatchedEchoPreview = (item) => {
  const echoes = item?.echoes
  if (!echoes || echoes.length === 0) return null
  const terms = (props.highlightTerms || []).map(t => (t || '').trim().toLowerCase()).filter(Boolean)
  if (terms.length > 0) {
    const matched = echoes.find(e => terms.some(t => (e.content || '').toLowerCase().includes(t)))
    if (matched) return matched
  }
  if (item.matched_reason && item.matched_reason.includes('回响命中')) {
    return echoes[0]
  }
  return null
}
</script>
