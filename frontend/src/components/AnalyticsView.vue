<template>
  <div class="w-full space-y-5 pb-10 select-none">
    <!-- 顶部标题与时间范围切换 -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#09090c] border border-[#1a1a22] rounded-xs p-3.5 sm:p-4">
      <div class="flex items-center space-x-2.5">
        <span class="text-[#dc143c] text-sm leading-none">✦</span>
        <div>
          <h2 class="text-sm font-semibold text-zinc-100 tracking-wider font-mono uppercase">数据洞察 · ANALYTICS</h2>
          <p class="text-[11px] text-zinc-500 mt-0.5">基于写作节律、情绪色彩、实体图谱与记忆引用的多维复盘</p>
        </div>
      </div>

      <div class="w-full sm:w-auto grid grid-cols-4 sm:flex items-center gap-1 bg-[#050505] p-1 border border-[#1a1a22] rounded-xs">
        <button
          v-for="opt in rangeOptions"
          :key="opt.value"
          @click="changeRange(opt.value)"
          class="px-2.5 py-1.5 sm:py-1 text-[11px] font-mono rounded-xs transition-colors cursor-pointer text-center"
          :class="selectedRange === opt.value
            ? 'bg-[#180a0e] text-[#f43f5e] border border-[#dc143c]/50 font-medium'
            : 'text-zinc-400 hover:text-zinc-200 border border-transparent'"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>

    <!-- 加载中状态 -->
    <div v-if="loading" class="py-20 flex flex-col items-center justify-center space-y-3 text-zinc-500 font-mono text-xs">
      <span class="text-[#dc143c] text-lg animate-pulse">✦</span>
      <span>正在聚合记忆维度...</span>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="errorMsg" class="p-6 bg-[#0d0a0b] border border-[#dc143c]/40 rounded-xs text-center space-y-2">
      <p class="text-xs text-[#f43f5e] font-mono">{{ errorMsg }}</p>
      <button
        @click="fetchAnalytics"
        class="px-3 py-1.5 text-xs font-mono bg-[#180a0e] text-zinc-200 border border-[#dc143c]/50 rounded-xs hover:border-[#dc143c] cursor-pointer"
      >
        重试
      </button>
    </div>

    <!-- 空数据状态 -->
    <div v-else-if="!data || data.overview.total_diaries === 0" class="py-16 bg-[#09090c] border border-[#1a1a22] rounded-xs text-center space-y-2">
      <span class="text-zinc-600 text-lg">✧</span>
      <p class="text-xs text-zinc-400 font-mono">当前时间范围内暂无日记记录</p>
    </div>

    <!-- 主体分析看板 -->
    <template v-else>
      <!-- 1. 核心指标 KPI -->
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <div class="bg-[#09090c] border border-[#1a1a22] rounded-xs p-3.5 space-y-1">
          <div class="text-[10px] font-mono text-zinc-500 uppercase flex items-center justify-between">
            <span>总篇数</span>
            <span class="text-[#dc143c]">✦</span>
          </div>
          <div class="text-xl font-mono font-semibold text-zinc-100">{{ data.overview.total_diaries }}</div>
          <div class="text-[11px] text-zinc-500 font-mono">活跃 {{ data.overview.active_days }} 天</div>
        </div>

        <div class="bg-[#09090c] border border-[#1a1a22] rounded-xs p-3.5 space-y-1">
          <div class="text-[10px] font-mono text-zinc-500 uppercase">总字数</div>
          <div class="text-xl font-mono font-semibold text-zinc-100">{{ formatNumber(data.overview.total_words) }}</div>
          <div class="text-[11px] text-zinc-500 font-mono">平均 {{ data.overview.avg_words }} 字/篇</div>
        </div>

        <div class="bg-[#09090c] border border-[#1a1a22] rounded-xs p-3.5 space-y-1">
          <div class="text-[10px] font-mono text-zinc-500 uppercase">当前连击</div>
          <div class="text-xl font-mono font-semibold text-[#f43f5e]">
            {{ data.overview.current_streak }} <span class="text-xs font-normal text-zinc-400">天</span>
          </div>
          <div class="text-[11px] text-zinc-500 font-mono">区间最长 {{ data.overview.longest_streak }} 天</div>
        </div>

        <div class="bg-[#09090c] border border-[#1a1a22] rounded-xs p-3.5 space-y-1">
          <div class="text-[10px] font-mono text-zinc-500 uppercase">最长单篇</div>
          <div class="text-xl font-mono font-semibold text-zinc-100">{{ formatNumber(data.overview.max_words) }}</div>
          <div class="text-[11px] text-zinc-500 font-mono">字符深度峰值</div>
        </div>

        <div class="bg-[#09090c] border border-[#1a1a22] rounded-xs p-3.5 space-y-1 col-span-2 sm:col-span-1">
          <div class="text-[10px] font-mono text-zinc-500 uppercase">自我回溯率</div>
          <div class="text-xl font-mono font-semibold text-zinc-100">{{ data.overview.quote_rate }}%</div>
          <div class="text-[11px] text-zinc-500 font-mono">共引用 {{ data.overview.total_quotes }} 次</div>
        </div>
      </div>

      <!-- 2. 年度/区间记录热力图 -->
      <div class="bg-[#09090c] border border-[#1a1a22] rounded-xs p-4 space-y-3">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div class="flex items-center space-x-2 text-xs font-mono text-zinc-300">
            <span class="text-[#dc143c]">✧</span>
            <span>记录热力图</span>
            <span class="text-[11px] text-zinc-500 hidden sm:inline">· 近 {{ heatmapWeeks.length }} 周足迹</span>
          </div>
          <div class="text-[11px] font-mono text-zinc-400 min-h-[16px]">
            <span v-if="hoveredHeatDay">
              {{ hoveredHeatDay.date }} · {{ hoveredHeatDay.count }} 篇 · {{ hoveredHeatDay.words }} 字
            </span>
            <span v-else class="text-zinc-600">悬停方格查看当日详情</span>
          </div>
        </div>

        <div class="overflow-x-auto no-scrollbar pb-1">
          <div class="w-full flex gap-[3px] sm:gap-1">
            <div
              v-for="(week, wIdx) in heatmapWeeks"
              :key="wIdx"
              class="flex-1 min-w-[10px] flex flex-col gap-[3px] sm:gap-1"
            >
              <div
                v-for="(cell, dIdx) in week"
                :key="dIdx"
                @mouseenter="hoveredHeatDay = cell"
                @mouseleave="hoveredHeatDay = null"
                class="w-full aspect-square max-h-5 rounded-[2px] transition-transform hover:scale-110"
                :style="{ backgroundColor: cell.future ? 'transparent' : getHeatColor(cell.words) }"
                :class="cell.future ? 'pointer-events-none' : 'border border-white/5 cursor-default'"
              ></div>
            </div>
          </div>
        </div>

        <div class="flex items-center justify-end space-x-1.5 text-[10px] font-mono text-zinc-500">
          <span>少</span>
          <span class="w-2.5 h-2.5 rounded-[2px] bg-[#121217] border border-white/5"></span>
          <span class="w-2.5 h-2.5 rounded-[2px] bg-[#4a0e1a]"></span>
          <span class="w-2.5 h-2.5 rounded-[2px] bg-[#88132b]"></span>
          <span class="w-2.5 h-2.5 rounded-[2px] bg-[#be123c]"></span>
          <span class="w-2.5 h-2.5 rounded-[2px] bg-[#f43f5e]"></span>
          <span>多</span>
        </div>
      </div>

      <!-- 3. 情绪光谱与分布 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- 情绪色彩时间轴 -->
        <div class="bg-[#09090c] border border-[#1a1a22] rounded-xs p-4 space-y-3 flex flex-col justify-between">
          <div class="space-y-3">
            <div class="flex items-center justify-between text-xs font-mono text-zinc-300">
              <span><span class="text-[#dc143c] mr-1.5">✧</span>情绪色彩光谱</span>
              <span class="text-[10px] text-zinc-500">点击色块直达日记</span>
            </div>

            <div class="h-10 w-full flex rounded-xs overflow-hidden border border-[#1e1e26] bg-[#050505]">
              <button
                v-for="item in data.mood_timeline"
                :key="item.id"
                type="button"
                @click="$emit('open-diary', item.id)"
                @mouseenter="hoveredMoodItem = item"
                @mouseleave="hoveredMoodItem = null"
                class="flex-1 min-w-[3px] h-full transition-opacity hover:opacity-100 opacity-85 cursor-pointer focus:outline-none"
                :style="{ backgroundColor: item.color || '#dc143c' }"
                :title="`${item.date} · ${item.mood}`"
              ></button>
            </div>
          </div>

          <div class="pt-2 border-t border-[#16161c] text-[11px] font-mono min-h-[36px] flex items-center">
            <template v-if="hoveredMoodItem">
              <span
                class="w-2 h-2 rounded-full mr-2 shrink-0"
                :style="{ backgroundColor: hoveredMoodItem.color }"
              ></span>
              <span class="text-zinc-300 shrink-0 mr-2">{{ hoveredMoodItem.date }}</span>
              <span class="text-[#f43f5e] shrink-0 mr-2">[{{ hoveredMoodItem.mood }}]</span>
              <span class="text-zinc-500 truncate">{{ hoveredMoodItem.summary }}</span>
            </template>
            <span v-else class="text-zinc-600">按时间顺序排列近 {{ data.mood_timeline.length }} 篇心境主题色</span>
          </div>
        </div>

        <!-- 情绪频次排行 -->
        <div class="bg-[#09090c] border border-[#1a1a22] rounded-xs p-4 space-y-3">
          <div class="flex items-center justify-between text-xs font-mono text-zinc-300">
            <span><span class="text-[#dc143c] mr-1.5">✧</span>情绪词分布</span>
            <span class="text-[10px] text-zinc-500">篇数 · 平均字数</span>
          </div>

          <div v-if="data.mood_distribution.length === 0" class="py-6 text-center text-xs text-zinc-600 font-mono">
            暂无情绪标签数据
          </div>

          <div v-else class="space-y-2 max-h-48 overflow-y-auto pr-1 no-scrollbar">
            <div
              v-for="m in data.mood_distribution"
              :key="m.mood"
              class="space-y-1"
            >
              <div class="flex items-center justify-between text-[11px] font-mono">
                <div class="flex items-center space-x-2">
                  <span class="w-2 h-2 rounded-full shrink-0" :style="{ backgroundColor: m.color }"></span>
                  <span class="text-zinc-200">{{ m.mood }}</span>
                </div>
                <div class="text-zinc-500">
                  <span class="text-zinc-300">{{ m.count }}</span> 篇 · {{ m.avg_words }} 字
                </div>
              </div>
              <div class="h-1.5 w-full bg-[#121217] rounded-xs overflow-hidden">
                <div
                  class="h-full rounded-xs transition-all duration-300"
                  :style="{
                    width: `${Math.max(4, (m.count / maxMoodCount) * 100)}%`,
                    backgroundColor: m.color
                  }"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 4. 写作节律：24小时分布 & 星期分布 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- 24小时时段分布 -->
        <div class="bg-[#09090c] border border-[#1a1a22] rounded-xs p-4 space-y-3">
          <div class="flex items-center justify-between text-xs font-mono text-zinc-300">
            <span><span class="text-[#dc143c] mr-1.5">✧</span>写作时段分布 (24H)</span>
            <span class="text-[11px] text-zinc-500">
              高峰: <span class="text-[#f43f5e]">{{ peakHourText }}</span>
            </span>
          </div>

          <div class="h-28 flex items-end gap-1 pt-2">
            <div
              v-for="h in data.hourly_distribution"
              :key="h.hour"
              class="flex-1 flex flex-col items-center justify-end h-full group relative"
              :title="`${String(h.hour).padStart(2, '0')}:00 · ${h.count} 篇 · ${h.words} 字`"
            >
              <div
                class="w-full rounded-t-[2px] transition-all duration-200"
                :class="h.count > 0 ? 'bg-[#dc143c]/75 group-hover:bg-[#f43f5e]' : 'bg-[#16161d]'"
                :style="{ height: h.count > 0 ? `${Math.max(10, (h.count / maxHourlyCount) * 100)}%` : '3px' }"
              ></div>
            </div>
          </div>
          <div class="flex justify-between text-[10px] font-mono text-zinc-600 pt-1 border-t border-[#16161c]">
            <span>00:00</span>
            <span>06:00</span>
            <span>12:00</span>
            <span>18:00</span>
            <span>23:00</span>
          </div>
        </div>

        <!-- 星期分布 -->
        <div class="bg-[#09090c] border border-[#1a1a22] rounded-xs p-4 space-y-3">
          <div class="flex items-center justify-between text-xs font-mono text-zinc-300">
            <span><span class="text-[#dc143c] mr-1.5">✧</span>星期习惯分布</span>
            <span class="text-[10px] text-zinc-500">篇数与字数</span>
          </div>

          <div class="space-y-2">
            <div
              v-for="w in data.weekday_distribution"
              :key="w.weekday"
              class="flex items-center gap-2.5 text-[11px] font-mono"
            >
              <span class="w-8 text-zinc-400 shrink-0">{{ w.label }}</span>
              <div class="flex-1 h-2 bg-[#121217] rounded-xs overflow-hidden">
                <div
                  class="h-full bg-[#dc143c]/80 rounded-xs transition-all duration-300"
                  :style="{ width: w.count > 0 ? `${Math.max(3, (w.count / maxWeekdayCount) * 100)}%` : '0%' }"
                ></div>
              </div>
              <span class="w-24 text-right text-zinc-500 shrink-0">
                <span class="text-zinc-300">{{ w.count }}</span> 篇 · {{ formatNumber(w.words) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 5. 高频实体与关注焦点 -->
      <div class="bg-[#09090c] border border-[#1a1a22] rounded-xs p-4 space-y-3">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div class="text-xs font-mono text-zinc-300">
            <span class="text-[#dc143c] mr-1.5">✧</span>关注焦点与实体排行
          </div>
          <span class="text-[10px] font-mono text-zinc-500">点击标签可直接检索相关记忆</span>
        </div>

        <div v-if="Object.keys(data.entity_groups).length === 0" class="py-6 text-center text-xs text-zinc-600 font-mono">
          暂无实体提取记录
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          <div
            v-for="(items, etype) in data.entity_groups"
            :key="etype"
            class="bg-[#0c0c10] border border-[#1a1a20] rounded-xs p-3 space-y-2.5"
          >
            <div class="text-[11px] font-mono text-zinc-400 flex items-center justify-between border-b border-[#18181f] pb-1.5">
              <span>{{ getEntityTypeLabel(etype) }}</span>
              <span class="text-[10px] text-zinc-600 uppercase">{{ etype }}</span>
            </div>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="ent in items"
                :key="ent.name"
                @click="$emit('search-entity', ent.name)"
                class="inline-flex items-center space-x-1.5 px-2 py-1 bg-[#14141a] hover:bg-[#180a0e] border border-[#22222c] hover:border-[#dc143c]/50 rounded-xs text-[11px] font-mono text-zinc-200 hover:text-[#f43f5e] transition-colors cursor-pointer"
              >
                <span>{{ ent.name }}</span>
                <span class="text-[10px] text-zinc-500">{{ ent.count }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 6. 实体关系 & 核心被引用记忆 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- 高频关系边 -->
        <div class="bg-[#09090c] border border-[#1a1a22] rounded-xs p-4 space-y-3">
          <div class="text-xs font-mono text-zinc-300">
            <span class="text-[#dc143c] mr-1.5">✧</span>高频关联脉络
          </div>
          <div v-if="data.top_relations.length === 0" class="py-6 text-center text-xs text-zinc-600 font-mono">
            暂无实体关系记录
          </div>
          <div v-else class="space-y-1.5">
            <div
              v-for="(rel, idx) in data.top_relations"
              :key="idx"
              class="flex items-center justify-between px-2.5 py-1.5 bg-[#0c0c10] border border-[#18181f] rounded-xs text-[11px] font-mono"
            >
              <div class="flex items-center space-x-1.5 truncate">
                <span class="text-zinc-200">{{ rel.source_name }}</span>
                <span class="text-[#dc143c] text-[10px]">—[{{ rel.relation }}]→</span>
                <span class="text-zinc-200">{{ rel.target_name }}</span>
              </div>
              <span class="text-[10px] text-zinc-500 shrink-0 ml-2">w={{ rel.weight }}</span>
            </div>
          </div>
        </div>

        <!-- 被引用最多的核心记忆 -->
        <div class="bg-[#09090c] border border-[#1a1a22] rounded-xs p-4 space-y-3">
          <div class="flex items-center justify-between text-xs font-mono text-zinc-300">
            <span><span class="text-[#dc143c] mr-1.5">✧</span>高频被引用核心记忆</span>
            <span class="text-[10px] text-zinc-500">点击查看</span>
          </div>
          <div v-if="data.top_quoted_diaries.length === 0" class="py-6 text-center text-xs text-zinc-600 font-mono">
            暂无日记引用记录
          </div>
          <div v-else class="space-y-2">
            <button
              v-for="q in data.top_quoted_diaries"
              :key="q.id"
              @click="$emit('open-diary', q.id)"
              class="w-full text-left p-2.5 bg-[#0c0c10] hover:bg-[#14141a] border border-[#18181f] hover:border-[#dc143c]/50 rounded-xs transition-colors cursor-pointer space-y-1"
            >
              <div class="flex items-center justify-between text-[10px] font-mono">
                <div class="flex items-center space-x-2">
                  <span class="w-1.5 h-1.5 rounded-full" :style="{ backgroundColor: q.mood_color }"></span>
                  <span class="text-zinc-400">{{ q.created_at }}</span>
                  <span v-if="q.mood" class="text-[#f43f5e]">[{{ q.mood }}]</span>
                </div>
                <span class="text-[#dc143c]">被引用 {{ q.quote_count }} 次</span>
              </div>
              <p class="text-xs text-zinc-200 line-clamp-1">{{ q.summary }}</p>
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { diaryApi } from '../api/diary'

const emit = defineEmits(['open-diary', 'search-entity'])

const rangeOptions = [
  { label: '全部', value: 'all' },
  { label: '近一年', value: '365d' },
  { label: '近90天', value: '90d' },
  { label: '近30天', value: '30d' }
]

const selectedRange = ref('all')
const loading = ref(false)
const errorMsg = ref('')
const data = ref(null)

const hoveredHeatDay = ref(null)
const hoveredMoodItem = ref(null)

const fetchAnalytics = async () => {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await diaryApi.getAnalyticsOverview(selectedRange.value)
    data.value = res.data
  } catch (err) {
    errorMsg.value = err?.response?.data?.detail || '获取数据分析失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

const changeRange = (val) => {
  if (selectedRange.value === val) return
  selectedRange.value = val
  fetchAnalytics()
}

onMounted(fetchAnalytics)

const formatNumber = (n) => {
  if (n == null) return '0'
  return Number(n).toLocaleString('zh-CN')
}

// 构建热力图网格（按周列排列；“全部”模式下最多展示 104 周以覆盖更长历史）
const heatmapWeeks = computed(() => {
  const map = {}
  let earliestDate = null
  if (data.value?.heatmap) {
    data.value.heatmap.forEach(d => {
      map[d.date] = d
      if (!earliestDate || d.date < earliestDate) {
        earliestDate = d.date
      }
    })
  }

  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const end = new Date(today)
  const defaultStart = new Date(today)
  defaultStart.setDate(defaultStart.getDate() - 364)

  let start = defaultStart
  if (selectedRange.value === 'all' && earliestDate) {
    const earliest = new Date(earliestDate + 'T00:00:00')
    if (!isNaN(earliest.getTime()) && earliest < defaultStart) {
      const maxLookback = new Date(today)
      maxLookback.setDate(maxLookback.getDate() - 727) // 最多约 104 周 (2年)
      start = earliest > maxLookback ? earliest : maxLookback
    }
  }
  start.setDate(start.getDate() - start.getDay())

  const weeks = []
  let currentWeek = []
  const cursor = new Date(start)
  const pad = (n) => String(n).padStart(2, '0')

  while (cursor <= end || currentWeek.length > 0) {
    const dateStr = `${cursor.getFullYear()}-${pad(cursor.getMonth() + 1)}-${pad(cursor.getDate())}`
    const isFuture = cursor > end
    const entry = map[dateStr]
    currentWeek.push({
      date: dateStr,
      count: entry ? entry.count : 0,
      words: entry ? entry.words : 0,
      future: isFuture
    })

    if (currentWeek.length === 7) {
      weeks.push(currentWeek)
      currentWeek = []
      if (cursor >= end) break
    }
    cursor.setDate(cursor.getDate() + 1)
  }
  return weeks
})

const getHeatColor = (words) => {
  if (!words || words <= 0) return '#121217'
  if (words < 100) return '#4a0e1a'
  if (words < 300) return '#88132b'
  if (words < 700) return '#be123c'
  return '#f43f5e'
}

const maxMoodCount = computed(() => {
  if (!data.value?.mood_distribution?.length) return 1
  return Math.max(...data.value.mood_distribution.map(m => m.count), 1)
})

const maxHourlyCount = computed(() => {
  if (!data.value?.hourly_distribution?.length) return 1
  return Math.max(...data.value.hourly_distribution.map(h => h.count), 1)
})

const peakHourText = computed(() => {
  if (!data.value?.hourly_distribution?.length) return '-'
  const best = data.value.hourly_distribution.reduce((a, b) => (b.count > a.count ? b : a), { hour: 0, count: 0 })
  if (best.count === 0) return '-'
  return `${String(best.hour).padStart(2, '0')}:00 (${best.count} 篇)`
})

const maxWeekdayCount = computed(() => {
  if (!data.value?.weekday_distribution?.length) return 1
  return Math.max(...data.value.weekday_distribution.map(w => w.count), 1)
})

const entityTypeLabels = {
  person: '人物',
  place: '地点',
  event: '事件',
  concept: '主题 / 概念',
  tag: '标签',
  pet: '宠物',
  time: '时间'
}

const getEntityTypeLabel = (type) => entityTypeLabels[type] || type
</script>

