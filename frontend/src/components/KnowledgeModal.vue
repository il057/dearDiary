<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 bg-[#050505] flex flex-col text-zinc-100 select-none overflow-hidden overscroll-contain animate-in fade-in duration-150"
  >
    <!-- 顶栏：适配 iOS PWA 灵动岛安全区 -->
    <header class="flex items-center justify-between px-4 sm:px-8 pwa-safe-top pb-3.5 border-b border-[#18181f] bg-[#08080a] shrink-0">
      <div class="flex items-center space-x-3">
        <button
          @click="$emit('close')"
          class="inline-flex items-center space-x-1.5 px-2.5 py-1 text-xs text-zinc-400 hover:text-zinc-100 hover:bg-[#16161c] rounded-xs border border-[#1f1f26] transition-colors cursor-pointer"
        >
          <ArrowLeft class="w-3.5 h-3.5" />
          <span>返回</span>
        </button>

        <div class="flex items-center space-x-2">
          <span class="text-[#dc143c] text-xs leading-none">✦</span>
          <h3 class="text-xs sm:text-sm font-semibold text-zinc-100 tracking-wider">标签与别名</h3>
        </div>
      </div>

      <div class="text-[11px] text-zinc-500 font-mono hidden sm:flex items-center space-x-3">
        <span>别名: <strong class="text-zinc-200">{{ Object.keys(aliases).length }}</strong></span>
        <span>·</span>
        <span>标签: <strong class="text-[#f43f5e]">{{ Object.keys(entities).length }}</strong></span>
      </div>
    </header>

    <!-- 主体内容区：Web 端左右分栏，移动端上下流式，单一滚动条 -->
    <main class="flex-1 overflow-y-auto px-4 sm:px-8 py-6">
      <div class="w-full max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        <!-- 左栏 (4列)：实体别名归一 -->
        <section class="lg:col-span-4 space-y-4">
          <div class="bg-[#09090c] border border-[#1a1a20] rounded-xs p-4 space-y-4">
            <div class="pb-2.5 border-b border-[#15151a]">
              <div class="flex items-center space-x-2">
                <span class="text-[#dc143c] text-xs leading-none">✧</span>
                <h4 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider">别名合并</h4>
              </div>
              <p class="text-[11px] text-zinc-500 mt-1">将不同称呼合并为同一个标签</p>
            </div>

            <!-- 绑定输入框：两行垂直排列，避免移动端横向溢出 -->
            <div class="space-y-2.5">
              <div class="flex flex-col space-y-1.5">
                <input
                  v-model="newAlias"
                  placeholder="别名（如：Alex）"
                  class="w-full bg-[#050505] border border-[#1e1e26] rounded-xs px-3 py-2 text-zinc-100 text-xs focus:outline-none focus:border-[#dc143c] transition-colors"
                />
                <div class="text-center text-[#dc143c] text-xs font-mono leading-none select-none">↓</div>
                <input
                  v-model="newCanonical"
                  placeholder="合并到（如：张三）"
                  class="w-full bg-[#050505] border border-[#1e1e26] rounded-xs px-3 py-2 text-zinc-100 text-xs focus:outline-none focus:border-[#dc143c] transition-colors"
                  @keydown.enter="handleAddAlias"
                />
              </div>
              <button
                @click="handleAddAlias"
                :disabled="!newAlias.trim() || !newCanonical.trim()"
                class="w-full py-2 bg-[#dc143c] hover:bg-[#e11d48] text-white font-medium text-xs rounded-xs disabled:opacity-35 disabled:pointer-events-none transition-all cursor-pointer"
              >
                添加
              </button>
            </div>

            <!-- 现有映射列表 -->
            <div class="pt-2 border-t border-[#15151a] space-y-2">
              <div class="text-[11px] text-zinc-500 font-mono">已添加 ({{ Object.keys(aliases).length }})</div>

              <div v-if="Object.keys(aliases).length === 0" class="text-zinc-600 text-xs py-6 text-center border border-dashed border-[#18181f] rounded-xs">
                暂无别名
              </div>

              <div v-else class="space-y-1.5 max-h-[45vh] overflow-y-auto pr-1">
                <div
                  v-for="(canonical, alias) in aliases"
                  :key="alias"
                  class="flex items-center justify-between px-3 py-2 bg-[#060608] border border-[#18181f] rounded-xs text-xs group hover:border-[#2a2a35] transition-colors"
                >
                  <div class="flex items-center space-x-2 truncate">
                    <span class="text-zinc-400 font-mono truncate">{{ alias }}</span>
                    <span class="text-[#dc143c] text-[10px] shrink-0">➔</span>
                    <span class="text-zinc-100 font-medium truncate">{{ canonical }}</span>
                  </div>
                  <button
                    @click="handleDeleteAlias(alias)"
                    class="text-zinc-600 hover:text-red-400 cursor-pointer p-1 shrink-0 transition-colors"
                    title="解除此映射"
                  >
                    <X class="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 右栏 (8列)：日记关联实体图谱 -->
        <section class="lg:col-span-8 space-y-4">
          <div class="bg-[#09090c] border border-[#1a1a20] rounded-xs p-4 space-y-4">
            <!-- 标题与搜索框 -->
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#15151a]">
              <div>
                <h4 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider">
                  <span class="text-[#dc143c] mr-1.5">✧</span>全部标签 ({{ filteredEntities.length }})
                </h4>
              </div>

              <div class="relative w-full sm:w-56 shrink-0">
                <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
                <input
                  v-model="searchQuery"
                  placeholder="筛选标签..."
                  class="w-full pl-8 pr-7 py-1.5 bg-[#050505] border border-[#1e1e26] rounded-xs text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-[#dc143c]"
                />
                <button
                  v-if="searchQuery"
                  @click="searchQuery = ''"
                  class="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 cursor-pointer"
                >
                  <X class="w-3 h-3" />
                </button>
              </div>
            </div>

            <!-- 分类筛选 Tabs -->
            <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-1">
              <button
                v-for="cat in categoryTabs"
                :key="cat.value"
                @click="activeCategory = cat.value"
                class="shrink-0 px-2.5 py-1 rounded-xs text-[11px] font-mono border transition-colors cursor-pointer"
                :class="activeCategory === cat.value
                  ? 'bg-[#180a0e] text-[#f43f5e] border-[#dc143c]/60 font-medium'
                  : 'bg-[#060608] text-zinc-400 hover:text-zinc-200 border-[#18181f]'"
              >
                <span>{{ cat.label }}</span>
                <span class="ml-1 text-[10px] opacity-60">({{ getCategoryCount(cat.value) }})</span>
              </button>
            </div>

            <!-- 实体列表 -->
            <div v-if="filteredEntities.length === 0" class="text-zinc-600 text-xs py-12 text-center border border-dashed border-[#18181f] rounded-xs">
              暂无匹配标签
            </div>

            <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <div
                v-for="item in filteredEntities"
                :key="item.name"
                class="flex items-center justify-between p-2.5 bg-[#060608] border border-[#18181f] hover:border-[#252530] rounded-xs transition-colors"
              >
                <div class="flex items-center space-x-2 min-w-0 pr-2">
                  <span class="text-xs font-medium text-zinc-200 truncate">#{{ item.name }}</span>
                  <span v-if="item.count > 0" class="text-[10px] text-zinc-500 font-mono shrink-0">
                    {{ item.count }}篇
                  </span>
                </div>

                <!-- 快捷胶囊分类切换 + 删除 -->
                <div class="flex items-center space-x-1 shrink-0">
                  <button
                    v-for="t in typeOptions"
                    :key="t.value"
                    @click="handleUpdateType(item.name, t.value)"
                    class="px-1.5 py-0.5 text-[10px] rounded-xs border transition-colors cursor-pointer"
                    :class="(item.entity_type || 'concept') === t.value
                      ? 'bg-[#180a0e] text-[#f43f5e] border-[#dc143c]/50 font-medium'
                      : 'bg-transparent text-zinc-600 hover:text-zinc-300 border-transparent hover:border-[#22222c]'"
                    :title="`设为「${t.label}」`"
                  >
                    {{ t.short }}
                  </button>

                  <div class="w-px h-3 bg-[#1e1e26] mx-1"></div>

                  <button
                    @click="handleDeleteEntity(item.name)"
                    class="text-zinc-600 hover:text-red-400 cursor-pointer p-1 transition-colors"
                    title="从所有日记与词典中永久删除此标签"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>

      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ArrowLeft, Sparkles, X, Search, Trash2 } from '@lucide/vue'
import { diaryApi } from '../api/diary'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'updated', 'entity-deleted'])

const aliases = ref({})
const entities = ref({})
const newAlias = ref('')
const newCanonical = ref('')
const searchQuery = ref('')
const activeCategory = ref('all')

const categoryTabs = [
  { value: 'all', label: '全部' },
  { value: 'person', label: '人物' },
  { value: 'pet', label: '宠物' },
  { value: 'place', label: '地点' },
  { value: 'time', label: '时间' },
  { value: 'concept', label: '概念' }
]

const typeOptions = [
  { value: 'person', label: '人物', short: '人' },
  { value: 'pet', label: '宠物', short: '宠' },
  { value: 'place', label: '地点', short: '地' },
  { value: 'time', label: '时间', short: '时' },
  { value: 'concept', label: '概念', short: '概' }
]

const entitiesList = computed(() => {
  return Object.entries(entities.value)
    .map(([name, info]) => ({
      name,
      entity_type: info.entity_type || 'concept',
      count: info.count || 0
    }))
    .sort((a, b) => b.count - a.count)
})

const getCategoryCount = (cat) => {
  if (cat === 'all') return entitiesList.value.length
  return entitiesList.value.filter(e => e.entity_type === cat).length
}

const filteredEntities = computed(() => {
  return entitiesList.value.filter(item => {
    const matchCat = activeCategory.value === 'all' || item.entity_type === activeCategory.value
    const matchSearch = !searchQuery.value.trim() || item.name.toLowerCase().includes(searchQuery.value.trim().toLowerCase())
    return matchCat && matchSearch
  })
})

const loadKnowledge = async () => {
  try {
    const res = await diaryApi.getKnowledge()
    aliases.value = res.data.aliases || {}
    entities.value = res.data.entities || {}
  } catch (err) {
    console.error('加载知识库失败', err)
  }
}

watch(() => props.isOpen, (open) => {
  if (open) {
    loadKnowledge()
  }
})

const handleAddAlias = async () => {
  if (!newAlias.value.trim() || !newCanonical.value.trim()) return
  const a = newAlias.value.trim()
  const c = newCanonical.value.trim()
  try {
    await diaryApi.setAlias(a, c)
    aliases.value[a] = c
    if (!entities.value[c]) {
      entities.value[c] = { entity_type: 'person', count: 0 }
    }
    newAlias.value = ''
    newCanonical.value = ''
    emit('updated')
  } catch (err) {
    console.error('绑定别名失败', err)
  }
}

const handleDeleteAlias = async (alias) => {
  try {
    await diaryApi.deleteAlias(alias)
    const updatedAliases = { ...aliases.value }
    delete updatedAliases[alias]
    aliases.value = updatedAliases
    emit('updated')
  } catch (err) {
    console.error('删除别名失败', err)
  }
}

const handleDeleteEntity = async (name) => {
  try {
    await diaryApi.deleteEntity(name)
    const updated = { ...entities.value }
    delete updated[name]
    entities.value = updated

    const updatedAliases = { ...aliases.value }
    for (const [k, v] of Object.entries(updatedAliases)) {
      if (v === name || k === name) {
        delete updatedAliases[k]
      }
    }
    aliases.value = updatedAliases

    emit('entity-deleted', name)
  } catch (err) {
    console.error('删除实体失败', err)
  }
}

const handleUpdateType = async (name, newType) => {
  if (entities.value[name] && entities.value[name].entity_type === newType) return
  try {
    await diaryApi.updateEntityType(name, newType)
    if (entities.value[name]) {
      entities.value[name].entity_type = newType
    }
    emit('updated')
  } catch (err) {
    console.error('更新类型失败', err)
  }
}

onMounted(() => {
  if (props.isOpen) {
    loadKnowledge()
  }
})
</script>
