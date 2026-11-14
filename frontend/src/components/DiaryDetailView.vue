<template>
  <div class="fixed inset-0 z-50 bg-[#050505] flex flex-col text-zinc-100 select-text overflow-hidden overscroll-contain animate-in fade-in duration-150">
    <!-- 顶部操作导航条 -->
    <header class="flex items-center justify-between gap-2 px-3 sm:px-8 pwa-safe-top pb-3 sm:pb-3.5 border-b border-[#18181f] bg-[#08080a] select-none shrink-0">
      <div class="flex items-center space-x-2 sm:space-x-3 min-w-0">
        <button
          @click="$emit('close')"
          class="inline-flex items-center space-x-1.5 px-2 sm:px-2.5 py-1.5 sm:py-1 text-xs text-zinc-400 hover:text-zinc-100 hover:bg-[#16161c] rounded-xs border border-neutral-800 transition-colors cursor-pointer shrink-0"
          title="返回"
        >
          <ArrowLeft class="w-3.5 h-3.5" />
          <span class="hidden sm:inline">返回</span>
        </button>

        <div class="flex items-center space-x-1.5 sm:space-x-2 min-w-0">
          <span class="text-[#dc143c] text-xs leading-none shrink-0">✦</span>
          <span class="text-xs font-semibold text-zinc-200 truncate">
            {{ isEditing ? '编辑' : '详情' }}
          </span>
        </div>
      </div>

      <!-- 右侧操作栏 -->
      <div class="flex items-center space-x-1.5 sm:space-x-2 shrink-0">
        <template v-if="!isEditing">
          <button
            @click="$emit('reindex', diary.id || diary.diary_id)"
            :disabled="isProcessing"
            class="p-1.5 text-zinc-400 hover:text-zinc-100 hover:bg-[#16161c] rounded-xs border border-neutral-800 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-wait"
            title="重新分析"
          >
            <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin text-[#dc143c]': isProcessing }" />
          </button>

          <button
            @click="$emit('quote', diary)"
            class="inline-flex items-center sm:space-x-1 p-1.5 sm:px-3 sm:py-1 bg-[#180a0e] hover:bg-[#260e15] text-[#fda4af] rounded-xs border border-[#dc143c]/40 text-xs transition-colors cursor-pointer"
            title="引用这篇日记并写新感悟"
          >
            <Quote class="w-3.5 h-3.5 sm:w-3 sm:h-3 text-[#dc143c]" />
            <span class="hidden sm:inline">引用</span>
          </button>

          <button
            @click="startEdit"
            class="inline-flex items-center sm:space-x-1 p-1.5 sm:px-3 sm:py-1 bg-neutral-900 hover:bg-neutral-800 text-zinc-200 rounded-xs border border-neutral-800 text-xs transition-colors cursor-pointer"
            title="编辑"
          >
            <Pencil class="w-3.5 h-3.5 sm:w-3 sm:h-3 text-[#dc143c]" />
            <span class="hidden sm:inline">编辑</span>
          </button>

          <button
            @click="handleDelete"
            class="p-1.5 text-zinc-500 hover:text-red-400 hover:bg-[#16161c] rounded-xs border border-neutral-800 transition-colors cursor-pointer"
            title="删除此篇日记"
          >
            <Trash2 class="w-3.5 h-3.5" />
          </button>
        </template>

        <template v-else>
          <button
            @click="cancelEdit"
            class="px-2.5 sm:px-3 py-1 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-neutral-900 rounded-xs transition-colors cursor-pointer"
          >
            取消
          </button>
          <button
            @click="saveEdit"
            :disabled="!editDraftContent.trim()"
            class="inline-flex items-center space-x-1.5 px-3 sm:px-4 py-1 bg-[#dc143c] hover:bg-[#e11d48] text-white text-xs font-medium rounded-xs active:scale-95 disabled:opacity-40 transition-all cursor-pointer shadow-[0_0_10px_rgba(220,20,60,0.3)]"
          >
            <Check class="w-3.5 h-3.5" />
            <span class="hidden sm:inline">保存修改</span>
            <span class="sm:hidden">保存</span>
          </button>
        </template>
      </div>
    </header>

    <!-- 主体区域 -->
    <main class="flex-1 overflow-y-auto px-4 sm:px-12 md:px-24 py-5 sm:py-8 pb-[max(env(safe-area-inset-bottom),1.5rem)] max-w-4xl w-full mx-auto space-y-6">
      <!-- 1. 编辑状态 -->
      <div v-if="isEditing" class="space-y-4">
        <!-- 修改时间 -->
        <div class="flex flex-wrap items-center justify-between gap-2 p-3 bg-[#0a0a0d] border border-[#18181f] rounded-xs text-xs select-none">
          <div class="flex items-center space-x-2 min-w-0">
            <Clock class="w-4 h-4 text-[#dc143c] shrink-0" />
            <span class="text-zinc-400 hidden sm:inline">日期时间:</span>
            <input
              type="datetime-local"
              v-model="editDraftTime"
              class="bg-[#050505] border border-neutral-800 text-zinc-100 rounded-xs px-2.5 py-1 text-xs outline-none focus:border-[#dc143c] max-w-full"
            />
          </div>
          <span class="text-[11px] text-zinc-500 font-mono shrink-0">{{ editDraftContent.length }} 字</span>
        </div>

        <!-- 编辑状态下的引用管理 -->
        <div v-if="editDraftQuotes.length > 0" class="space-y-2">
          <div
            v-for="q in editDraftQuotes"
            :key="q.id"
            class="flex items-start justify-between gap-3 p-3 bg-[#09090d] border border-[#1c1c24] border-l-2 border-l-[#dc143c] rounded-xs"
          >
            <div class="min-w-0 flex-1 space-y-1">
              <div class="flex items-center space-x-2 text-[11px] select-none">
                <Quote class="w-3 h-3 text-[#dc143c] shrink-0" />
                <span class="font-mono text-zinc-400">引用 · {{ formatCleanTime(q.created_at) }}</span>
                <span v-if="q.mood" class="px-1.5 py-0.2 bg-[#12080a] text-[#f43f5e] border border-[#dc143c]/30 rounded-xs text-[10px]">
                  {{ q.mood }}
                </span>
              </div>
              <p class="text-xs text-zinc-300 line-clamp-2 leading-relaxed">{{ q.content }}</p>
            </div>
            <button
              type="button"
              @click="editDraftQuotes = editDraftQuotes.filter(item => item.id !== q.id)"
              class="p-1 text-zinc-500 hover:text-red-400 transition-colors cursor-pointer shrink-0"
              title="移除引用"
            >
              <X class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <!-- 编辑大文本框 -->
        <textarea
          v-model="editDraftContent"
          placeholder="日记正文..."
          class="w-full bg-[#08080a] p-4 text-sm sm:text-base text-zinc-100 placeholder-neutral-600 border border-neutral-800 rounded-xs focus:border-[#dc143c] focus:outline-none min-h-[50vh] resize-y leading-relaxed font-normal"
        ></textarea>
      </div>

      <!-- 2. 普通阅读态 -->
      <div v-else class="space-y-6">
        <!-- 头部元数据条 -->
        <div class="flex items-center justify-between pb-4 border-b border-[#18181f] text-xs text-zinc-400 select-none">
          <div class="flex items-center space-x-3">
            <!-- 情绪星标 -->
            <span
              class="text-sm leading-none transition-opacity"
              :class="{ 'animate-pulse': isProcessing }"
              :style="{
                color: diary.mood_color || '#dc143c'
              }"
            >✦</span>

            <!-- 心情标签 (重算时展示骨架屏) -->
            <span
              v-if="isProcessing"
              class="w-16 h-5 bg-[#180c10] border border-[#dc143c]/25 rounded-xs animate-pulse"
            ></span>
            <span v-else-if="diary.mood" class="px-2 py-0.5 bg-[#12080a] text-[#f43f5e] border border-[#dc143c]/40 rounded-xs text-[11px]">
              {{ diary.mood }}
            </span>

            <span class="font-mono text-zinc-400">{{ formatCleanTime(diary.created_at) }}</span>
          </div>

          <span class="font-mono text-zinc-500">{{ (diary.content || '').length }} 字</span>
        </div>

        <!-- 语义检索原因 (如有) -->
        <div v-if="diary.matched_reason" class="p-2.5 bg-[#180a0e] border border-[#dc143c]/30 text-[#f43f5e] rounded-xs text-xs flex items-center space-x-2">
          <Sparkles class="w-4 h-4 text-[#dc143c]" />
          <span>{{ diary.matched_reason }}</span>
        </div>

        <!-- 引用的过往日记 (如有) -->
        <div v-if="diary.quoted_diaries && diary.quoted_diaries.length > 0" class="space-y-2 select-none">
          <div
            v-for="q in diary.quoted_diaries"
            :key="q.id"
            @click="$emit('select-related', q.id)"
            class="p-3.5 bg-[#09090d] hover:bg-[#100a0d] border border-[#1c1c24] hover:border-[#dc143c]/50 border-l-2 border-l-[#dc143c] rounded-xs transition-colors cursor-pointer space-y-1.5 group"
          >
            <div class="flex items-center justify-between text-[11px] gap-2">
              <div class="flex items-center space-x-2 min-w-0">
                <Quote class="w-3 h-3 text-[#dc143c] shrink-0" />
                <span class="font-mono text-zinc-400 truncate">引用自 {{ formatCleanTime(q.created_at) }}</span>
                <span v-if="q.mood" class="px-1.5 py-0.2 bg-[#12080a] text-[#f43f5e] border border-[#dc143c]/30 rounded-xs text-[10px] shrink-0">
                  {{ q.mood }}
                </span>
              </div>
              <span class="text-[10px] text-zinc-600 group-hover:text-[#f43f5e] font-mono transition-colors shrink-0"><span class="hidden sm:inline">查看原文 </span>→</span>
            </div>
            <p class="text-xs sm:text-[13px] text-zinc-300 group-hover:text-zinc-100 line-clamp-3 leading-relaxed">
              {{ q.content }}
            </p>
          </div>
        </div>

        <!-- 完整长文内容展示（支持搜索关键词/实体高亮） -->
        <article class="text-sm sm:text-base text-zinc-200 leading-relaxed sm:leading-loose whitespace-pre-wrap select-text font-normal tracking-wide">
          <template v-if="highlightTerms.length > 0">
            <template v-for="(seg, sIdx) in splitHighlightSegments(diary.content, highlightTerms)" :key="sIdx">
              <mark v-if="seg.match" class="bg-[#dc143c]/25 text-[#fda4af] px-0.5 rounded-xs">{{ seg.text }}</mark>
              <template v-else>{{ seg.text }}</template>
            </template>
          </template>
          <template v-else>{{ diary.content }}</template>
        </article>

        <!-- 底部标签栏 -->
        <div class="pt-6 border-t border-[#18181f] space-y-3 select-none">
          <div class="flex items-center justify-between text-xs text-zinc-500">
            <span class="font-mono uppercase tracking-wider text-[11px]">标签</span>
            <span v-if="isProcessing" class="text-[10px] text-[#f43f5e] font-mono inline-flex items-center space-x-1">
              <span class="animate-pulse">✦</span>
              <span>正在分析...</span>
            </span>
          </div>

          <!-- 重算骨架屏占位 -->
          <div v-if="isProcessing" class="flex flex-wrap items-center gap-2">
            <span class="w-14 h-6 bg-[#0e0e13] border border-[#1f1f28] rounded-xs animate-pulse"></span>
            <span class="w-20 h-6 bg-[#0e0e13] border border-[#1f1f28] rounded-xs animate-pulse"></span>
            <span class="w-16 h-6 bg-[#0e0e13] border border-[#1f1f28] rounded-xs animate-pulse"></span>
            <span class="w-24 h-6 bg-[#0e0e13] border border-[#1f1f28] rounded-xs animate-pulse"></span>
          </div>

          <div v-else class="flex flex-wrap items-center gap-2">
            <span
              v-for="ent in (diary.entities || diary.related_entities || [])"
              :key="ent"
              class="group inline-flex items-center text-xs px-2.5 py-1 rounded-xs border transition-colors"
              :class="isEntityHighlighted(ent, highlightTerms)
                ? 'bg-[#180a0e] text-[#fda4af] border-[#dc143c]/60 font-medium'
                : 'bg-[#0c0c0f] hover:bg-[#180a0e] text-zinc-300 hover:text-[#f43f5e] border-neutral-800 hover:border-[#dc143c]/40'"
            >
              <span @click="$emit('filter-tag', ent)" class="cursor-pointer">#{{ ent }}</span>
              <button
                @click.stop="handleRemoveTag(ent)"
                class="ml-1.5 text-zinc-600 hover:text-red-400 cursor-pointer"
                title="移除标签"
              >
                <X class="w-3 h-3" />
              </button>
            </span>

            <!-- 手工快速补充标签 -->
            <span v-if="isAddingTag" class="inline-flex items-center space-x-1">
              <input
                v-model="newTagText"
                @keydown.enter.prevent="handleAddTag"
                @keydown.esc="isAddingTag = false"
                placeholder="新标签..."
                class="w-24 px-2 py-1 bg-[#050505] border border-neutral-700 rounded-xs text-xs text-zinc-100 focus:outline-none focus:border-[#dc143c]"
                autofocus
              />
              <button @click="handleAddTag" class="text-[#f43f5e] text-xs cursor-pointer px-1">确定</button>
              <button @click="isAddingTag = false" class="text-zinc-500 text-xs cursor-pointer px-1">取消</button>
            </span>
            <button
              v-else
              @click="isAddingTag = true"
              class="inline-flex items-center space-x-1 text-xs px-2.5 py-1 text-zinc-500 hover:text-zinc-200 bg-neutral-900 hover:bg-[#16161c] rounded-xs border border-dashed border-neutral-800 transition-colors cursor-pointer"
            >
              <Plus class="w-3 h-3 text-[#dc143c]" />
              <span>新标签</span>
            </button>
          </div>
        </div>

        <!-- 后续引用 / 感悟 (被哪些后来的日记引用了) -->
        <div v-if="diary.quoted_by && diary.quoted_by.length > 0" class="pt-6 border-t border-[#18181f] space-y-3 select-none">
          <div class="flex items-center justify-between text-xs text-zinc-500">
            <span class="font-mono uppercase tracking-wider text-[11px] flex items-center space-x-1.5">
              <Quote class="w-3 h-3 text-[#dc143c]" />
              <span>后续引用 ({{ diary.quoted_by.length }})</span>
            </span>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <div
              v-for="item in diary.quoted_by"
              :key="item.id"
              @click="$emit('select-related', item.id)"
              class="p-3 bg-[#09090d] hover:bg-[#100a0d] border border-[#1c1c24] hover:border-[#dc143c]/50 border-l-2 border-l-[#dc143c]/70 rounded-xs transition-colors cursor-pointer space-y-1.5 group"
            >
              <div class="flex items-center justify-between text-[11px] gap-2">
                <div class="flex items-center space-x-1.5 min-w-0">
                  <span class="text-xs leading-none shrink-0" :style="{ color: item.mood_color || '#dc143c' }">✦</span>
                  <span class="font-mono text-zinc-400 truncate">{{ formatCleanTime(item.created_at) }}</span>
                  <span v-if="item.mood" class="px-1.5 py-0.2 bg-[#12080a] text-[#f43f5e] border border-[#dc143c]/30 rounded-xs text-[10px] shrink-0">
                    {{ item.mood }}
                  </span>
                </div>
                <span class="text-[10px] text-zinc-600 group-hover:text-[#f43f5e] font-mono shrink-0"><span class="hidden sm:inline">查看 </span>→</span>
              </div>
              <p class="text-xs text-zinc-300 group-hover:text-zinc-100 line-clamp-2 leading-relaxed">
                {{ item.content }}
              </p>
            </div>
          </div>
        </div>

        <!-- 相关历史记忆推荐 -->
        <div v-if="relatedLoading || relatedDiaries.length > 0" class="pt-6 border-t border-[#18181f] space-y-3 select-none">
          <div class="flex items-center justify-between text-xs text-zinc-500">
            <span class="font-mono uppercase tracking-wider text-[11px] flex items-center space-x-1.5">
              <span class="text-[#dc143c]">✦</span>
              <span>相关记忆</span>
            </span>
            <span v-if="relatedLoading" class="text-[10px] text-zinc-600 font-mono">检索中...</span>
          </div>

          <div v-if="relatedLoading" class="space-y-2">
            <div v-for="i in 2" :key="i" class="h-14 bg-[#0a0a0d] border border-[#18181f] rounded-xs animate-pulse"></div>
          </div>

          <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <div
              v-for="item in relatedDiaries"
              :key="item.diary_id"
              @click="$emit('select-related', item.diary_id)"
              class="p-3 bg-[#08080b] hover:bg-[#0e0b0d] border border-[#18181f] hover:border-[#dc143c]/40 rounded-xs transition-colors cursor-pointer space-y-1.5 group"
            >
              <div class="flex items-center justify-between text-[11px] gap-2">
                <div class="flex items-center space-x-1.5 min-w-0">
                  <span class="text-xs leading-none shrink-0" :style="{ color: item.mood_color || '#dc143c' }">✦</span>
                  <span class="font-mono text-zinc-400 shrink-0">{{ formatCleanTime(item.created_at) }}</span>
                  <span v-if="item.mood" class="px-1.5 py-0.2 bg-[#12080a] text-[#f43f5e] border border-[#dc143c]/30 rounded-xs text-[10px] shrink-0">
                    {{ item.mood }}
                  </span>
                </div>
                <span class="text-[10px] text-[#f43f5e]/80 truncate">{{ item.matched_reason }}</span>
              </div>
              <p class="text-xs text-zinc-300 group-hover:text-zinc-100 line-clamp-2 leading-relaxed">
                {{ item.summary || item.content }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import {
  ArrowLeft, RefreshCw, Pencil, Trash2, Check,
  Clock, Sparkles, X, Plus, Quote
} from '@lucide/vue'
import { splitHighlightSegments, isEntityHighlighted } from '../utils/highlight'
import { diaryApi } from '../api/diary'

const props = defineProps({
  diary: {
    type: Object,
    required: true
  },
  isProcessing: {
    type: Boolean,
    default: false
  },
  highlightTerms: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits([
  'close', 'update', 'delete', 'reindex', 'filter-tag', 'update-entities', 'select-related', 'quote'
])

const isEditing = ref(false)
const editDraftContent = ref('')
const editDraftTime = ref('')
const editDraftQuotes = ref([])
const isAddingTag = ref(false)
const newTagText = ref('')
const relatedDiaries = ref([])
const relatedLoading = ref(false)

const fetchRelated = async (id) => {
  if (!id) {
    relatedDiaries.value = []
    return
  }
  relatedLoading.value = true
  try {
    const res = await diaryApi.getRelatedDiaries(id, 4)
    relatedDiaries.value = res.data || []
  } catch {
    relatedDiaries.value = []
  } finally {
    relatedLoading.value = false
  }
}

watch(
  () => props.diary?.id || props.diary?.diary_id,
  (newId) => {
    isEditing.value = false
    fetchRelated(newId)
  },
  { immediate: true }
)

const toDatetimeLocal = (isoStr) => {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  if (isNaN(d.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const startEdit = () => {
  editDraftContent.value = props.diary.content || ''
  editDraftTime.value = toDatetimeLocal(props.diary.created_at)
  editDraftQuotes.value = [...(props.diary.quoted_diaries || [])]
  isEditing.value = true
}

const cancelEdit = () => {
  isEditing.value = false
  editDraftContent.value = ''
  editDraftTime.value = ''
  editDraftQuotes.value = []
}

const saveEdit = () => {
  const updatedText = editDraftContent.value.trim()
  if (!updatedText) return

  let customCreatedAt = null
  if (editDraftTime.value) {
    const d = new Date(editDraftTime.value)
    if (!isNaN(d.getTime())) {
      customCreatedAt = d.toISOString()
    }
  }

  isEditing.value = false
  emit('update', {
    id: props.diary.id || props.diary.diary_id,
    content: updatedText,
    created_at: customCreatedAt,
    quoted_diary_ids: editDraftQuotes.value.map(q => q.id)
  })
}

const handleDelete = () => {
  emit('delete', props.diary.id || props.diary.diary_id)
}

const handleAddTag = () => {
  const tag = newTagText.value.trim()
  if (!tag) {
    isAddingTag.value = false
    return
  }
  const current = [...(props.diary.entities || props.diary.related_entities || [])]
  if (!current.includes(tag)) {
    current.push(tag)
    emit('update-entities', {
      id: props.diary.id || props.diary.diary_id,
      entities: current
    })
  }
  newTagText.value = ''
  isAddingTag.value = false
}

const handleRemoveTag = (ent) => {
  const current = (props.diary.entities || props.diary.related_entities || []).filter(e => e !== ent)
  emit('update-entities', {
    id: props.diary.id || props.diary.diary_id,
    entities: current
  })
}

const formatCleanTime = (timeStr) => {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  if (isNaN(d.getTime())) return timeStr
  const isDefaultNoon = d.getHours() === 12 && d.getMinutes() === 0 && d.getSeconds() === 0
  
  if (isDefaultNoon) {
    return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`
  }
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

