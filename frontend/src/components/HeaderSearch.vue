<template>
  <div class="relative w-full">
    <div class="relative flex items-center">
      <Search class="absolute left-3 w-4 h-4 text-zinc-500 pointer-events-none" />
      <input
        type="text"
        v-model="queryText"
        @keydown.enter="handleSearch"
        placeholder="搜索日记..."
        class="w-full pl-9 pr-9 py-2 bg-[#0c0c0e] text-xs sm:text-sm text-zinc-100 placeholder-neutral-600 rounded-xs border border-neutral-800 hover:border-neutral-700 focus:border-[#dc143c] focus:outline-none transition-colors"
      />
      <button
        v-if="queryText"
        @click="clearSearch"
        class="absolute right-2.5 p-1 text-zinc-500 hover:text-zinc-200 cursor-pointer"
        title="清除"
      >
        <X class="w-3.5 h-3.5" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Search, X } from '@lucide/vue'

const emit = defineEmits(['search', 'clear'])
const queryText = ref('')

const handleSearch = () => {
  if (queryText.value.trim()) {
    emit('search', queryText.value.trim())
  }
}

const clearSearch = () => {
  queryText.value = ''
  emit('clear')
}
</script>
