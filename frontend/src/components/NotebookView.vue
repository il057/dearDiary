<template>
  <div class="flex-1 min-h-0 w-full flex flex-col justify-between select-none">
    <!-- 顶部手账控制栏 -->
    <div class="flex flex-wrap items-center justify-between gap-2 pb-2.5 shrink-0 text-xs">
      <div class="flex items-center space-x-2.5">
        <span class="text-[#dc143c] text-xs leading-none">✦</span>
        <span class="font-mono text-zinc-200 font-medium tracking-wide">随笔手账</span>
        <span v-if="orderedItems.length > 0" class="text-[11px] font-mono text-zinc-500">
          · {{ orderedItems.length }} 篇 / {{ virtualPages.length }} 页
        </span>
      </div>

      <div class="flex items-center space-x-1.5 sm:space-x-2">
        <!-- 翻阅顺序切换：倒序(最新在前) / 正序(从头翻阅) -->
        <button
          @click="toggleSortOrder"
          class="inline-flex items-center space-x-1 px-2.5 py-1 bg-[#0b0b0f] hover:bg-[#14141a] text-zinc-300 border border-[#22222b] rounded-xs text-[11px] font-mono transition-colors cursor-pointer"
          :title="sortOrder === 'asc' ? '当前：从最早开始翻阅' : '当前：从最新开始翻阅'"
        >
          <ArrowDownUp class="w-3 h-3 text-[#dc143c]" />
          <span>{{ sortOrder === 'asc' ? '正序' : '倒序' }}</span>
        </button>

        <!-- 快捷写日记 -->
        <button
          @click="$emit('create-diary')"
          class="inline-flex items-center space-x-1 px-2.5 py-1 bg-[#180a0e] hover:bg-[#240d13] text-[#f43f5e] border border-[#dc143c]/40 rounded-xs text-[11px] font-mono transition-colors cursor-pointer"
        >
          <Plus class="w-3 h-3" />
          <span>写日记</span>
        </button>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="flex-1 flex flex-col items-center justify-center text-zinc-500 text-xs font-mono space-y-2.5">
      <div class="flex items-center space-x-2">
        <span class="text-zinc-600">✧</span>
        <span class="text-[#dc143c] animate-pulse">✦</span>
        <span class="text-zinc-600">✧</span>
      </div>
      <span>正在装订手账...</span>
    </div>

    <!-- 空状态 -->
    <div v-else-if="orderedItems.length === 0" class="flex-1 flex flex-col items-center justify-center text-center space-y-4">
      <div class="w-56 h-72 rounded-r-md rounded-l-xs bg-[#141012] border border-[#2a1d22] shadow-2xl flex flex-col items-center justify-center p-6 space-y-4 relative overflow-hidden">
        <div class="absolute left-0 top-0 bottom-0 w-3 bg-gradient-to-r from-black/60 to-transparent"></div>
        <span class="text-[#dc143c] text-lg">✦</span>
        <div class="font-mono text-xs text-zinc-300 tracking-widest uppercase">dearDiary</div>
        <div class="text-[11px] text-zinc-500 font-mono">✧ 空白的日记本 ✧</div>
        <button
          @click="$emit('create-diary')"
          class="px-3 py-1.5 bg-[#dc143c] hover:bg-[#e11d48] text-white text-xs font-mono rounded-xs cursor-pointer transition-colors"
        >
          写下第一页
        </button>
      </div>
    </div>

    <!-- 仿真日记本主体舞台 -->
    <div
      v-else
      class="flex-1 min-h-0 flex items-center justify-center py-1 sm:py-2"
      @touchstart.passive="onTouchStart"
      @touchend.passive="onTouchEnd"
    >
      <!-- 暗色皮革硬壳封面外框 -->
      <div class="relative w-full max-w-6xl h-full max-h-[760px] flex flex-col rounded-sm p-1.5 sm:p-2.5 bg-[#0d0c10] border border-[#231e26] book-cover-shadow">
        <!-- 顶部红色丝带书签头 -->
        <div class="absolute -top-1 left-1/2 -translate-x-1/2 z-30 pointer-events-none hidden md:block">
          <div class="w-3.5 h-6 bg-[#dc143c] shadow-md rounded-t-xs"></div>
        </div>

        <!-- 底部垂落的红色丝带书签尾 -->
        <div class="absolute -bottom-3.5 left-1/2 -translate-x-1/2 z-30 pointer-events-none hidden md:block">
          <div class="w-3.5 h-5 bg-[#dc143c] ribbon-tail shadow-lg"></div>
        </div>

        <!-- 书页叠层厚度与书页容器 -->
        <div class="relative flex-1 min-h-0 flex book-perspective">
          <!-- 左侧叠页厚度（仅双页展开且非首页时可见） -->
          <div
            v-if="isSpread && currentSpreadIndex > 0"
            @click="prevPage"
            class="hidden md:block w-2 sm:w-3 shrink-0 rounded-l-xs cursor-pointer page-stack-dark"
            title="翻到上一页"
          ></div>

          <!-- 书页容器 -->
          <div
            class="relative flex-1 min-h-0 grid overflow-hidden rounded-xs"
            :class="isSpread ? 'grid-cols-2' : 'grid-cols-1'"
          >
            <!-- ==================== 左页（双页模式）或 当前页（单页模式） ==================== -->
            <div
              class="relative h-full min-h-0 flex flex-col overflow-hidden bg-[#0e0e13] text-zinc-200"
              :class="isSpread ? 'border-r border-black/40' : ''"
            >
              <!-- 左侧红边线装饰 -->
              <div class="absolute top-0 bottom-0 left-7 sm:left-9 w-px pointer-events-none bg-[#dc143c]/20"></div>

              <!-- 书脊阴影（双页模式在右侧，单页模式在左侧） -->
              <div
                class="absolute top-0 bottom-0 w-7 pointer-events-none z-10"
                :class="isSpread
                  ? 'right-0 bg-gradient-to-l from-black/35 via-black/10 to-transparent'
                  : 'left-0 bg-gradient-to-r from-black/40 via-black/10 to-transparent'"
              ></div>

              <!-- 左页/单页内容 -->
              <template v-if="displayLeftPage">
                <div class="relative z-10 flex-1 min-h-0 flex flex-col pl-10 pr-5 sm:pl-13 sm:pr-8 pt-5 pb-3">
                  <!-- 页眉：仅首篇第一页显示日期/星期/心情，续页保持极简留白 -->
                  <div
                    v-if="displayLeftPage.isFirstPage"
                    class="flex items-center justify-between pb-2.5 mb-2 border-b border-[#22222c] shrink-0 h-9"
                  >
                    <div class="flex items-baseline space-x-2 min-w-0">
                      <span class="font-mono font-bold text-sm sm:text-base tracking-tight text-zinc-100">
                        {{ formatPageDate(displayLeftPage.diary.created_at) }}
                      </span>
                      <span class="font-mono text-[11px] shrink-0 text-zinc-500">
                        {{ formatWeekday(displayLeftPage.diary.created_at) }}<template v-if="formatTimeOnly(displayLeftPage.diary.created_at)"> · {{ formatTimeOnly(displayLeftPage.diary.created_at) }}</template>
                      </span>
                    </div>

                    <div class="flex items-center space-x-1.5 shrink-0">
                      <span
                        class="text-xs leading-none"
                        :style="{ color: displayLeftPage.diary.mood_color || '#dc143c' }"
                      >✦</span>
                      <span
                        v-if="processingIds.has(displayLeftPage.diary.id || displayLeftPage.diary.diary_id)"
                        class="w-10 h-4 rounded-xs animate-pulse bg-[#1a1a22]"
                      ></span>
                      <span
                        v-else-if="displayLeftPage.diary.mood"
                        class="px-1.5 py-0.5 rounded-xs text-[10px] font-mono border bg-[#180a0e] text-[#f43f5e] border-[#dc143c]/35"
                      >
                        {{ displayLeftPage.diary.mood }}
                      </span>
                    </div>
                  </div>
                  <div v-else class="pb-2.5 mb-2 border-b border-[#191922]/60 shrink-0 h-9 flex items-center justify-between">
                    <span class="text-[10px] font-mono text-zinc-600 tracking-widest">· 续 ·</span>
                  </div>

                  <!-- 语义匹配提示（仅该日记第一页展示） -->
                  <div
                    v-if="displayLeftPage.isFirstPage && displayLeftPage.diary.matched_reason"
                    class="mb-2 px-2 py-0.5 rounded-xs text-[10px] font-mono inline-flex items-center space-x-1 self-start shrink-0 bg-[#180a0e] text-[#f43f5e] border border-[#dc143c]/25"
                  >
                    <span>✦</span>
                    <span>{{ displayLeftPage.diary.matched_reason }}</span>
                  </div>

                  <!-- 正文测量容器 & 展示区（自动分页，无滚动条，文字底部对齐横线） -->
                  <div ref="pageBodyMeasureWrapRef" class="relative flex-1 min-h-0 overflow-hidden">
                    <article
                      class="diary-paper-font ruled-lines-dark whitespace-pre-wrap text-[15px] leading-[30px] tracking-wide break-words text-zinc-200 select-text"
                      :style="{ height: snappedBodyHeight ? snappedBodyHeight + 'px' : '100%' }"
                    >
                      <template v-if="highlightTerms.length > 0">
                        <template v-for="(seg, sIdx) in splitHighlightSegments(displayLeftPage.text, highlightTerms)" :key="sIdx">
                          <mark
                            v-if="seg.match"
                            class="px-0.5 rounded-xs bg-[#dc143c]/30 text-[#fda4af]"
                          >{{ seg.text }}</mark>
                          <template v-else>{{ seg.text }}</template>
                        </template>
                      </template>
                      <template v-else>{{ displayLeftPage.text }}</template>
                    </article>

                    <!-- 贴在日记末尾的回响纸片 -->
                    <EchoPaperSlip
                      v-if="displayLeftPage.isLastPage && displayLeftPage.diary.echoes && displayLeftPage.diary.echoes.length > 0"
                      :echoes="displayLeftPage.diary.echoes"
                      :highlight-terms="highlightTerms"
                      @open-detail="$emit('select-diary', displayLeftPage.diary)"
                    />
                  </div>

                  <!-- 页脚：标签、全文编辑按钮与页码 -->
                  <div class="pt-2 mt-2 border-t border-[#202028] flex items-center justify-between gap-2 shrink-0 text-[11px]">
                    <div class="flex items-center gap-1 overflow-hidden max-h-5 flex-wrap">
                      <span
                        v-for="ent in (displayLeftPage.diary.entities || displayLeftPage.diary.related_entities || []).slice(0, 3)"
                        :key="ent"
                        class="px-1.5 py-0.2 rounded-xs text-[10px] font-mono border bg-[#121216] text-zinc-400 border-[#24242c]"
                      >
                        #{{ ent }}
                      </span>
                    </div>

                    <div class="flex items-center space-x-3 shrink-0">
                      <button
                        @click="$emit('select-diary', displayLeftPage.diary)"
                        class="text-[11px] font-mono text-[#f43f5e] hover:underline cursor-pointer"
                      >
                        详情/编辑
                      </button>
                      <span class="font-mono text-[10px] text-zinc-500">
                        P.{{ String(displayLeftPageNumber).padStart(2, '0') }}
                      </span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- 左下角上一页翻页热区 -->
              <button
                v-if="canGoPrev"
                @click="prevPage"
                class="absolute bottom-0 left-0 w-12 h-12 z-20 flex items-end justify-start p-2 group cursor-pointer"
                title="上一页 (←)"
              >
                <span class="opacity-45 group-hover:opacity-100 transition-opacity text-xs font-mono text-zinc-400">
                  ‹
                </span>
              </button>

              <!-- 单页模式右下角下一页热区 -->
              <button
                v-if="!isSpread && canGoNext"
                @click="nextPage"
                class="absolute bottom-0 right-0 w-12 h-12 z-20 flex items-end justify-end p-2 group cursor-pointer"
                title="下一页"
              >
                <span class="w-6 h-6 flex items-end justify-end opacity-65 group-hover:opacity-100 transition-all group-hover:scale-110 corner-curl-dark"></span>
              </button>
            </div>

            <!-- ==================== 右页（仅双页模式显示） ==================== -->
            <div
              v-if="isSpread"
              class="relative h-full min-h-0 flex flex-col overflow-hidden bg-[#0e0e13] text-zinc-200"
            >
              <!-- 右侧红边线装饰 -->
              <div class="absolute top-0 bottom-0 right-7 sm:right-9 w-px pointer-events-none bg-[#dc143c]/15"></div>

              <!-- 左侧书脊阴影 -->
              <div class="absolute top-0 bottom-0 left-0 w-7 pointer-events-none z-10 bg-gradient-to-r from-black/35 via-black/10 to-transparent"></div>

              <!-- 右页有内容 -->
              <template v-if="displayRightPage">
                <div class="relative z-10 flex-1 min-h-0 flex flex-col pl-8 pr-10 sm:pl-9 sm:pr-12 pt-5 pb-3">
                  <!-- 页眉：续页不重复展示日期 -->
                  <div
                    v-if="displayRightPage.isFirstPage"
                    class="flex items-center justify-between pb-2.5 mb-2 border-b border-[#22222c] shrink-0 h-9"
                  >
                    <div class="flex items-baseline space-x-2 min-w-0">
                      <span class="font-mono font-bold text-sm sm:text-base tracking-tight text-zinc-100">
                        {{ formatPageDate(displayRightPage.diary.created_at) }}
                      </span>
                      <span class="font-mono text-[11px] shrink-0 text-zinc-500">
                        {{ formatWeekday(displayRightPage.diary.created_at) }}<template v-if="formatTimeOnly(displayRightPage.diary.created_at)"> · {{ formatTimeOnly(displayRightPage.diary.created_at) }}</template>
                      </span>
                    </div>

                    <div class="flex items-center space-x-1.5 shrink-0">
                      <span
                        class="text-xs leading-none"
                        :style="{ color: displayRightPage.diary.mood_color || '#dc143c' }"
                      >✦</span>
                      <span
                        v-if="processingIds.has(displayRightPage.diary.id || displayRightPage.diary.diary_id)"
                        class="w-10 h-4 rounded-xs animate-pulse bg-[#1a1a22]"
                      ></span>
                      <span
                        v-else-if="displayRightPage.diary.mood"
                        class="px-1.5 py-0.5 rounded-xs text-[10px] font-mono border bg-[#180a0e] text-[#f43f5e] border-[#dc143c]/35"
                      >
                        {{ displayRightPage.diary.mood }}
                      </span>
                    </div>
                  </div>
                  <div v-else class="pb-2.5 mb-2 border-b border-[#191922]/60 shrink-0 h-9 flex items-center justify-between">
                    <span class="text-[10px] font-mono text-zinc-600 tracking-widest">· 续 ·</span>
                  </div>

                  <!-- 语义匹配提示 -->
                  <div
                    v-if="displayRightPage.isFirstPage && displayRightPage.diary.matched_reason"
                    class="mb-2 px-2 py-0.5 rounded-xs text-[10px] font-mono inline-flex items-center space-x-1 self-start shrink-0 bg-[#180a0e] text-[#f43f5e] border border-[#dc143c]/25"
                  >
                    <span>✦</span>
                    <span>{{ displayRightPage.diary.matched_reason }}</span>
                  </div>

                  <!-- 正文 -->
                  <div class="relative flex-1 min-h-0 overflow-hidden">
                    <article
                      class="diary-paper-font ruled-lines-dark whitespace-pre-wrap text-[15px] leading-[30px] tracking-wide break-words text-zinc-200 select-text"
                      :style="{ height: snappedBodyHeight ? snappedBodyHeight + 'px' : '100%' }"
                    >
                      <template v-if="highlightTerms.length > 0">
                        <template v-for="(seg, sIdx) in splitHighlightSegments(displayRightPage.text, highlightTerms)" :key="sIdx">
                          <mark
                            v-if="seg.match"
                            class="px-0.5 rounded-xs bg-[#dc143c]/30 text-[#fda4af]"
                          >{{ seg.text }}</mark>
                          <template v-else>{{ seg.text }}</template>
                        </template>
                      </template>
                      <template v-else>{{ displayRightPage.text }}</template>
                    </article>

                    <!-- 贴在日记末尾的回响纸片 -->
                    <EchoPaperSlip
                      v-if="displayRightPage.isLastPage && displayRightPage.diary.echoes && displayRightPage.diary.echoes.length > 0"
                      :echoes="displayRightPage.diary.echoes"
                      :highlight-terms="highlightTerms"
                      @open-detail="$emit('select-diary', displayRightPage.diary)"
                    />
                  </div>

                  <!-- 页脚 -->
                  <div class="pt-2 mt-2 border-t border-[#202028] flex items-center justify-between gap-2 shrink-0 text-[11px]">
                    <div class="flex items-center gap-1 overflow-hidden max-h-5 flex-wrap">
                      <span
                        v-for="ent in (displayRightPage.diary.entities || displayRightPage.diary.related_entities || []).slice(0, 3)"
                        :key="ent"
                        class="px-1.5 py-0.2 rounded-xs text-[10px] font-mono border bg-[#121216] text-zinc-400 border-[#24242c]"
                      >
                        #{{ ent }}
                      </span>
                    </div>

                    <div class="flex items-center space-x-3 shrink-0">
                      <button
                        @click="$emit('select-diary', displayRightPage.diary)"
                        class="text-[11px] font-mono text-[#f43f5e] hover:underline cursor-pointer"
                      >
                        详情/编辑
                      </button>
                      <span class="font-mono text-[10px] text-zinc-500">
                        P.{{ String(displayRightPageNumber).padStart(2, '0') }}
                      </span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- 若总页数为奇数，最后一页右侧展示空白待写页 -->
              <template v-else>
                <div class="relative z-10 flex-1 flex flex-col items-center justify-center p-8 text-center space-y-4">
                  <pre class="text-[11px] leading-relaxed font-mono text-zinc-600">  ✧  .  <span class="text-[#dc143c]">✦</span>  .  ✧
    未完待续</pre>
                  <button
                    @click="$emit('create-diary')"
                    class="px-3.5 py-1.5 rounded-xs text-xs font-mono border transition-colors cursor-pointer bg-[#180a0e] hover:bg-[#240d13] text-[#f43f5e] border-[#dc143c]/40"
                  >
                    + 续写新的一页
                  </button>
                </div>
              </template>

              <!-- 右下角下一页折角热区 -->
              <button
                v-if="canGoNext"
                @click="nextPage"
                class="absolute bottom-0 right-0 w-14 h-14 z-20 flex items-end justify-end p-2 group cursor-pointer"
                title="下一页 (→)"
              >
                <span class="w-7 h-7 opacity-65 group-hover:opacity-100 transition-all group-hover:scale-110 corner-curl-dark"></span>
              </button>
            </div>

            <!-- ==================== 3D 翻页动画层（同步挂载，零闪烁） ==================== -->
            <div
              v-if="flipState.active"
              :key="flipState.key"
              class="absolute top-0 bottom-0 z-30 pointer-events-none flip-leaf"
              :class="[
                isSpread
                  ? (flipState.direction === 'next' ? 'left-1/2 right-0 origin-left flip-spread-next' : 'left-0 right-1/2 origin-right flip-spread-prev')
                  : (flipState.direction === 'next' ? 'left-0 right-0 origin-left flip-mobile-next' : 'left-0 right-0 origin-left flip-mobile-prev')
              ]"
            >
              <!-- 翻页正面 -->
              <div class="absolute inset-0 backface-hidden overflow-hidden border-l border-black/30 bg-[#0e0e13] text-zinc-200">
                <div class="relative pl-10 pr-6 pt-5 pb-3 h-full flex flex-col">
                  <div class="h-9 pb-2.5 mb-2 border-b border-[#22222c] flex items-center">
                    <span v-if="flipState.frontPage?.isFirstPage" class="font-mono font-bold text-sm text-zinc-100">
                      {{ formatPageDate(flipState.frontPage.diary.created_at) }}
                    </span>
                    <span v-else class="text-[10px] font-mono text-zinc-600 tracking-widest">· 续 ·</span>
                  </div>
                  <p class="diary-paper-font ruled-lines-dark flex-1 overflow-hidden text-[15px] leading-[30px] tracking-wide whitespace-pre-wrap break-words text-zinc-200">
                    {{ flipState.frontPage?.text || '' }}
                  </p>
                </div>
                <div class="absolute inset-0 bg-gradient-to-r from-black/25 via-transparent to-black/10"></div>
              </div>

              <!-- 翻页背面 -->
              <div class="absolute inset-0 backface-hidden rotate-y-180 overflow-hidden bg-[#0e0e13] text-zinc-200">
                <div class="relative pl-10 pr-6 pt-5 pb-3 h-full flex flex-col">
                  <div class="h-9 pb-2.5 mb-2 border-b border-[#22222c] flex items-center">
                    <span v-if="flipState.backPage?.isFirstPage" class="font-mono font-bold text-sm text-zinc-100">
                      {{ formatPageDate(flipState.backPage.diary.created_at) }}
                    </span>
                    <span v-else class="text-[10px] font-mono text-zinc-600 tracking-widest">· 续 ·</span>
                  </div>
                  <p class="diary-paper-font ruled-lines-dark flex-1 overflow-hidden text-[15px] leading-[30px] tracking-wide whitespace-pre-wrap break-words text-zinc-200">
                    {{ flipState.backPage?.text || '' }}
                  </p>
                </div>
                <div class="absolute inset-0 bg-gradient-to-l from-black/25 via-transparent to-black/10"></div>
              </div>
            </div>
          </div>

          <!-- 右侧叠页厚度（尚有后续页面时可见） -->
          <div
            v-if="canGoNext"
            @click="nextPage"
            class="w-2 sm:w-3 shrink-0 rounded-r-xs cursor-pointer page-stack-dark"
            title="翻到下一页"
          ></div>
        </div>
      </div>
    </div>

    <!-- 隐藏的文本分页测量容器（与真实正文区域同宽同字体同行高） -->
    <div
      ref="measureElRef"
      aria-hidden="true"
      class="diary-paper-font fixed -left-[9999px] top-0 pointer-events-none opacity-0 whitespace-pre-wrap text-[15px] leading-[30px] tracking-wide break-words"
      :style="{ width: measureWidth + 'px' }"
    ></div>

    <!-- 底部翻页控制条 & 进度滑块 -->
    <div v-if="!loading && virtualPages.length > 0" class="pt-3 pb-1 shrink-0 flex items-center justify-between gap-3 text-xs font-mono">
      <button
        @click="prevPage"
        :disabled="!canGoPrev"
        class="inline-flex items-center space-x-1 px-3 py-1.5 bg-[#0b0b0f] hover:bg-[#16161d] disabled:opacity-30 disabled:pointer-events-none text-zinc-200 border border-[#22222b] rounded-xs cursor-pointer transition-colors"
      >
        <ChevronLeft class="w-3.5 h-3.5 text-[#dc143c]" />
        <span>上一页</span>
      </button>

      <!-- 中央进度滑块与页码 -->
      <div class="flex-1 max-w-md flex items-center space-x-3">
        <input
          type="range"
          :min="0"
          :max="maxIndex"
          :value="currentIndex"
          @input="onSliderJump"
          class="flex-1 accent-[#dc143c] h-1 bg-[#1e1e26] rounded-lg cursor-pointer"
        />
        <span class="text-[11px] text-zinc-400 shrink-0 tabular-nums">
          <template v-if="isSpread && rightPage">
            {{ leftPageNumber }}-{{ rightPageNumber }} / {{ virtualPages.length }}
          </template>
          <template v-else>
            {{ leftPageNumber }} / {{ virtualPages.length }}
          </template>
        </span>
      </div>

      <button
        @click="nextPage"
        :disabled="!canGoNext"
        class="inline-flex items-center space-x-1 px-3 py-1.5 bg-[#0b0b0f] hover:bg-[#16161d] disabled:opacity-30 disabled:pointer-events-none text-zinc-200 border border-[#22222b] rounded-xs cursor-pointer transition-colors"
      >
        <span>下一页</span>
        <ChevronRight class="w-3.5 h-3.5 text-[#dc143c]" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ChevronLeft, ChevronRight, Plus, ArrowDownUp } from '@lucide/vue'
import EchoPaperSlip from './EchoPaperSlip.vue'

const LINE_HEIGHT = 30

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
    type: Object,
    default: () => new Set()
  },
  highlightTerms: {
    type: Array,
    default: () => []
  }
})

defineEmits(['select-diary', 'create-diary'])

const BOOK_PAGE_KEY = 'deardiary_book_page'
const sortOrder = ref(localStorage.getItem('deardiary_book_sort') || 'desc')
const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1024)
const savedPageRaw = parseInt(localStorage.getItem(BOOK_PAGE_KEY) || '0', 10)
const savedPageIndex = Number.isFinite(savedPageRaw) && savedPageRaw >= 0 ? savedPageRaw : 0
let hasRestoredPage = false
const currentIndex = ref(0)

const isSpread = computed(() => windowWidth.value >= 768)
const stepSize = computed(() => (isSpread.value ? 2 : 1))

const orderedItems = computed(() => {
  const list = [...props.items]
  list.sort((a, b) => {
    const ta = new Date(a.created_at || 0).getTime()
    const tb = new Date(b.created_at || 0).getTime()
    return sortOrder.value === 'asc' ? ta - tb : tb - ta
  })
  return list
})

// 自动分页测量
const pageBodyMeasureWrapRef = ref(null)
const measureElRef = ref(null)
const measureWidth = ref(360)
const snappedBodyHeight = ref(0)
const virtualPages = ref([])

const paginateText = (text, maxH, el) => {
  const content = text || ''
  if (!content || !el || maxH <= 0) {
    return [content]
  }
  el.textContent = content
  if (el.scrollHeight <= maxH + 1) {
    return [content]
  }

  const chunks = []
  let start = 0
  const totalLen = content.length

  while (start < totalLen) {
    let low = start + 1
    let high = totalLen
    let best = start + 1

    while (low <= high) {
      const mid = (low + high) >> 1
      el.textContent = content.slice(start, mid)
      if (el.scrollHeight <= maxH + 1) {
        best = mid
        low = mid + 1
      } else {
        high = mid - 1
      }
    }

    if (best < totalLen && content[best] === '\n') {
      best += 1
    }

    chunks.push(content.slice(start, best))
    start = best
  }

  return chunks.length > 0 ? chunks : ['']
}

const recomputePages = () => {
  const items = orderedItems.value
  if (items.length === 0) {
    virtualPages.value = []
    return
  }

  const wrap = pageBodyMeasureWrapRef.value
  const el = measureElRef.value
  if (!wrap || !el || wrap.clientWidth <= 0 || wrap.clientHeight <= 0) {
    virtualPages.value = items.map(diary => ({
      diary,
      text: diary.content || '',
      pageInDiary: 1,
      totalInDiary: 1,
      isFirstPage: true,
      isLastPage: true
    }))
    return
  }

  measureWidth.value = wrap.clientWidth
  const lines = Math.max(3, Math.floor(wrap.clientHeight / LINE_HEIGHT))
  const maxH = lines * LINE_HEIGHT
  snappedBodyHeight.value = maxH
  el.style.width = wrap.clientWidth + 'px'

  const pages = []
  for (const diary of items) {
    const chunks = paginateText(diary.content || '', maxH, el)
    // 若该日记有回响纸片且最后一页剩余空间不足，则追加一页以防纸片遮挡正文末尾文字
    if (diary.echoes && diary.echoes.length > 0 && chunks.length > 0) {
      el.textContent = chunks[chunks.length - 1]
      const totalEchoChars = diary.echoes.reduce((sum, e) => sum + (e.content || '').length, 0)
      const estimatedSlipHeight = diary.echoes.length === 1 && totalEchoChars <= 45 ? 96 : 168
      if (maxH - el.scrollHeight < estimatedSlipHeight) {
        chunks.push('')
      }
    }
    const total = chunks.length
    chunks.forEach((chunk, idx) => {
      pages.push({
        diary,
        text: chunk,
        pageInDiary: idx + 1,
        totalInDiary: total,
        isFirstPage: idx === 0,
        isLastPage: idx === total - 1
      })
    })
  }
  virtualPages.value = pages
}

let resizeObserver = null
const setupResizeObserver = () => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (pageBodyMeasureWrapRef.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      recomputePages()
    })
    resizeObserver.observe(pageBodyMeasureWrapRef.value)
  }
}

watch(pageBodyMeasureWrapRef, () => {
  setupResizeObserver()
  nextTick(recomputePages)
})

watch(orderedItems, () => {
  nextTick(recomputePages)
}, { immediate: true, deep: true })

const maxIndex = computed(() => {
  const len = virtualPages.value.length
  if (len === 0) return 0
  if (isSpread.value) {
    return len % 2 === 0 ? Math.max(0, len - 2) : Math.max(0, len - 1)
  }
  return Math.max(0, len - 1)
})

const currentSpreadIndex = computed(() => Math.floor(currentIndex.value / stepSize.value))
const leftPage = computed(() => virtualPages.value[currentIndex.value] || null)
const rightPage = computed(() => (isSpread.value ? virtualPages.value[currentIndex.value + 1] || null : null))
const leftPageNumber = computed(() => currentIndex.value + 1)
const rightPageNumber = computed(() => currentIndex.value + 2)

const canGoPrev = computed(() => currentIndex.value > 0)
const canGoNext = computed(() => currentIndex.value + stepSize.value < virtualPages.value.length)

// 3D 翻页动画状态（通过 underlayIndex 分离底层与翻页层，彻底消除闪烁）
const flipState = reactive({
  active: false,
  key: 0,
  direction: 'next',
  frontPage: null,
  backPage: null,
  underlayLeftIndex: 0,
  underlayRightIndex: 1
})
let flipTimer = null

const displayLeftPage = computed(() => {
  if (!flipState.active) return leftPage.value
  return virtualPages.value[flipState.underlayLeftIndex] || null
})

const displayRightPage = computed(() => {
  if (!isSpread.value) return null
  if (!flipState.active) return rightPage.value
  return virtualPages.value[flipState.underlayRightIndex] || null
})

const displayLeftPageNumber = computed(() =>
  (flipState.active ? flipState.underlayLeftIndex : currentIndex.value) + 1
)

const displayRightPageNumber = computed(() =>
  (flipState.active ? flipState.underlayRightIndex : currentIndex.value + 1) + 1
)

const triggerFlip = (direction, targetIndex) => {
  if (flipTimer) {
    clearTimeout(flipTimer)
    flipTimer = null
  }

  const oldIdx = currentIndex.value
  const newLeft = virtualPages.value[targetIndex] || null
  const newRight = virtualPages.value[targetIndex + 1] || null
  const oldLeft = virtualPages.value[oldIdx] || null
  const oldRight = virtualPages.value[oldIdx + 1] || null

  if (isSpread.value) {
    if (direction === 'next') {
      // 下一页：左侧保留旧左页，右侧立刻露新右页；翻页叶正面=旧右页，背面=新左页
      flipState.underlayLeftIndex = oldIdx
      flipState.underlayRightIndex = targetIndex + 1
      flipState.frontPage = oldRight
      flipState.backPage = newLeft
    } else {
      // 上一页：左侧立刻露新左页，右侧保留旧右页；翻页叶正面=旧左页，背面=新右页
      flipState.underlayLeftIndex = targetIndex
      flipState.underlayRightIndex = oldIdx + 1
      flipState.frontPage = oldLeft
      flipState.backPage = newRight
    }
  } else {
    if (direction === 'next') {
      // 移动端下一页：底层直接放新页，翻页叶正面=旧页 从 0deg -> -180deg 掀开
      flipState.underlayLeftIndex = targetIndex
      flipState.frontPage = oldLeft
      flipState.backPage = oldLeft
    } else {
      // 移动端上一页：底层继续保持旧页，翻页叶正面=新页 从 -180deg -> 0deg 翻回盖住旧页
      flipState.underlayLeftIndex = oldIdx
      flipState.frontPage = newLeft
      flipState.backPage = newLeft
    }
  }

  flipState.direction = direction
  flipState.key += 1
  flipState.active = true
  currentIndex.value = targetIndex

  flipTimer = setTimeout(() => {
    flipState.active = false
    flipTimer = null
  }, 420)
}

const nextPage = () => {
  if (!canGoNext.value) return
  const target = Math.min(maxIndex.value, currentIndex.value + stepSize.value)
  triggerFlip('next', target)
}

const prevPage = () => {
  if (!canGoPrev.value) return
  const target = Math.max(0, currentIndex.value - stepSize.value)
  triggerFlip('prev', target)
}

const onSliderJump = (e) => {
  flipState.active = false
  if (flipTimer) {
    clearTimeout(flipTimer)
    flipTimer = null
  }
  let target = Number(e.target.value)
  if (isSpread.value) {
    target = target % 2 === 0 ? target : Math.max(0, target - 1)
  }
  currentIndex.value = Math.min(maxIndex.value, Math.max(0, target))
}

const toggleSortOrder = () => {
  flipState.active = false
  sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  localStorage.setItem('deardiary_book_sort', sortOrder.value)
  currentIndex.value = 0
}

const alignIndexForSpread = (idx) => {
  if (!isSpread.value) return idx
  return idx % 2 === 0 ? idx : Math.max(0, idx - 1)
}

const jumpToDate = (dateStr) => {
  if (!dateStr || virtualPages.value.length === 0) return
  const idx = virtualPages.value.findIndex(p => (p.diary.created_at || '').startsWith(dateStr))
  if (idx !== -1) {
    flipState.active = false
    currentIndex.value = alignIndexForSpread(idx)
  }
}

const jumpToFirst = () => {
  flipState.active = false
  currentIndex.value = 0
}

const jumpToLast = () => {
  flipState.active = false
  currentIndex.value = maxIndex.value
}

defineExpose({ jumpToDate, jumpToFirst, jumpToLast })

watch([() => virtualPages.value.length, isSpread], ([len]) => {
  if (len === 0) return
  if (!hasRestoredPage) {
    hasRestoredPage = true
    currentIndex.value = alignIndexForSpread(Math.min(maxIndex.value, savedPageIndex))
    return
  }
  if (currentIndex.value > maxIndex.value) {
    currentIndex.value = maxIndex.value
  } else {
    currentIndex.value = alignIndexForSpread(currentIndex.value)
  }
})

watch(currentIndex, (idx) => {
  if (!hasRestoredPage) return
  try {
    localStorage.setItem(BOOK_PAGE_KEY, String(idx))
  } catch {
    // ignore
  }
})

// 键盘左右键翻页
const handleKeydown = (e) => {
  const tag = e.target?.tagName?.toLowerCase()
  if (tag === 'input' || tag === 'textarea') return
  if (e.key === 'ArrowRight') {
    nextPage()
  } else if (e.key === 'ArrowLeft') {
    prevPage()
  }
}

// 移动端左右滑动手势翻页
let touchStartX = 0
let touchStartY = 0
const onTouchStart = (e) => {
  if (!e.touches || e.touches.length === 0) return
  touchStartX = e.touches[0].clientX
  touchStartY = e.touches[0].clientY
}
const onTouchEnd = (e) => {
  if (!e.changedTouches || e.changedTouches.length === 0) return
  const dx = e.changedTouches[0].clientX - touchStartX
  const dy = e.changedTouches[0].clientY - touchStartY
  if (Math.abs(dx) > 48 && Math.abs(dx) > Math.abs(dy) * 1.4) {
    if (dx < 0) nextPage()
    else prevPage()
  }
}

const handleResize = () => {
  windowWidth.value = window.innerWidth
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  window.addEventListener('keydown', handleKeydown)
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => {
      nextTick(recomputePages)
    })
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('keydown', handleKeydown)
  if (resizeObserver) resizeObserver.disconnect()
  if (flipTimer) clearTimeout(flipTimer)
})

// 日期与文本高亮辅助函数
const WEEKDAYS = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']

const formatPageDate = (isoStr) => {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  if (isNaN(d.getTime())) return isoStr.slice(0, 10)
  return `${d.getFullYear()}年${String(d.getMonth() + 1).padStart(2, '0')}月${String(d.getDate()).padStart(2, '0')}日`
}

const formatWeekday = (isoStr) => {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return isNaN(d.getTime()) ? '' : WEEKDAYS[d.getDay()]
}

// 若时间为 12:00:00 整（通常为批量导入默认时间），则不显示具体时间
const formatTimeOnly = (isoStr) => {
  if (!isoStr) return ''
  if (/T12:00:00(\.0+)?(Z|[+-]\d{2}:?\d{2})?$/.test(isoStr.trim())) return ''
  const d = new Date(isoStr)
  if (isNaN(d.getTime())) return ''
  if (d.getHours() === 12 && d.getMinutes() === 0 && d.getSeconds() === 0) return ''
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const splitHighlightSegments = (text, terms) => {
  if (!text) return []
  if (!terms || terms.length === 0) return [{ text, match: false }]
  const escaped = terms
    .map(t => (t || '').trim())
    .filter(Boolean)
    .map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  if (escaped.length === 0) return [{ text, match: false }]
  const regex = new RegExp(`(${escaped.join('|')})`, 'gi')
  return text.split(regex).filter(Boolean).map(part => ({
    text: part,
    match: regex.test(part)
  }))
}
</script>

<style scoped>
/* 纸页正文专用油印字体（覆盖全局 !important） */
.diary-paper-font,
.diary-paper-font * {
  font-family: 'PoZhenTypewriter', 'UnifontJP', monospace !important;
}

.book-perspective {
  perspective: 2000px;
}

.book-cover-shadow {
  box-shadow:
    0 24px 55px -15px rgba(0, 0, 0, 0.9),
    0 0 0 1px rgba(255, 255, 255, 0.03) inset;
}

/* 书签丝带燕尾缺口 */
.ribbon-tail {
  clip-path: polygon(0 0, 100% 0, 100% 100%, 50% 72%, 0 100%);
}

/* 横线纹理与 30px 行高底线对齐（文字底部压在横线上） */
.ruled-lines-dark {
  background-image: repeating-linear-gradient(
    to bottom,
    transparent 0px,
    transparent 29px,
    rgba(255, 255, 255, 0.065) 29px,
    rgba(255, 255, 255, 0.065) 30px
  );
  background-size: 100% 30px;
  background-position: 0 -2px;
}

/* 书页边缘叠层厚度纹理 */
.page-stack-dark {
  background-color: #16161d;
  background-image: repeating-linear-gradient(
    to right,
    rgba(255, 255, 255, 0.06) 0px,
    rgba(255, 255, 255, 0.06) 1px,
    transparent 1px,
    transparent 3px
  );
}

/* 右下角折角翻页提示 */
.corner-curl-dark {
  background: linear-gradient(135deg, transparent 50%, #1e1e26 50%, #2a2a36 100%);
  box-shadow: -2px -2px 5px rgba(0, 0, 0, 0.45);
  border-top-left-radius: 3px;
}

/* 3D 翻页动画 */
.flip-leaf {
  transform-style: preserve-3d;
}

.backface-hidden {
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
}

.rotate-y-180 {
  transform: rotateY(180deg);
}

/* 桌面端双页：下一页从右向左翻，上一页从左向右翻 */
.flip-spread-next {
  animation: spreadFlipNext 0.42s cubic-bezier(0.645, 0.045, 0.355, 1) forwards;
}

.flip-spread-prev {
  animation: spreadFlipPrev 0.42s cubic-bezier(0.645, 0.045, 0.355, 1) forwards;
}

/* 移动端单页：下一页从右掀开向左翻出，上一页从左侧翻回覆盖 */
.flip-mobile-next {
  animation: mobileFlipNext 0.42s cubic-bezier(0.645, 0.045, 0.355, 1) forwards;
}

.flip-mobile-prev {
  animation: mobileFlipPrev 0.42s cubic-bezier(0.645, 0.045, 0.355, 1) forwards;
}

@keyframes spreadFlipNext {
  0% { transform: rotateY(0deg); }
  100% { transform: rotateY(-180deg); }
}

@keyframes spreadFlipPrev {
  0% { transform: rotateY(0deg); }
  100% { transform: rotateY(180deg); }
}

@keyframes mobileFlipNext {
  0% { transform: rotateY(0deg); }
  100% { transform: rotateY(-180deg); }
}

@keyframes mobileFlipPrev {
  0% { transform: rotateY(-180deg); }
  100% { transform: rotateY(0deg); }
}
</style>
