<template>
  <div class="fixed inset-0 z-50 bg-[#050505] flex flex-col text-zinc-100 select-text overflow-hidden overscroll-contain animate-in fade-in duration-150">
    <!-- 顶部操作导航条 -->
    <header class="flex items-center justify-between px-4 sm:px-8 pwa-safe-top pb-3.5 border-b border-[#18181f] bg-[#08080a] select-none shrink-0">
      <div class="flex items-center space-x-3">
        <button
          @click="$emit('close')"
          class="inline-flex items-center space-x-1.5 px-2.5 py-1 text-xs text-zinc-400 hover:text-zinc-100 hover:bg-[#16161c] rounded-xs border border-neutral-800 transition-colors cursor-pointer"
        >
          <ArrowLeft class="w-3.5 h-3.5" />
          <span>返回</span>
        </button>

        <div class="flex items-center space-x-2">
          <span class="text-[#dc143c] text-xs leading-none">✦</span>
          <span class="text-xs font-semibold text-zinc-200">
            {{ isEditing ? '编辑日记' : '日记详情' }}
          </span>
          <span class="text-[11px] text-zinc-500 font-mono">
            {{ formatCleanTime(diary.created_at) }}
          </span>
        </div>
      </div>

      <!-- 右侧操作栏 -->
      <div class="flex items-center space-x-2">
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
            @click="startEdit"
            class="inline-flex items-center space-x-1 px-3 py-1 bg-neutral-900 hover:bg-neutral-800 text-zinc-200 rounded-xs border border-neutral-800 text-xs transition-colors cursor-pointer"
          >
            <Pencil class="w-3 h-3 text-[#dc143c]" />
            <span>编辑</span>
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
            class="px-3 py-1 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-neutral-900 rounded-xs transition-colors cursor-pointer"
          >
            取消
          </button>
          <button
            @click="saveEdit"
            :disabled="!editDraftContent.trim()"
            class="inline-flex items-center space-x-1.5 px-4 py-1 bg-[#dc143c] hover:bg-[#e11d48] text-white text-xs font-medium rounded-xs active:scale-95 disabled:opacity-40 transition-all cursor-pointer shadow-[0_0_10px_rgba(220,20,60,0.3)]"
          >
            <Check class="w-3.5 h-3.5" />
            <span>保存修改</span>
          </button>
        </template>
      </div>
    </header>

    <!-- 主体区域 -->
    <main class="flex-1 overflow-y-auto px-4 sm:px-12 md:px-24 py-8 max-w-4xl w-full mx-auto space-y-6">
      <!-- 1. 编辑状态 -->
      <div v-if="isEditing" class="space-y-4">
        <!-- 修改时间 -->
        <div class="flex items-center justify-between p-3 bg-[#0a0a0d] border border-[#18181f] rounded-xs text-xs select-none">
          <div class="flex items-center space-x-2">
            <Clock class="w-4 h-4 text-[#dc143c]" />
            <span class="text-zinc-400">日期时间:</span>
            <input
              type="datetime-local"
              v-model="editDraftTime"
              class="bg-[#050505] border border-neutral-800 text-zinc-100 rounded-xs px-2.5 py-1 text-xs outline-none focus:border-[#dc143c]"
            />
          </div>
          <span class="text-[11px] text-zinc-500 font-mono">{{ editDraftContent.length }} 字</span>
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
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import {
  ArrowLeft, RefreshCw, Pencil, Trash2, Check,
  Clock, Sparkles, X, Plus
} from '@lucide/vue'
import { splitHighlightSegments, isEntityHighlighted } from '../utils/highlight'

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
  'close', 'update', 'delete', 'reindex', 'filter-tag', 'update-entities'
])

const isEditing = ref(false)
const editDraftContent = ref('')
const editDraftTime = ref('')
const isAddingTag = ref(false)
const newTagText = ref('')

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
  isEditing.value = true
}

const cancelEdit = () => {
  isEditing.value = false
  editDraftContent.value = ''
  editDraftTime.value = ''
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
    created_at: customCreatedAt
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

