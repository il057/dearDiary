<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      @click.self="handleCancel"
      class="fixed inset-0 z-[80] bg-black/75 backdrop-blur-[2px] flex items-center justify-center p-4 select-none animate-in fade-in duration-150"
    >
      <div
        class="w-full max-w-sm bg-[#0a0a0e] border border-[#261d24] rounded-xs shadow-[0_20px_50px_rgba(0,0,0,0.85)] overflow-hidden"
        role="dialog"
        aria-modal="true"
      >
        <!-- 顶部提示栏 -->
        <div class="px-4 py-3 border-b border-[#19161d] flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <span class="text-[#dc143c] text-xs leading-none">✦</span>
            <h3 class="text-xs font-mono font-semibold text-zinc-100 tracking-wide">
              {{ title }}
            </h3>
          </div>
          <button
            @click="handleCancel"
            :disabled="loading"
            class="text-zinc-500 hover:text-zinc-200 transition-colors cursor-pointer disabled:opacity-40"
            title="关闭"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- 正文说明 -->
        <div class="px-4 py-4 text-xs sm:text-[13px] text-zinc-300 leading-relaxed whitespace-pre-wrap">
          {{ message }}
        </div>

        <!-- 底部操作按钮 -->
        <div class="px-4 py-3 bg-[#08080b] border-t border-[#16141a] flex items-center justify-end space-x-2 text-xs">
          <button
            @click="handleCancel"
            :disabled="loading"
            class="px-3 py-1.5 text-zinc-400 hover:text-zinc-100 hover:bg-[#14141a] border border-[#22222b] rounded-xs transition-colors cursor-pointer disabled:opacity-40"
          >
            {{ cancelText }}
          </button>
          <button
            @click="handleConfirm"
            :disabled="loading"
            class="px-3.5 py-1.5 rounded-xs font-medium transition-colors cursor-pointer disabled:opacity-40"
            :class="danger
              ? 'bg-[#dc143c] hover:bg-[#e11d48] text-white shadow-[0_0_12px_rgba(220,20,60,0.3)]'
              : 'bg-[#180a0e] hover:bg-[#260e15] text-[#fda4af] border border-[#dc143c]/50'"
          >
            {{ loading ? '处理中...' : confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { watch, onBeforeUnmount } from 'vue'
import { X } from '@lucide/vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: '确认操作'
  },
  message: {
    type: String,
    default: '确定要执行此操作吗？'
  },
  confirmText: {
    type: String,
    default: '确定'
  },
  cancelText: {
    type: String,
    default: '取消'
  },
  danger: {
    type: Boolean,
    default: true
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['confirm', 'cancel'])

const handleConfirm = () => {
  if (!props.loading) emit('confirm')
}

const handleCancel = () => {
  if (!props.loading) emit('cancel')
}

const onKeyDown = (e) => {
  if (props.isOpen && e.key === 'Escape') {
    handleCancel()
  }
}

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      window.addEventListener('keydown', onKeyDown)
    } else {
      window.removeEventListener('keydown', onKeyDown)
    }
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown)
})
</script>
