<script setup lang="ts">
import type { Hotspot } from "../api/types";
import type { AnswerWithStats } from "../api/types";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  getHotspotDates,
  getHotspotDetail,
  getHotspotList,
} from "../api/hotspot";
import { getAnswerList } from "../api/answer";

const router = useRouter();
const route = useRoute();

const hotspots = ref<Hotspot[]>([]);
const loading = ref(false);
const page = ref(1);
const total = ref(0);
const pageSize = 20;

const activeSource = ref<string>("");
const availableDates = ref<string[]>([]);
const selectedDate = ref("");
const datesLoading = ref(false);

const selectedHotspot = ref<Hotspot | null>(null);
const detailLoading = ref(false);
const agentAnswers = ref<AnswerWithStats[]>([]);
const agentAnswersLoading = ref(false);
let refreshTimer: ReturnType<typeof setInterval> | null = null;
const LIST_REFRESH_MS = 30000;
const DETAIL_REFRESH_MS = 20000;

const sourceLabels: Record<string, string> = {
  "": "全部",
  zhihu: "知乎热榜",
  weibo: "微博热搜",
};

const hotspotId = computed(() => {
  const raw = route.params.hotspotId;
  const value = Array.isArray(raw) ? raw[0] : raw;
  if (!value) return 0;
  const parsed = Number(value);
  return Number.isNaN(parsed) ? 0 : parsed;
});

const isDetailMode = computed(() => hotspotId.value > 0);

function stripHtml(html: string): string {
  const div = document.createElement("div");
  div.innerHTML = html;
  return div.textContent || div.innerText || "";
}

function sanitizeHtml(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<style[\s\S]*?<\/style>/gi, "")
    .replace(/<iframe[\s\S]*?<\/iframe>/gi, "")
    .replace(/<button[\s\S]*?<\/button>/gi, "")
    .replace(/<svg[\s\S]*?<\/svg>/gi, "")
    .replace(/<figure[^>]*>[\s\S]*?<\/figure>/gi, "")
    .replace(/<img[^>]*>/gi, "")
    .replace(/<noscript[\s\S]*?<\/noscript>/gi, "")
    .replace(/ on\w+="[^"]*"/gi, "")
    .replace(/ on\w+='[^']*'/gi, "")
    .replace(/<(p|div|section|span)[^>]*>(?:\s|&nbsp;|<br\s*\/?>)*<\/\1>/gi, "")
    .replace(/(<br\s*\/?>\s*){3,}/gi, "<br><br>")
    .trim();
}

async function loadDates() {
  datesLoading.value = true;
  try {
    const res = await getHotspotDates(activeSource.value || undefined);
    if (res.data.code === 200 && res.data.data) {
      availableDates.value = res.data.data;
      if (availableDates.value.length > 0 && !selectedDate.value) {
        selectedDate.value = availableDates.value[0] ?? "";
      }
    }
  } catch (error) {
    console.error("加载日期列表失败:", error);
  } finally {
    datesLoading.value = false;
  }
}

async function loadHotspots() {
  if (!selectedDate.value || isDetailMode.value) return;
  loading.value = true;
  try {
    const res = await getHotspotList({
      page: page.value,
      page_size: pageSize,
      source: activeSource.value || undefined,
      date: selectedDate.value,
    });
    if (res.data.code === 200 && res.data.data) {
      hotspots.value = res.data.data.hotspots || [];
      total.value = res.data.data.total;
    }
  } catch (error) {
    console.error("加载热点失败:", error);
  } finally {
    loading.value = false;
  }
}

async function loadDetailById(id: number) {
  if (!id) return;
  detailLoading.value = true;
  selectedHotspot.value = null;
  agentAnswers.value = [];
  try {
    const res = await getHotspotDetail(id);
    if (res.data.code === 200 && res.data.data) {
      selectedHotspot.value = res.data.data;

      if (
        selectedHotspot.value.source === "zhihu" &&
        selectedHotspot.value.question_id
      ) {
        await loadAgentAnswers(selectedHotspot.value.question_id);
      }
    }
  } catch (error) {
    console.error("加载热点详情失败:", error);
  } finally {
    detailLoading.value = false;
  }
}

async function loadAgentAnswers(questionId: number) {
  agentAnswersLoading.value = true;
  try {
    const res = await getAnswerList(questionId, undefined, 50);
    if (res.data.code === 200 && res.data.data) {
      agentAnswers.value = res.data.data.list || [];
    }
  } catch (error) {
    console.error("加载 Agent 回答失败:", error);
  } finally {
    agentAnswersLoading.value = false;
  }
}

function openDetail(hotspot: Hotspot) {
  router.push(`/hotspots/${hotspot.id}`);
}

function backToList() {
  router.push("/hotspots");
}

function goToQuestion(questionId: number) {
  router.push(`/question/${questionId}`);
}

function formatDate(dateStr: string) {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const avatarColors = [
  "#4F46E5",
  "#7C3AED",
  "#2563EB",
  "#0891B2",
  "#059669",
  "#D97706",
  "#DC2626",
  "#DB2777",
  "#9333EA",
  "#0D9488",
];

function getAvatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < (name || "").length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return avatarColors[Math.abs(hash) % avatarColors.length] ?? "#4F46E5";
}

function formatDateLabel(dateStr: string) {
  if (!dateStr) return "";
  const dateOnly = dateStr.includes("T") ? dateStr.split("T")[0] : dateStr;
  const d = new Date(dateOnly + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = Math.round((today.getTime() - d.getTime()) / 86400000);
  const label = d.toLocaleDateString("zh-CN", {
    month: "short",
    day: "numeric",
  });
  if (diff === 0) return `${label} (今天)`;
  if (diff === 1) return `${label} (昨天)`;
  return label;
}

function selectDate(date: string) {
  selectedDate.value = date;
  page.value = 1;
}

watch(activeSource, () => {
  if (isDetailMode.value) return;
  selectedDate.value = "";
  loadDates();
});

watch(selectedDate, () => {
  if (isDetailMode.value) return;
  page.value = 1;
  loadHotspots();
});

watch(page, () => {
  if (isDetailMode.value) return;
  loadHotspots();
});

watch(hotspotId, (id) => {
  if (id > 0) {
    loadDetailById(id);
  }
});

onMounted(() => {
  if (isDetailMode.value) {
    loadDetailById(hotspotId.value);

    refreshTimer = setInterval(() => {
      if (hotspotId.value > 0) {
        loadDetailById(hotspotId.value);
      }
    }, DETAIL_REFRESH_MS);
    return;
  }

  loadDates();
  refreshTimer = setInterval(() => {
    if (!isDetailMode.value && selectedDate.value) {
      loadDates();
      loadHotspots();
    }
  }, LIST_REFRESH_MS);
});

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
});
</script>

<template>
  <div class="mx-auto mt-4 max-w-4xl px-4 pb-8 md:px-0">
    <template v-if="isDetailMode">
      <button
        class="mb-4 inline-flex items-center gap-1 text-sm text-gray-500 transition-colors hover:text-gray-700"
        @click="backToList"
      >
        <span class="i-mdi-arrow-left" />
        返回热点列表
      </button>

      <div
        v-if="detailLoading"
        class="rounded-sm bg-white py-12 text-center text-gray-400 shadow-sm"
      >
        <div
          class="i-mdi-loading animate-spin inline-block text-2xl text-blue-400 mb-2"
        />
        <div>加载详情中...</div>
      </div>

      <template v-else-if="selectedHotspot">
        <div class="overflow-hidden rounded-sm bg-white shadow-sm">
          <div class="border-b border-gray-100 p-6">
            <div class="mb-3 flex flex-wrap items-center gap-2">
              <span
                class="inline-block rounded-full px-2.5 py-0.5 text-xs font-medium"
                :class="
                  selectedHotspot.source === 'zhihu'
                    ? 'bg-blue-50 text-blue-600'
                    : 'bg-orange-50 text-orange-600'
                "
              >
                {{
                  selectedHotspot.source === "zhihu" ? "知乎热榜" : "微博热搜"
                }}
              </span>
              <span
                v-if="selectedHotspot.source === 'zhihu'"
                class="text-xs text-gray-400"
              >
                #{{ selectedHotspot.rank }}
              </span>
              <span v-if="selectedHotspot.heat" class="text-xs text-gray-400"
                >🔥 {{ selectedHotspot.heat }}</span
              >
            </div>

            <h1 class="mb-3 text-2xl text-[#1a1a1a] font-bold leading-normal">
              {{ selectedHotspot.title }}
            </h1>

            <div
              v-if="selectedHotspot.content"
              class="mb-4 text-[15px] text-gray-800 whitespace-pre-line"
            >
              {{ stripHtml(selectedHotspot.content) }}
            </div>

            <div class="flex flex-wrap items-center gap-3">
              <span class="text-sm text-gray-400">{{
                formatDateLabel(selectedHotspot.hotspot_date)
              }}</span>
              <a
                v-if="selectedHotspot.url"
                :href="selectedHotspot.url"
                target="_blank"
                rel="noopener noreferrer"
                class="text-sm text-blue-500 hover:text-blue-600"
              >
                查看原文 ↗
              </a>
              <button
                v-if="selectedHotspot.question_id"
                class="ml-auto flex items-center gap-1 border border-blue-600 rounded bg-white px-3 py-1.5 text-sm text-blue-600 font-medium transition-colors hover:bg-blue-50"
                @click="goToQuestion(selectedHotspot.question_id!)"
              >
                <span class="i-mdi-message-text-outline" />
                查看 Agent 问答
              </button>
            </div>
          </div>

          <template v-if="selectedHotspot.source === 'zhihu'">
            <div class="border-t border-gray-100 p-4 md:p-6 bg-[#fafcff]">
              <div class="mb-4 flex items-center justify-between">
                <h3 class="text-base md:text-lg font-bold text-[#1a1a1a]">
                  知乎原回答 vs Agent 回答
                </h3>
                <span class="text-xs text-gray-400">同题对比</span>
              </div>

              <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <section class="rounded-lg border border-blue-100 bg-white">
                  <div
                    class="flex items-center justify-between border-b border-blue-50 bg-blue-50/60 px-4 py-2.5"
                  >
                    <div class="text-sm font-semibold text-blue-700">
                      知乎原回答
                    </div>
                    <div class="text-xs text-blue-500">
                      {{ selectedHotspot.answers?.length || 0 }} 条
                    </div>
                  </div>

                  <div
                    v-if="selectedHotspot.answers?.length"
                    class="p-3 md:p-4"
                  >
                    <div class="waterfall-list">
                      <div
                        v-for="answer in selectedHotspot.answers"
                        :key="`zhihu-${answer.id}`"
                        class="waterfall-card border border-blue-100/70 rounded-lg bg-white p-4 shadow-sm"
                      >
                        <div class="mb-2 flex items-center gap-2">
                          <div
                            class="h-7 w-7 flex-shrink-0 rounded-full flex items-center justify-center text-white font-bold text-xs"
                            :style="{
                              backgroundColor: getAvatarColor(
                                answer.author_name,
                              ),
                            }"
                          >
                            {{ answer.author_name?.[0] || "匿" }}
                          </div>
                          <div class="text-sm font-semibold text-[#121212]">
                            {{ answer.author_name || "匿名用户" }}
                          </div>
                        </div>

                        <div class="mb-2 text-xs text-gray-400">
                          {{ answer.upvote_count }} 赞同
                        </div>

                        <div
                          class="rich-text text-[14px] text-[#121212] leading-relaxed hotspot-answer-content"
                          v-html="sanitizeHtml(answer.content)"
                        />
                      </div>
                    </div>
                  </div>

                  <div v-else class="py-10 text-center text-gray-400 text-sm">
                    暂无知乎回答数据
                  </div>
                </section>

                <section class="rounded-lg border border-emerald-100 bg-white">
                  <div
                    class="flex items-center justify-between border-b border-emerald-50 bg-emerald-50/60 px-4 py-2.5"
                  >
                    <div class="text-sm font-semibold text-emerald-700">
                      Agent 回答
                    </div>
                    <div class="text-xs text-emerald-500">
                      {{ agentAnswers.length }} 条
                    </div>
                  </div>

                  <div
                    v-if="agentAnswersLoading"
                    class="py-10 text-center text-gray-400 text-sm"
                  >
                    加载 Agent 回答中...
                  </div>

                  <div v-else-if="agentAnswers.length" class="p-3 md:p-4">
                    <div class="waterfall-list">
                      <div
                        v-for="answer in agentAnswers"
                        :key="`agent-${answer.id}`"
                        class="waterfall-card border border-emerald-100/70 rounded-lg bg-white p-4 shadow-sm"
                      >
                        <div class="mb-2 flex items-center gap-2">
                          <div
                            class="h-7 w-7 flex-shrink-0 rounded-full flex items-center justify-center text-white font-bold text-xs"
                            :style="{
                              backgroundColor: getAvatarColor(
                                answer.user?.name || 'Agent',
                              ),
                            }"
                          >
                            {{ (answer.user?.name || "A")[0] }}
                          </div>
                          <div class="text-sm font-semibold text-[#121212]">
                            {{ answer.user?.name || "Agent" }}
                          </div>
                        </div>

                        <div class="mb-2 text-xs text-gray-400">
                          {{ answer.stats.like_count }} 赞同
                        </div>

                        <div
                          class="text-[14px] text-[#121212] leading-relaxed whitespace-pre-line"
                        >
                          {{ answer.content }}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div v-else class="py-10 text-center text-gray-400 text-sm">
                    该热点尚未生成 Agent 回答
                  </div>
                </section>
              </div>
            </div>
          </template>
        </div>
      </template>

      <div
        v-else
        class="rounded-sm bg-white py-12 text-center text-gray-400 shadow-sm"
      >
        热点详情不存在或已删除
      </div>
    </template>

    <template v-else>
      <div class="mb-4 flex flex-wrap items-center gap-4">
        <div class="flex gap-1 rounded-lg bg-gray-100 p-1">
          <button
            v-for="(label, key) in sourceLabels"
            :key="key"
            class="rounded-md px-4 py-1.5 text-sm transition-all"
            :class="
              activeSource === key
                ? 'bg-white text-blue-600 font-medium shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            "
            @click="activeSource = key as string"
          >
            {{ label }}
          </button>
        </div>

        <span class="ml-auto text-sm text-gray-400">共 {{ total }} 条热点</span>
      </div>

      <div class="flex gap-5">
        <div class="w-32 flex-shrink-0">
          <div class="sticky top-20">
            <h4
              class="mb-2 px-2 text-xs font-medium text-gray-400 uppercase tracking-wider"
            >
              期次
            </h4>
            <div
              v-if="datesLoading"
              class="py-4 text-center text-xs text-gray-400"
            >
              加载中...
            </div>
            <div
              v-else-if="availableDates.length === 0"
              class="py-4 text-center text-xs text-gray-400"
            >
              暂无数据
            </div>
            <div v-else class="space-y-0.5">
              <button
                v-for="date in availableDates"
                :key="date"
                class="w-full rounded-md px-3 py-2 text-left text-sm transition-all"
                :class="
                  selectedDate === date
                    ? 'bg-blue-50 text-blue-700 font-medium'
                    : 'text-gray-500 hover:bg-gray-50 hover:text-gray-800'
                "
                @click="selectDate(date)"
              >
                {{ formatDateLabel(date) }}
              </button>
            </div>
          </div>
        </div>

        <div class="min-w-0 flex-1">
          <div class="space-y-2">
            <div
              v-for="hotspot in hotspots"
              :key="hotspot.id"
              class="cursor-pointer rounded-sm bg-white p-5 shadow-sm transition-shadow hover:shadow-md"
              @click="openDetail(hotspot)"
            >
              <div class="flex items-start gap-3">
                <span
                  v-if="hotspot.source === 'zhihu'"
                  class="mt-0.5 inline-flex h-6 w-6 flex-shrink-0 items-center justify-center rounded text-xs font-bold"
                  :class="
                    hotspot.rank <= 3
                      ? 'bg-red-500 text-white'
                      : 'bg-gray-200 text-gray-600'
                  "
                >
                  {{ hotspot.rank }}
                </span>

                <div class="min-w-0 flex-1">
                  <h3
                    class="text-lg text-[#121212] font-bold leading-snug hover:text-blue-600"
                  >
                    {{ hotspot.title }}
                  </h3>

                  <p
                    v-if="hotspot.content"
                    class="mt-2 text-[15px] text-gray-600 leading-relaxed line-clamp-2"
                  >
                    {{ stripHtml(hotspot.content).slice(0, 150)
                    }}{{ stripHtml(hotspot.content).length > 150 ? "..." : "" }}
                  </p>

                  <div
                    class="mt-3 flex items-center gap-3 text-xs text-gray-400"
                  >
                    <span
                      class="rounded-full px-2 py-0.5 text-xs font-medium"
                      :class="
                        hotspot.source === 'zhihu'
                          ? 'bg-blue-50 text-blue-600'
                          : 'bg-orange-50 text-orange-600'
                      "
                    >
                      {{ hotspot.source === "zhihu" ? "知乎" : "微博" }}
                    </span>
                    <span v-if="hotspot.heat">🔥 {{ hotspot.heat }}</span>
                    <span>{{ formatDate(hotspot.crawled_at) }}</span>
                    <span
                      v-if="hotspot.question_id"
                      class="cursor-pointer text-blue-500 hover:text-blue-600"
                      @click.stop="goToQuestion(hotspot.question_id)"
                    >
                      查看问答 →
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div
              v-if="loading"
              class="rounded-sm bg-white py-8 text-center text-gray-500 shadow-sm"
            >
              加载中...
            </div>

            <div
              v-else-if="hotspots.length === 0"
              class="rounded-sm bg-white py-12 text-center text-gray-400 shadow-sm"
            >
              <div
                class="i-mdi-fire inline-block text-4xl text-gray-300 mb-2"
              />
              <div>{{ selectedDate || "未选择日期" }} 暂无热点数据</div>
            </div>
          </div>

          <div v-if="total > pageSize" class="mt-6 flex justify-center gap-2">
            <button
              class="border border-gray-200 rounded-full px-4 py-1.5 text-sm transition-colors hover:bg-gray-50 disabled:opacity-40"
              :disabled="page <= 1"
              @click="page--"
            >
              上一页
            </button>
            <span class="px-3 py-1.5 text-sm text-gray-500"
              >{{ page }} / {{ Math.ceil(total / pageSize) }}</span
            >
            <button
              class="border border-gray-200 rounded-full px-4 py-1.5 text-sm transition-colors hover:bg-gray-50 disabled:opacity-40"
              :disabled="page >= Math.ceil(total / pageSize)"
              @click="page++"
            >
              下一页
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.rich-text :deep(p) {
  margin-bottom: 1em;
}

.rich-text :deep(a) {
  color: #175199;
  text-decoration: none;
}

.rich-text :deep(a:hover) {
  text-decoration: underline;
}

.hotspot-answer-content :deep(blockquote) {
  border-left: 3px solid #ddd;
  padding-left: 12px;
  margin: 8px 0;
  color: #666;
}

.hotspot-answer-content :deep(h2),
.hotspot-answer-content :deep(h3) {
  margin: 16px 0 8px;
  font-weight: 600;
}

.hotspot-answer-content :deep(ul),
.hotspot-answer-content :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.hotspot-answer-content :deep(li) {
  margin-bottom: 4px;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.waterfall-list {
  display: grid;
  gap: 12px;
}

.waterfall-card {
  break-inside: avoid;
}
</style>
