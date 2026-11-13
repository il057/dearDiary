<template>
  <div
    class="relative w-full h-full bg-[#050505] overflow-hidden overscroll-none touch-none select-none border border-[#16161c] rounded-xs"
  >
    <!-- 2D 记忆星系 Canvas 画板 -->
    <canvas ref="canvasRef" class="w-full h-full block touch-none cursor-grab active:cursor-grabbing"></canvas>

    <!-- 左上角极简星图 HUD 与模式切换 -->
    <div v-if="!loading" class="absolute top-3 left-3 right-16 z-20 flex flex-col gap-2 pointer-events-none">
      <div class="flex flex-wrap items-center gap-2 pointer-events-auto">
        <!-- 视图切换胶囊 -->
        <div class="inline-flex items-center bg-[#08080a]/90 backdrop-blur-md border border-[#1c1c24] rounded-xs p-0.5 text-[11px] font-mono">
          <button
            @click="switchGraphMode('diary')"
            class="px-2 py-0.5 rounded-xs transition-colors cursor-pointer"
            :class="graphMode === 'diary' ? 'bg-[#180a0e] text-[#f43f5e] border border-[#dc143c]/50' : 'text-zinc-400 hover:text-zinc-200'"
          >
            日记星系
          </button>
          <button
            @click="switchGraphMode('entity')"
            class="px-2 py-0.5 rounded-xs transition-colors cursor-pointer"
            :class="graphMode === 'entity' ? 'bg-[#180a0e] text-[#f43f5e] border border-[#dc143c]/50' : 'text-zinc-400 hover:text-zinc-200'"
          >
            实体关系
          </button>
        </div>

        <div v-if="nodeCount > 0" class="inline-flex items-center space-x-2 text-[11px] font-mono text-zinc-400 bg-[#08080a]/85 backdrop-blur-md border border-[#1c1c24] px-2.5 py-1 rounded-xs w-fit">
          <span class="text-[#dc143c] text-xs leading-none">✦</span>
          <span>{{ graphMode === 'diary' ? '日记' : '实体' }}: <strong class="text-zinc-200">{{ nodeCount }}</strong></span>
          <span class="text-zinc-600">·</span>
          <span>{{ graphMode === 'diary' ? '关联' : '关系' }}: <strong class="text-zinc-200">{{ linkCount }}</strong></span>
          <button
            v-if="highlightTag || selectedNode"
            @click="clearSelection"
            class="ml-2 text-[#f43f5e] hover:underline cursor-pointer"
          >
            [清除高亮]
          </button>
        </div>
      </div>

      <!-- 高频实体快捷点亮胶囊（日记星系模式） -->
      <div v-if="graphMode === 'diary' && topEntities.length > 0" class="flex flex-wrap items-center gap-1.5 pointer-events-auto">
        <button
          v-for="ent in topEntities"
          :key="ent"
          @click="highlightByEntity(ent)"
          class="px-2 py-0.5 text-[10px] font-mono rounded-xs border backdrop-blur-md transition-colors cursor-pointer"
          :class="highlightTag === ent
            ? 'bg-[#180a0e]/95 text-[#f43f5e] border-[#dc143c]'
            : 'bg-[#08080a]/80 hover:bg-[#141418] text-zinc-400 hover:text-zinc-200 border-[#1c1c24]'"
        >
          #{{ ent }}
        </button>
      </div>
    </div>

    <!-- 右上角视角居中复位按钮 -->
    <button
      v-if="!loading && nodeCount > 0"
      @click="resetZoom"
      class="absolute top-3 right-3 z-20 p-2 bg-[#08080a]/85 hover:bg-[#16161c] text-zinc-400 hover:text-[#f43f5e] border border-[#1c1c24] rounded-xs backdrop-blur-md transition-colors cursor-pointer"
      title="重置星图视角"
    >
      <Crosshair class="w-4 h-4" />
    </button>

    <!-- 选中节点后的底部精炼卡片 -->
    <Transition name="drawer">
      <div
        v-if="selectedNode"
        class="absolute bottom-4 left-4 right-4 max-w-2xl mx-auto bg-[#08080b]/95 backdrop-blur-xl border border-[#24242e] p-4 rounded-xs shadow-2xl z-30 pointer-events-auto"
      >
        <template v-if="graphMode === 'diary'">
          <div class="flex items-center justify-between pb-2 border-b border-[#16161c] text-xs text-zinc-400">
            <div class="flex items-center space-x-2 flex-wrap gap-y-1">
              <span
                class="text-xs leading-none"
                :style="{
                  color: selectedNode.color || '#dc143c'
                }"
              >✦</span>
              <span class="font-mono text-zinc-300">{{ selectedNode.created_at }}</span>
              <span v-if="selectedNode.mood" class="px-1.5 py-0.5 bg-[#180a0e] border border-[#dc143c]/30 text-[#f43f5e] rounded-xs text-[10px]">
                {{ selectedNode.mood }}
              </span>
              <span v-if="highlightTag" class="text-[10px] px-1.5 py-0.5 bg-[#180a0e] text-[#f43f5e] border border-[#dc143c]/40 rounded-xs font-mono">
                #{{ highlightTag }} · {{ highlightNeighborIds.size }} 篇
              </span>
              <span v-else-if="highlightNeighborIds.size > 0" class="text-[10px] text-zinc-500 font-mono">
                · {{ highlightNeighborIds.size }} 篇关联
              </span>
            </div>

            <div class="flex items-center space-x-2">
              <button
                @click="$emit('open-diary', selectedNode.id)"
                class="text-[11px] font-mono text-[#f43f5e] hover:text-white px-2 py-0.5 bg-[#180a0e] border border-[#dc143c]/40 rounded-xs cursor-pointer transition-colors"
              >
                阅读全文 →
              </button>
              <button @click="clearSelection" class="p-1 text-zinc-500 hover:text-zinc-200 cursor-pointer">
                <X class="w-4 h-4" />
              </button>
            </div>
          </div>

          <p class="mt-2.5 text-zinc-200 text-xs sm:text-sm leading-relaxed line-clamp-3 select-text font-normal">
            {{ selectedNode.content }}
          </p>

          <!-- 实体标签栏：点击任意 Tag 高亮所有关联日记 -->
          <div v-if="selectedNode.entities && selectedNode.entities.length" class="mt-2.5 pt-2 border-t border-[#16161c] flex flex-wrap gap-1.5 items-center">
            <button
              v-for="ent in selectedNode.entities"
              :key="ent"
              @click.stop="highlightByEntity(ent)"
              class="px-2 py-0.5 rounded-xs text-[10px] font-mono transition-all cursor-pointer"
              :class="highlightTag === ent
                ? 'bg-[#180a0e] text-[#f43f5e] border border-[#dc143c]/60'
                : 'bg-[#0c0c10] hover:bg-[#16161c] text-zinc-400 hover:text-zinc-200 border border-[#1e1e26]'"
            >
              #{{ ent }}
            </button>
          </div>
        </template>

        <template v-else>
          <div class="flex items-center justify-between pb-2 border-b border-[#16161c] text-xs text-zinc-400">
            <div class="flex items-center space-x-2 flex-wrap gap-y-1">
              <span class="text-xs leading-none" :style="{ color: selectedNode.color || '#dc143c' }">✦</span>
              <span class="text-sm font-semibold text-zinc-100">{{ selectedNode.name }}</span>
              <span class="px-1.5 py-0.5 bg-[#12080a] border border-[#dc143c]/30 text-[#f43f5e] rounded-xs text-[10px] font-mono">
                {{ getTypeLabel(selectedNode.entity_type, selectedNode.is_owner) }}
              </span>
              <span v-if="selectedNode.count > 0" class="text-[10px] text-zinc-500 font-mono">
                提及 {{ selectedNode.count }} 篇
              </span>
            </div>

            <div class="flex items-center space-x-2">
              <button
                v-if="!selectedNode.is_owner || selectedNode.count > 0"
                @click="$emit('search-entity', selectedNode.name)"
                class="text-[11px] font-mono text-[#f43f5e] hover:text-white px-2 py-0.5 bg-[#180a0e] border border-[#dc143c]/40 rounded-xs cursor-pointer transition-colors"
              >
                搜索相关日记 →
              </button>
              <button @click="clearSelection" class="p-1 text-zinc-500 hover:text-zinc-200 cursor-pointer">
                <X class="w-4 h-4" />
              </button>
            </div>
          </div>

          <div v-if="selectedEntityRelations.length > 0" class="mt-2.5 flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
            <span
              v-for="(rel, idx) in selectedEntityRelations"
              :key="idx"
              class="inline-flex items-center space-x-1 text-[11px] px-2 py-0.5 bg-[#0c0c10] border border-[#1e1e26] rounded-xs text-zinc-300"
            >
              <span class="font-medium">{{ rel.sourceName }}</span>
              <span class="text-[#f43f5e] font-mono text-[10px]">—[{{ rel.relation }}]→</span>
              <span class="font-medium">{{ rel.targetName }}</span>
            </span>
          </div>
          <p v-else class="mt-2.5 text-xs text-zinc-500">暂无与其他实体的直接关系记录</p>
        </template>
      </div>
    </Transition>

    <!-- 加载指示 -->
    <div v-if="loading" class="absolute inset-0 flex flex-col items-center justify-center bg-[#050505]/80 backdrop-blur-xs space-y-2.5 text-xs text-zinc-500 font-mono">
      <div class="flex items-center space-x-2 text-xs">
        <span class="text-zinc-700">✧</span>
        <span class="text-[#dc143c] animate-pulse">✦</span>
        <span class="text-zinc-700">✧</span>
      </div>
      <span>加载中...</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  forceCollide
} from 'd3-force'
import { zoom, zoomIdentity } from 'd3-zoom'
import { select } from 'd3-selection'
import { X, Crosshair } from '@lucide/vue'
import { diaryApi } from '../api/diary'

const emit = defineEmits(['open-diary', 'search-entity'])

const CLUSTER_MODE_KEY = 'deardiary_cluster_mode'
const savedClusterMode = localStorage.getItem(CLUSTER_MODE_KEY)
const canvasRef = ref(null)
const graphMode = ref(savedClusterMode === 'entity' ? 'entity' : 'diary')
const loading = ref(false)
const selectedNode = ref(null)
const highlightNeighborIds = ref(new Set())
const highlightTag = ref('')
const nodeCount = ref(0)
const linkCount = ref(0)
const topEntities = ref([])

let simulation = null
let currentTransform = zoomIdentity
let zoomBehaviorInstance = null
let canvasSelection = null
let nodesData = []
let linksData = []
let animFrameId = null
let clickHandler = null

const ENTITY_TYPE_COLORS = {
  person: '#f43f5e',
  pet: '#f59e0b',
  place: '#38bdf8',
  time: '#a78bfa',
  concept: '#94a3b8'
}

const ENTITY_TYPE_LABELS = {
  person: '人物',
  pet: '宠物',
  place: '地点',
  time: '时间',
  concept: '概念'
}

const getTypeLabel = (etype, isOwner) => {
  if (isOwner) return '自己'
  return ENTITY_TYPE_LABELS[etype] || '概念'
}

const selectedEntityRelations = computed(() => {
  if (graphMode.value !== 'entity' || !selectedNode.value) return []
  const nid = selectedNode.value.id
  return linksData
    .filter(l => {
      const sid = l.source.id !== undefined ? l.source.id : l.source
      const tid = l.target.id !== undefined ? l.target.id : l.target
      return sid === nid || tid === nid
    })
    .map(l => ({
      sourceName: l.source.name || l.source.id || l.source,
      targetName: l.target.name || l.target.id || l.target,
      relation: l.relation
    }))
})

const switchGraphMode = (mode) => {
  if (graphMode.value === mode) return
  graphMode.value = mode
  try {
    localStorage.setItem(CLUSTER_MODE_KEY, mode)
  } catch {
    // ignore
  }
  clearSelection()
  initGraph()
}

const clearSelection = () => {
  selectedNode.value = null
  highlightTag.value = ''
  highlightNeighborIds.value.clear()
}

const resetZoom = () => {
  if (canvasSelection && zoomBehaviorInstance) {
    canvasSelection.transition().duration(350).call(zoomBehaviorInstance.transform, zoomIdentity)
  }
}

const getNeighbors = (nodeId) => {
  const neighbors = new Set()
  for (const link of linksData) {
    const sid = link.source.id !== undefined ? link.source.id : link.source
    const tid = link.target.id !== undefined ? link.target.id : link.target
    if (sid === nodeId) neighbors.add(tid)
    if (tid === nodeId) neighbors.add(sid)
  }
  return neighbors
}

const highlightByEntity = (ent) => {
  if (highlightTag.value === ent) {
    highlightTag.value = ''
    if (selectedNode.value) {
      highlightNeighborIds.value = getNeighbors(selectedNode.value.id)
    } else {
      highlightNeighborIds.value.clear()
    }
    return
  }

  highlightTag.value = ent
  const matched = new Set()
  for (const node of nodesData) {
    if (node.entities && node.entities.includes(ent)) {
      matched.add(node.id)
    }
  }
  highlightNeighborIds.value = matched
}

const initGraph = async () => {
  if (animFrameId) {
    cancelAnimationFrame(animFrameId)
    animFrameId = null
  }
  if (simulation) {
    simulation.stop()
    simulation = null
  }
  currentTransform = zoomIdentity

  loading.value = true
  try {
    if (graphMode.value === 'entity') {
      const res = await diaryApi.getEntityGraph()
      nodesData = (res.data.nodes || []).map(n => ({
        ...n,
        color: n.is_owner ? '#dc143c' : (ENTITY_TYPE_COLORS[n.entity_type] || '#94a3b8'),
        val: Math.min(16, Math.max(5, 5 + (n.count || 0) * 1.4 + (n.is_owner ? 4 : 0)))
      }))
      linksData = res.data.links || []
      topEntities.value = []
    } else {
      const res = await diaryApi.getClusterGraph2D()
      nodesData = res.data.nodes || []
      linksData = res.data.links || []

      // 统计高频实体 TOP 8 用于快捷滤镜
      const entCounts = {}
      nodesData.forEach(n => {
        (n.entities || []).forEach(e => {
          entCounts[e] = (entCounts[e] || 0) + 1
        })
      })
      topEntities.value = Object.entries(entCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8)
        .map(([name]) => name)
    }

    nodeCount.value = nodesData.length
    linkCount.value = linksData.length

    const canvas = canvasRef.value
    if (!canvas) return
    const ctx = canvas.getContext('2d')

    const dpr = window.devicePixelRatio || 1
    const rect = canvas.parentElement.getBoundingClientRect()
    const width = rect.width
    const height = rect.height

    canvas.width = width * dpr
    canvas.height = height * dpr
    ctx.scale(dpr, dpr)

    const getBaseRadius = (node) => {
      const v = Math.min(Math.max(node.val || 5, 5), 16)
      return 2.8 + ((v - 5) / 11) * 5.2
    }

    const isMobile = width < 640
    simulation = forceSimulation(nodesData)
      .force('link', forceLink(linksData).id(d => d.id).distance(isMobile ? 64 : 76).strength(0.5))
      .force('charge', forceManyBody().strength(isMobile ? -190 : -230).distanceMax(480))
      .force('center', forceCenter(width / 2, height / 2).strength(0.26))
      .force('collide', forceCollide().radius(d => getBaseRadius(d) + 10).strength(0.85))
      .alphaDecay(0.025)

    for (let i = 0; i < 140; ++i) {
      simulation.tick()
    }

    const render = () => {
      ctx.save()
      ctx.clearRect(0, 0, width, height)

      ctx.translate(currentTransform.x, currentTransform.y)
      ctx.scale(currentTransform.k, currentTransform.k)

      const k = currentTransform.k
      const invSqrtK = 1 / Math.sqrt(k)
      const hasHighlight = !!selectedNode.value || !!highlightTag.value
      const selectedId = selectedNode.value ? selectedNode.value.id : null

      // 1. 绘制星轨连线（按关联强度区分透明度与粗细）
      for (const link of linksData) {
        if (link.source.x === undefined || link.target.x === undefined) continue
        const sid = link.source.id !== undefined ? link.source.id : link.source
        const tid = link.target.id !== undefined ? link.target.id : link.target

        let isRelated = false
        if (selectedId && (sid === selectedId || tid === selectedId)) {
          isRelated = true
        } else if (highlightTag.value && highlightNeighborIds.value.has(sid) && highlightNeighborIds.value.has(tid)) {
          isRelated = true
        }

        const strength = Math.min(1, Math.max(0.2, ((link.value || 1) - 0.6) / 2.2))

        ctx.beginPath()
        ctx.moveTo(link.source.x, link.source.y)
        ctx.lineTo(link.target.x, link.target.y)

        if (hasHighlight) {
          if (isRelated) {
            ctx.strokeStyle = 'rgba(220, 20, 60, 0.78)'
            ctx.lineWidth = 1.45 * invSqrtK
          } else {
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.025)'
            ctx.lineWidth = 0.5 * invSqrtK
          }
        } else {
          const alpha = (0.045 + strength * 0.115).toFixed(3)
          ctx.strokeStyle = `rgba(255, 255, 255, ${alpha})`
          ctx.lineWidth = (0.55 + strength * 0.65) * invSqrtK
        }
        ctx.stroke()

        // 实体关系模式下绘制箭头与关系标签
        if (graphMode.value === 'entity' && link.relation) {
          const dx = link.target.x - link.source.x
          const dy = link.target.y - link.source.y
          const dist = Math.hypot(dx, dy)
          if (dist > 12) {
            const ux = dx / dist
            const uy = dy / dist
            const targetR = getBaseRadius(link.target) * Math.pow(k, -0.18) + 3 * invSqrtK
            const ax = link.target.x - ux * targetR
            const ay = link.target.y - uy * targetR
            const arrowLen = 5.5 * invSqrtK
            const angle = Math.atan2(dy, dx)

            ctx.beginPath()
            ctx.moveTo(ax, ay)
            ctx.lineTo(ax - arrowLen * Math.cos(angle - Math.PI / 6), ay - arrowLen * Math.sin(angle - Math.PI / 6))
            ctx.lineTo(ax - arrowLen * Math.cos(angle + Math.PI / 6), ay - arrowLen * Math.sin(angle + Math.PI / 6))
            ctx.closePath()
            ctx.fillStyle = (hasHighlight && isRelated) ? 'rgba(244, 63, 94, 0.9)' : 'rgba(255, 255, 255, 0.25)'
            ctx.fill()

            if ((hasHighlight && isRelated) || (!hasHighlight && k >= 1.15)) {
              const mx = (link.source.x + link.target.x) / 2
              const my = (link.source.y + link.target.y) / 2
              const relFont = Math.max(7.5, 9 * invSqrtK)
              ctx.font = `${relFont}px UnifontJP, monospace`
              ctx.textAlign = 'center'
              ctx.fillStyle = (hasHighlight && isRelated) ? '#fda4af' : 'rgba(161, 161, 170, 0.65)'
              ctx.fillText(link.relation, mx, my - 3 * invSqrtK)
            }
          }
        }
      }

      // 2. 绘制极简星辰节点（保留清晰的枢纽/普通节点大小层级）
      const labelBoxes = []
      const showZoomLabels = graphMode.value === 'entity' ? k >= 0.75 : k >= (isMobile ? 1.65 : 1.45)

      for (const node of nodesData) {
        if (node.x === undefined) continue
        const isSelected = selectedId === node.id
        const isNeighbor = highlightNeighborIds.value.has(node.id)
        const baseRadius = getBaseRadius(node) * Math.pow(k, -0.18)

        let nodeOpacity = 1.0
        if (hasHighlight && !isSelected && !isNeighbor) {
          nodeOpacity = 0.15
        }

        ctx.globalAlpha = nodeOpacity
        const nodeColor = node.color || '#dc143c'

        // 柔和星云光晕
        const haloExtra = isSelected ? 6.5 : (isNeighbor ? 3.8 : 2.2)
        ctx.beginPath()
        ctx.arc(node.x, node.y, baseRadius + haloExtra * invSqrtK, 0, 2 * Math.PI)
        ctx.fillStyle = isSelected ? 'rgba(220, 20, 60, 0.36)' : `${nodeColor}24`
        ctx.fill()

        // 核心星点
        ctx.beginPath()
        ctx.arc(node.x, node.y, baseRadius, 0, 2 * Math.PI)
        ctx.fillStyle = isSelected ? '#dc143c' : nodeColor
        ctx.fill()

        if (isSelected) {
          ctx.strokeStyle = '#ffffff'
          ctx.lineWidth = 1.6 * invSqrtK
          ctx.stroke()
        } else if (isNeighbor) {
          ctx.strokeStyle = '#f43f5e'
          ctx.lineWidth = 1.1 * invSqrtK
          ctx.stroke()
        }

        // 标签标注：日记模式显示日期，实体模式显示实体名，并做防重叠碰撞检测
        const shouldTryLabel = isSelected || isNeighbor || (!hasHighlight && showZoomLabels)
        if (shouldTryLabel) {
          const labelText = graphMode.value === 'entity' ? (node.name || '') : (node.created_at || '').slice(0, 10)
          const fontSize = Math.max(8.5, 10.5 * invSqrtK)
          ctx.font = `${fontSize}px UnifontJP, monospace`
          ctx.textAlign = 'center'

          const labelY = node.y + baseRadius + 10 * invSqrtK
          const textW = ctx.measureText(labelText).width + 6 * invSqrtK
          const textH = fontSize + 3 * invSqrtK
          const box = {
            x1: node.x - textW / 2,
            x2: node.x + textW / 2,
            y1: labelY - textH,
            y2: labelY + 2 * invSqrtK
          }

          const overlaps = !isSelected && labelBoxes.some(b =>
            box.x1 < b.x2 && box.x2 > b.x1 && box.y1 < b.y2 && box.y2 > b.y1
          )

          if (!overlaps) {
            labelBoxes.push(box)
            ctx.fillStyle = isSelected ? '#ffffff' : (isNeighbor ? '#fda4af' : 'rgba(212, 212, 216, 0.82)')
            ctx.fillText(labelText, node.x, labelY)
          }
        }

        ctx.globalAlpha = 1.0
      }

      ctx.restore()
      animFrameId = requestAnimationFrame(render)
    }

    render()

    zoomBehaviorInstance = zoom()
      .scaleExtent([0.3, 4.5])
      .on('zoom', (event) => {
        currentTransform = event.transform
      })

    canvasSelection = select(canvas)
    canvasSelection.call(zoomBehaviorInstance)
    canvasSelection.call(zoomBehaviorInstance.transform, zoomIdentity)

    if (clickHandler) {
      canvas.removeEventListener('click', clickHandler)
    }
    clickHandler = (e) => {
      const rect = canvas.getBoundingClientRect()
      const clickX = (e.clientX - rect.left - currentTransform.x) / currentTransform.k
      const clickY = (e.clientY - rect.top - currentTransform.y) / currentTransform.k

      let clicked = null
      let minDist = 22 / currentTransform.k

      for (const node of nodesData) {
        const dist = Math.hypot(node.x - clickX, node.y - clickY)
        if (dist < minDist) {
          minDist = dist
          clicked = node
        }
      }

      if (clicked) {
        selectedNode.value = clicked
        highlightTag.value = ''
        highlightNeighborIds.value = getNeighbors(clicked.id)
      } else {
        clearSelection()
      }
    }
    canvas.addEventListener('click', clickHandler)
  } catch (err) {
    console.error('加载 2D 聚类星图失败', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  initGraph()
})

onBeforeUnmount(() => {
  if (animFrameId) cancelAnimationFrame(animFrameId)
  if (simulation) simulation.stop()
})
</script>

<style scoped>
.drawer-enter-active,
.drawer-leave-active {
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
  transform: translateY(16px);
}
</style>
