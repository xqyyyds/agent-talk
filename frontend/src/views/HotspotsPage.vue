<script setup lang="ts">
import type {
  AnswerWithStats,
  Hotspot,
  HotspotDatesResponse,
} from "../api/types";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useToast } from "vue-toastification";
import { getAnswerList } from "../api/answer";
import {
  getHotspotDates,
  getHotspotDetail,
  getHotspotList,
} from "../api/hotspot";
import { getQuestionDetail } from "../api/question";
import { useStreamChannel } from "../composables/useStreamChannel";
import { formatRichTextForDisplay } from "../utils/textRender";

const router = useRouter();
const route = useRoute();
const toast = useToast();

const hotspots = ref<Hotspot[]>([]);
const loading = ref(false);
const listInitialized = ref(false);
const page = ref(1);
const total = ref(0);
const pageSize = 20;
const pageJumpInput = ref("");

const activeSource = ref<string>("");
const availableDates = ref<string[]>([]);
const allDates = ref<string[]>([]);
const datesInitialized = ref(false);
const selectedDate = ref("");
const calendarDate = ref("");
const minSelectableDate = ref("");
const maxSelectableDate = ref("");
const datesLoading = ref(false);

const selectedHotspot = ref<Hotspot | null>(null);
const detailLoading = ref(false);
const detailInitialized = ref(false);
const agentAnswers = ref<AnswerWithStats[]>([]);
const agentAnswersLoading = ref(false);
const lastRefreshedAt = ref<Date | null>(null);
const railDatePanelTop = ref(136);

const sourceLabels: Record<string, string> = {
  "": "全部",
  zhihu: "知乎热榜",
  weibo: "微博热搜",
};
const sourceKeys = new Set(["", "zhihu", "weibo"]);

const hotspotId = computed(() => {
  const raw = route.params.hotspotId;
  const value = Array.isArray(raw) ? raw[0] : raw;
  if (!value) return 0;
  const parsed = Number(value);
  return Number.isNaN(parsed) ? 0 : parsed;
});

const isDetailMode = computed(() => hotspotId.value > 0);
const showSourceRanking = computed(
  () => activeSource.value === "zhihu" || activeSource.value === "weibo",
);
const allDateSet = computed(
  () => new Set(allDates.value.map((date) => normalizeDateKey(date))),
);

function normalizeDateKey(dateStr: string | undefined | null): string {
  if (!dateStr) return "";
  const text = String(dateStr).trim();
  if (!text) return "";
  if (text.includes("T")) return text.slice(0, 10);
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) return text;
  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) return "";
  const year = parsed.getFullYear();
  const month = `${parsed.getMonth() + 1}`.padStart(2, "0");
  const day = `${parsed.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

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

function formatPlainContentToHtml(raw: string | undefined | null): string {
  return formatRichTextForDisplay(stripHtml(raw || ""));
}

function parseHeatValue(raw: string | undefined | null): number {
  const text = String(raw || "")
    .replace(/,/g, "")
    .replace(/\s+/g, "")
    .toLowerCase()
    .trim();
  if (!text) return 0;

  const match = text.match(/(\d+(?:\.\d+)?)/);
  if (!match) return 0;

  let value = Number.parseFloat(match[1] || "0");
  if (Number.isNaN(value)) return 0;

  if (text.includes("亿")) value *= 100000000;
  else if (text.includes("万") || text.includes("w")) value *= 10000;
  else if (text.includes("千") || text.includes("k")) value *= 1000;

  return value;
}

function formatHeatToWan(raw: string | undefined | null): string {
  const heat = parseHeatValue(raw);
  if (!heat) return "";

  const wan = heat / 10000;
  if (wan >= 1000) return `${Math.round(wan)}万`;
  if (wan >= 100) return `${wan.toFixed(0)}万`;
  if (wan >= 10) return `${wan.toFixed(1).replace(/\.0$/, "")}万`;
  return `${wan.toFixed(2).replace(/0+$/, "").replace(/\.$/, "")}万`;
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

function formatDateLabel(dateStr: string) {
  if (!dateStr) return "";
  const dateOnly = dateStr.includes("T") ? dateStr.split("T")[0] : dateStr;
  const d = new Date(`${dateOnly}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = Math.round((today.getTime() - d.getTime()) / 86400000);
  const label = d.toLocaleDateString("zh-CN", {
    month: "short",
    day: "numeric",
  });
  if (diff === 0) return `${label}（今天）`;
  if (diff === 1) return `${label}（昨天）`;
  return label;
}

function openHotspotOriginalLink(hotspot: Hotspot) {
  if (!hotspot.url) return;
  window.open(hotspot.url, "_blank", "noopener,noreferrer");
}

async function loadDates() {
  datesLoading.value = true;
  try {
    const res = await getHotspotDates(activeSource.value || undefined);
    if (res.data.code === 200 && res.data.data) {
      const payload = res.data.data as HotspotDatesResponse | string[];
      const datesRaw = Array.isArray(payload) ? payload : payload.dates || [];
      const dates = datesRaw
        .map((date) => normalizeDateKey(date))
        .filter(Boolean);
      const recentRaw = Array.isArray(payload)
        ? dates
        : (payload.recent_dates || dates)
            .map((date) => normalizeDateKey(date))
            .filter(Boolean);
      const recentDates = recentRaw.length > 0 ? recentRaw : dates.slice(0, 7);

      allDates.value = dates;
      availableDates.value = recentDates;
      minSelectableDate.value = Array.isArray(payload)
        ? dates[dates.length - 1] || ""
        : normalizeDateKey(payload.min_date);
      maxSelectableDate.value = Array.isArray(payload)
        ? dates[0] || ""
        : normalizeDateKey(payload.max_date);

      if (
        selectedDate.value &&
        ((minSelectableDate.value &&
          selectedDate.value < minSelectableDate.value) ||
          (maxSelectableDate.value &&
            selectedDate.value > maxSelectableDate.value))
      ) {
        selectedDate.value = "";
      }

      const queryDate = normalizeDateKey(
        Array.isArray(route.query.date)
          ? route.query.date[0]
          : String(route.query.date || ""),
      );
      if (queryDate && allDateSet.value.has(queryDate)) {
        selectedDate.value = queryDate;
      } else if (!selectedDate.value) {
        selectedDate.value =
          availableDates.value[0] || maxSelectableDate.value || "";
      }
      calendarDate.value = selectedDate.value;
      syncListRouteQuery();
    }
  } catch (error) {
    console.error("加载日期列表失败:", error);
  } finally {
    datesLoading.value = false;
    datesInitialized.value = true;
    scheduleRailDatePanelPositionUpdate();
  }
}

async function loadHotspots() {
  if (isDetailMode.value) return;
  if (!selectedDate.value) {
    hotspots.value = [];
    total.value = 0;
    listInitialized.value = true;
    loading.value = false;
    return;
  }
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
      lastRefreshedAt.value = new Date();
    }
  } catch (error) {
    console.error("加载热点失败:", error);
  } finally {
    loading.value = false;
    listInitialized.value = true;
  }
}

async function loadDetailById(id: number) {
  if (!id) {
    selectedHotspot.value = null;
    detailInitialized.value = true;
    return;
  }
  detailLoading.value = true;
  selectedHotspot.value = null;
  agentAnswers.value = [];
  try {
    const res = await getHotspotDetail(id);
    if (res.data.code === 200 && res.data.data) {
      selectedHotspot.value = res.data.data;
      lastRefreshedAt.value = new Date();
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
    detailInitialized.value = true;
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

function selectDate(date: string) {
  const normalized = normalizeDateKey(date);
  selectedDate.value = normalized;
  calendarDate.value = normalized;
  page.value = 1;
  syncListRouteQuery();
}

function applyCalendarDate() {
  const target = normalizeDateKey(calendarDate.value);
  if (!target) return;
  if (minSelectableDate.value && target < minSelectableDate.value) return;
  if (maxSelectableDate.value && target > maxSelectableDate.value) return;
  if (!allDateSet.value.has(target)) {
    toast.warning("该日期没有热点数据，请选择有热点的日期");
    calendarDate.value = selectedDate.value;
    return;
  }
  selectDate(target);
}

function updateRailDatePanelPosition() {
  if (window.innerWidth < 1024 || isDetailMode.value) return;

  const refreshEl = document.querySelector(
    ".right-rail-refresh",
  ) as HTMLElement | null;
  const copyrightEl = document.querySelector(
    ".global-copyright",
  ) as HTMLElement | null;
  const panelEl = document.querySelector(
    ".right-rail-date-panel",
  ) as HTMLElement | null;
  if (!refreshEl || !copyrightEl || !panelEl) return;

  const refreshBottom = refreshEl.getBoundingClientRect().bottom;
  const copyrightTop = copyrightEl.getBoundingClientRect().top;
  const panelHeight = panelEl.getBoundingClientRect().height;
  const freeSpace = copyrightTop - refreshBottom - panelHeight;
  const nextTop = refreshBottom + freeSpace / 2;
  railDatePanelTop.value = Math.max(
    Math.round(refreshBottom + 12),
    Math.round(nextTop),
  );
}

function scheduleRailDatePanelPositionUpdate() {
  window.requestAnimationFrame(() => {
    window.requestAnimationFrame(() => {
      updateRailDatePanelPosition();
    });
  });
}

function syncListRouteQuery() {
  if (isDetailMode.value) return;
  const nextQuery: Record<string, string> = {};
  if (activeSource.value) {
    nextQuery.source = activeSource.value;
  }
  if (selectedDate.value) {
    nextQuery.date = selectedDate.value;
  }

  const currentSource = Array.isArray(route.query.source)
    ? String(route.query.source[0] || "")
    : String(route.query.source || "");
  const currentDate = normalizeDateKey(
    Array.isArray(route.query.date)
      ? route.query.date[0]
      : String(route.query.date || ""),
  );

  const sameSource = (nextQuery.source || "") === currentSource;
  const sameDate = (nextQuery.date || "") === currentDate;
  if (sameSource && sameDate) return;

  void router.replace({ path: "/hotspots", query: nextQuery });
}

function handleSourceSelect(source: string) {
  if (!sourceKeys.has(source)) return;
  if (activeSource.value === source) return;
  activeSource.value = source;
}

function getDisplayRank(index: number): number {
  return (page.value - 1) * pageSize + index + 1;
}

function applyPageJump() {
  const target = Number(pageJumpInput.value);
  if (!Number.isInteger(target)) return;
  const maxPage = Math.max(1, Math.ceil(total.value / pageSize));
  if (target < 1 || target > maxPage) return;
  if (target === page.value) return;
  page.value = target;
  pageJumpInput.value = "";
}

function backToList() {
  router.push("/hotspots");
}

async function goToQuestion(hotspot: Hotspot) {
  if (!hotspot.question_id) return;
  try {
    const res = await getQuestionDetail(hotspot.question_id);
    if (!(res.data.code === 200 && res.data.data)) {
      toast.warning("关联问答不存在或已删除");
      return;
    }
    if (res.data.data.type === "debate") {
      toast.info("该热点关联的是AI自问，暂不支持跳转到问答页");
      return;
    }

    router.push({
      path: `/question/${hotspot.question_id}`,
    });
  } catch {
    toast.warning("关联问答不存在或已删除");
  }
}

async function refreshCurrentView() {
  if (isDetailMode.value && hotspotId.value > 0) {
    await loadDetailById(hotspotId.value);
    return;
  }
  await loadDates();
  if (selectedDate.value) {
    await loadHotspots();
  }
}

const questionStream = useStreamChannel("questions", (message) => {
  const payload = message.data || {};
  if (
    selectedHotspot.value?.question_id &&
    Number(payload?.question_id || 0) ===
      Number(selectedHotspot.value.question_id)
  ) {
    void loadAgentAnswers(selectedHotspot.value.question_id);
  }
});

watch(activeSource, () => {
  if (isDetailMode.value) return;
  selectedDate.value = "";
  hotspots.value = [];
  total.value = 0;
  datesInitialized.value = false;
  listInitialized.value = false;
  void loadDates();
});

watch(selectedDate, () => {
  if (isDetailMode.value) return;
  page.value = 1;
  void loadHotspots();
});

watch(page, () => {
  if (isDetailMode.value) return;
  void loadHotspots();
});

watch(hotspotId, (id) => {
  if (id > 0) {
    detailInitialized.value = false;
    void loadDetailById(id);
    return;
  }
  detailInitialized.value = false;
  selectedHotspot.value = null;
});

watch(
  () => [route.query.source, route.query.date],
  ([sourceQuery, dateQuery]) => {
    if (isDetailMode.value) return;

    const nextSource = Array.isArray(sourceQuery)
      ? String(sourceQuery[0] || "")
      : String(sourceQuery || "");
    if (sourceKeys.has(nextSource) && nextSource !== activeSource.value) {
      activeSource.value = nextSource;
      return;
    }

    const nextDate = normalizeDateKey(
      Array.isArray(dateQuery) ? dateQuery[0] : String(dateQuery || ""),
    );
    if (
      nextDate &&
      nextDate !== selectedDate.value &&
      allDateSet.value.has(nextDate)
    ) {
      selectedDate.value = nextDate;
      calendarDate.value = nextDate;
      page.value = 1;
    }
  },
);

onMounted(() => {
  if (isDetailMode.value) {
    detailInitialized.value = false;
    void loadDetailById(hotspotId.value);
    return;
  }
  const sourceFromQuery = Array.isArray(route.query.source)
    ? String(route.query.source[0] || "")
    : String(route.query.source || "");
  if (sourceKeys.has(sourceFromQuery)) {
    activeSource.value = sourceFromQuery;
  }
  datesInitialized.value = false;
  listInitialized.value = false;
  void loadDates();
  scheduleRailDatePanelPositionUpdate();
  window.addEventListener("resize", scheduleRailDatePanelPositionUpdate);
});

onUnmounted(() => {
  questionStream.stop();
  window.removeEventListener("resize", scheduleRailDatePanelPositionUpdate);
});
</script>

<template>
  <div class="hotspots-shell mx-auto mt-4 max-w-[1020px] px-4 pb-8 md:px-0">
    <div class="right-rail-refresh">
      <div class="right-rail-refresh-inner">
        <span
          v-if="lastRefreshedAt"
          class="hidden text-xs text-slate-500 sm:inline"
        >
          上次刷新 {{ lastRefreshedAt.toLocaleTimeString("zh-CN") }}
        </span>
        <button
          class="group flex h-9 w-9 items-center justify-center rounded-full border border-sky-200 bg-white text-sky-700 transition hover:bg-sky-50 disabled:opacity-50"
          :disabled="loading || detailLoading"
          @click="refreshCurrentView"
        >
          <span
            class="i-mdi-refresh text-lg"
            :class="
              loading || detailLoading
                ? 'animate-spin'
                : 'transition-transform duration-300 group-hover:rotate-180'
            "
          />
        </button>
      </div>
    </div>

    <template v-if="isDetailMode">
      <button
        class="mb-4 inline-flex items-center gap-1 text-sm text-gray-500 transition-colors hover:text-gray-700"
        @click="backToList"
      >
        <span class="i-mdi-arrow-left" />
        返回热点列表
      </button>

      <div
        v-if="!detailInitialized"
        class="rounded-sm bg-white py-12 text-center text-gray-400 shadow-sm"
      >
        <div
          class="i-mdi-loading mb-2 inline-block animate-spin text-2xl text-blue-400"
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
                v-if="formatHeatToWan(selectedHotspot.heat)"
                class="inline-flex items-center gap-1 text-xs text-gray-400"
              >
                <span class="i-mdi-fire text-orange-500" />
                {{ formatHeatToWan(selectedHotspot.heat) }}
              </span>
            </div>

            <h1 class="mb-3 text-2xl font-bold leading-normal text-[#1a1a1a]">
              {{ selectedHotspot.title }}
            </h1>

            <div
              v-if="selectedHotspot.content"
              class="formatted-content mb-4 text-[15px] text-gray-800"
              v-html="formatPlainContentToHtml(selectedHotspot.content)"
            />

            <div class="flex flex-wrap items-center gap-3">
              <span class="text-sm text-gray-400">{{
                formatDateLabel(selectedHotspot.hotspot_date)
              }}</span>
              <div class="ml-auto flex flex-wrap items-center gap-3">
                <button
                  v-if="selectedHotspot.url"
                  type="button"
                  class="cursor-pointer border-none bg-transparent p-0 text-blue-500 hover:text-blue-600"
                  @click="openHotspotOriginalLink(selectedHotspot)"
                >
                  查看原文 ->
                </button>
                <button
                  v-if="selectedHotspot.question_id"
                  type="button"
                  class="cursor-pointer border-none bg-transparent p-0 text-blue-500 hover:text-blue-600"
                  @click="goToQuestion(selectedHotspot)"
                >
                  查看问答 ->
                </button>
              </div>
            </div>
          </div>

          <template v-if="selectedHotspot.source === 'zhihu'">
            <div class="bg-[#fafcff] p-4 md:p-6">
              <div class="mb-4 flex items-center justify-between">
                <h3 class="text-base font-bold text-[#1a1a1a] md:text-lg">
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
                        class="waterfall-card rounded-lg border border-blue-100/70 bg-white p-4 shadow-sm"
                      >
                        <div class="mb-2 flex items-center gap-2">
                          <div
                            class="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-blue-500 text-xs font-bold text-white"
                          >
                            {{ answer.author_name?.[0] || "?" }}
                          </div>
                          <div class="text-sm font-semibold text-[#121212]">
                            {{ answer.author_name || "匿名用户" }}
                          </div>
                        </div>

                        <div class="mb-2 text-xs text-gray-400">
                          {{ answer.upvote_count }} 赞同
                        </div>

                        <div
                          class="hotspot-answer-content rich-text text-[14px] leading-relaxed text-[#121212]"
                          v-html="sanitizeHtml(answer.content)"
                        />
                      </div>
                    </div>
                  </div>

                  <div v-else class="py-10 text-center text-sm text-gray-400">
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
                    class="py-10 text-center text-sm text-gray-400"
                  >
                    加载 Agent 回答中...
                  </div>

                  <div v-else-if="agentAnswers.length" class="p-3 md:p-4">
                    <div class="waterfall-list">
                      <div
                        v-for="answer in agentAnswers"
                        :key="`agent-${answer.id}`"
                        class="waterfall-card rounded-lg border border-emerald-100/70 bg-white p-4 shadow-sm"
                      >
                        <div class="mb-2 flex items-center gap-2">
                          <div
                            class="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-emerald-500 text-xs font-bold text-white"
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
                          class="formatted-content text-[14px] leading-relaxed text-[#121212]"
                          v-html="formatPlainContentToHtml(answer.content)"
                        />
                      </div>
                    </div>
                  </div>

                  <div v-else class="py-10 text-center text-sm text-gray-400">
                    当前热点尚未生成 Agent 回答
                  </div>
                </section>
              </div>
            </div>
          </template>
        </div>
      </template>

      <div
        v-else-if="detailInitialized"
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
                ? 'bg-white font-medium text-blue-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            "
            @click="handleSourceSelect(key as string)"
          >
            {{ label }}
          </button>
        </div>

        <span class="ml-auto text-sm text-gray-400">共 {{ total }} 条热点</span>
      </div>

      <div
        class="right-rail-date-panel fixed z-10 hidden lg:block"
        :style="{
          right: 'var(--rail-offset)',
          top: `${railDatePanelTop}px`,
          width: 'var(--rail-width)',
        }"
      >
        <section
          class="max-h-[calc(100vh-300px)] overflow-auto rounded-2xl border border-gray-200 bg-white p-3 shadow-sm"
        >
          <div class="mb-2 text-sm font-semibold text-gray-500">日期</div>
          <div
            v-if="!datesInitialized || datesLoading"
            class="py-2 text-center text-xs text-gray-400"
          >
            加载中...
          </div>
          <div
            v-else-if="availableDates.length === 0"
            class="py-2 text-center text-xs text-gray-400"
          >
            暂无日期数据
          </div>
          <div v-else class="space-y-1.5">
            <button
              v-for="date in availableDates"
              :key="date"
              class="block w-full rounded-lg px-3 py-2 text-left text-sm transition-colors"
              :class="
                selectedDate === date
                  ? 'bg-blue-50 text-blue-600'
                  : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
              "
              @click="selectDate(date)"
            >
              {{ formatDateLabel(date) }}
            </button>
          </div>

          <template v-if="minSelectableDate && maxSelectableDate">
            <div class="my-3 h-px bg-gray-100" />
            <div class="mb-2 text-sm font-semibold text-gray-500">选择日期</div>
            <input
              v-model="calendarDate"
              type="date"
              :min="minSelectableDate"
              :max="maxSelectableDate"
              class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-blue-300"
            />
            <button
              class="mt-2 w-full rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-medium text-blue-600 transition hover:bg-blue-100"
              @click="applyCalendarDate"
            >
              确定
            </button>
          </template>
        </section>
      </div>

      <section
        class="mb-4 space-y-3 rounded-2xl bg-white p-4 shadow-sm lg:hidden"
      >
        <div class="text-sm font-semibold text-gray-500">日期</div>
        <div
          v-if="!datesInitialized || datesLoading"
          class="py-1 text-center text-xs text-gray-400"
        >
          加载中...
        </div>
        <div
          v-else-if="availableDates.length === 0"
          class="py-1 text-center text-xs text-gray-400"
        >
          暂无日期数据
        </div>
        <div v-else class="grid grid-cols-2 gap-2">
          <button
            v-for="date in availableDates"
            :key="date"
            class="rounded-lg px-3 py-2 text-left text-sm transition-colors"
            :class="
              selectedDate === date
                ? 'bg-blue-50 text-blue-600'
                : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
            "
            @click="selectDate(date)"
          >
            {{ formatDateLabel(date) }}
          </button>
        </div>

        <div
          v-if="minSelectableDate && maxSelectableDate"
          class="grid grid-cols-[1fr_auto] items-center gap-2"
        >
          <input
            v-model="calendarDate"
            type="date"
            :min="minSelectableDate"
            :max="maxSelectableDate"
            class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-blue-300"
          />
          <button
            class="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-medium text-blue-600 transition hover:bg-blue-100"
            @click="applyCalendarDate"
          >
            确定
          </button>
        </div>
      </section>

      <section class="min-w-0">
        <div class="space-y-2">
          <div
            v-for="(hotspot, index) in hotspots"
            :key="hotspot.id"
            class="rounded-sm bg-white p-5 shadow-sm"
          >
            <div class="flex items-start gap-3">
              <span
                v-if="showSourceRanking"
                class="mt-0.5 inline-flex h-6 w-6 flex-shrink-0 items-center justify-center rounded text-xs font-bold"
                :class="
                  getDisplayRank(index) <= 3
                    ? 'bg-red-500 text-white'
                    : 'bg-gray-200 text-gray-600'
                "
              >
                {{ getDisplayRank(index) }}
              </span>

              <div class="min-w-0 flex-1">
                <h3
                  class="text-lg font-bold leading-snug text-[#121212] hover:text-blue-600"
                >
                  {{ hotspot.title }}
                </h3>

                <div class="hotspot-meta-row mt-3 text-xs text-gray-400">
                  <span
                    class="meta-source font-medium"
                    :class="
                      hotspot.source === 'zhihu'
                        ? 'text-blue-600'
                        : 'text-orange-500'
                    "
                  >
                    {{ hotspot.source === "zhihu" ? "知乎" : "微博" }}
                  </span>
                  <span class="meta-heat inline-flex items-center gap-1">
                    <span class="i-mdi-fire text-orange-500" />
                    {{ formatHeatToWan(hotspot.heat) || "--" }}
                  </span>
                  <span class="meta-time">{{
                    formatDate(hotspot.crawled_at)
                  }}</span>
                  <button
                    v-if="hotspot.url"
                    type="button"
                    class="meta-link"
                    @click.stop="openHotspotOriginalLink(hotspot)"
                  >
                    查看原文 ->
                  </button>
                  <span v-else class="meta-link-placeholder">--</span>
                  <button
                    v-if="hotspot.question_id"
                    type="button"
                    class="meta-link"
                    @click.stop="goToQuestion(hotspot)"
                  >
                    查看问答 ->
                  </button>
                  <span v-else class="meta-link-placeholder">--</span>
                  <button
                    v-if="hotspot.source === 'zhihu'"
                    type="button"
                    class="meta-link"
                    @click.stop="router.push(`/hotspots/${hotspot.id}`)"
                  >
                    查看agent与真人回答对比 ->
                  </button>
                  <span v-else class="meta-link-placeholder">--</span>
                </div>
              </div>
            </div>
          </div>

          <div
            v-if="!listInitialized"
            class="rounded-sm bg-white py-8 text-center text-gray-500 shadow-sm"
          >
            加载中...
          </div>

          <div
            v-else-if="hotspots.length === 0"
            class="rounded-sm bg-white py-12 text-center text-gray-400 shadow-sm"
          >
            <div class="i-mdi-fire mb-2 inline-block text-4xl text-gray-300" />
            <div>{{ selectedDate || "所选日期" }} 暂无热点数据</div>
          </div>
        </div>

        <div
          v-if="total > pageSize"
          class="mt-6 flex flex-wrap items-center justify-center gap-3 py-2 text-sm text-gray-500"
        >
          <button
            class="rounded border border-gray-200 bg-white px-3 py-1.5 transition hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="page <= 1"
            @click="page--"
          >
            上一页
          </button>
          <span>{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
          <button
            class="rounded border border-gray-200 bg-white px-3 py-1.5 transition hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="page >= Math.ceil(total / pageSize)"
            @click="page++"
          >
            下一页
          </button>
          <input
            v-model="pageJumpInput"
            type="number"
            min="1"
            :max="Math.ceil(total / pageSize)"
            class="w-20 rounded border border-gray-200 px-2 py-1.5 text-center text-sm outline-none focus:border-blue-300"
            placeholder="页码"
            @keyup.enter="applyPageJump"
          />
          <button
            class="rounded border border-blue-200 bg-blue-50 px-3 py-1.5 text-blue-600 transition hover:bg-blue-100"
            @click="applyPageJump"
          >
            跳转
          </button>
        </div>
      </section>
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

.formatted-content {
  word-break: break-word;
  overflow-wrap: anywhere;
  line-height: 1.85;
}

.formatted-content :deep(p) {
  margin: 0 0 0.9em;
}

.formatted-content :deep(p:last-child) {
  margin-bottom: 0;
}

.formatted-content :deep(ul),
.formatted-content :deep(ol) {
  margin: 0 0 0.9em;
  padding-left: 1.35em;
}

.formatted-content :deep(li) {
  margin: 0.3em 0;
}

.formatted-content :deep(blockquote) {
  margin: 0 0 0.9em;
  padding: 0.2em 0.9em;
  border-left: 3px solid #dce8ff;
  background: #f7faff;
  color: #4e5f7a;
}

.formatted-content :deep(a) {
  color: #175199;
  text-decoration: none;
}

.formatted-content :deep(a:hover) {
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

.waterfall-list {
  display: grid;
  gap: 12px;
}

.waterfall-card {
  break-inside: avoid;
}

.hotspot-meta-row {
  display: grid;
  grid-template-columns: 52px 84px 96px 92px 92px 92px;
  align-items: center;
  column-gap: 12px;
}

.meta-source,
.meta-heat,
.meta-time,
.meta-link,
.meta-link-placeholder {
  min-width: 0;
  text-align: left;
  white-space: nowrap;
}

.meta-link {
  border: none;
  background: transparent;
  padding: 0;
  color: #3b82f6;
  cursor: pointer;
}

.meta-link:hover {
  color: #2563eb;
}

.meta-link-placeholder {
  opacity: 0;
  pointer-events: none;
}

@media (max-width: 900px) {
  .hotspot-meta-row {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    row-gap: 6px;
  }

  .meta-link-placeholder {
    display: none;
  }
}
</style>
