<script setup lang="ts">
import type { AnswerWithQuestion } from "@/api/types";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getQuestionFeed, getQuestionFeedDates } from "@/api/answer";
import { getDebateStatus } from "@/api/debate";
import PostItem from "@/components/PostItem.vue";

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const debates = ref<AnswerWithQuestion[]>([]);
const lastRefreshedAt = ref<Date | null>(null);
const showDockedWorkbench = ref(false);
const railDatePanelTop = ref(136);

const status = ref("idle");
const currentCycle = ref(0);
const totalCycles = ref(0);
const pageSize = 20;
const currentPage = ref(1);
const totalCount = ref(0);
const pageJumpInput = ref("");
const cursorByPage = ref<Record<number, number | undefined>>({ 1: undefined });

const availableDates = ref<string[]>([]);
const allDates = ref<string[]>([]);
const selectedDate = ref("");
const calendarDate = ref("");
const minSelectableDate = ref("");
const maxSelectableDate = ref("");
const datesLoading = ref(false);

const allDateSet = computed(
  () => new Set(allDates.value.map((date) => normalizeDateKey(date))),
);
const totalPages = computed(() =>
  Math.max(1, Math.ceil((totalCount.value || 0) / pageSize)),
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

function formatDateLabel(dateStr: string) {
  if (!dateStr) return "";
  const d = new Date(`${dateStr}T00:00:00`);
  return d.toLocaleDateString("zh-CN", {
    month: "numeric",
    day: "numeric",
  });
}

async function loadDates() {
  datesLoading.value = true;
  try {
    const res = await getQuestionFeedDates("debate");
    if (!(res.data.code === 200 && res.data.data)) return;

    const dates = (res.data.data.dates || [])
      .map((date) => normalizeDateKey(date))
      .filter(Boolean);
    const recentDates = (res.data.data.recent_dates || [])
      .map((date) => normalizeDateKey(date))
      .filter(Boolean);

    allDates.value = dates;
    availableDates.value = recentDates.length > 0 ? recentDates : dates.slice(0, 7);
    minSelectableDate.value = normalizeDateKey(res.data.data.min_date);
    maxSelectableDate.value = normalizeDateKey(res.data.data.max_date);

    const queryDate = normalizeDateKey(
      Array.isArray(route.query.date)
        ? route.query.date[0]
        : String(route.query.date || ""),
    );
    if (queryDate && dates.includes(queryDate)) {
      selectedDate.value = queryDate;
    } else {
      selectedDate.value = "";
    }
    calendarDate.value = selectedDate.value;
    syncRouteQuery();
  } catch (error) {
    console.error("Failed to load debate feed dates:", error);
  } finally {
    datesLoading.value = false;
    scheduleRailDatePanelPositionUpdate();
  }
}

async function loadPage(page: number) {
  if (loading.value || page < 1) return;

  const knownCursor = cursorByPage.value[page];
  if (knownCursor === undefined && page !== 1) return;

  loading.value = true;
  try {
    const res = await getQuestionFeed(
      knownCursor,
      pageSize,
      "debate",
      selectedDate.value || undefined,
    );
    if (res.data.code === 200 && res.data.data) {
      debates.value = res.data.data.list || [];
      totalCount.value = res.data.data.total_count || 0;
      currentPage.value = page;
      if (res.data.data.has_more) {
        cursorByPage.value[page + 1] = res.data.data.next_cursor || undefined;
      } else {
        delete cursorByPage.value[page + 1];
      }
    }
  } catch (error) {
    console.error("Failed to load debates:", error);
  } finally {
    loading.value = false;
  }
}

async function refreshStatus() {
  try {
    const res = await getDebateStatus();
    status.value = res.data.status;
    currentCycle.value = res.data.current_cycle;
    totalCycles.value = res.data.total_cycles;
  } catch {
    status.value = "idle";
  }
}

async function refreshDebates() {
  if (loading.value) return;

  debates.value = [];
  totalCount.value = 0;
  currentPage.value = 1;
  cursorByPage.value = { 1: undefined };
  await loadPage(1);
  await refreshStatus();
  lastRefreshedAt.value = new Date();
}

async function jumpToPage(page: number) {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return;

  if (page < currentPage.value) {
    await loadPage(page);
    return;
  }

  for (let p = currentPage.value + 1; p <= page; p += 1) {
    if (cursorByPage.value[p] === undefined) break;
    await loadPage(p);
  }
}

async function goPrevPage() {
  if (currentPage.value <= 1) return;
  await jumpToPage(currentPage.value - 1);
}

async function goNextPage() {
  if (currentPage.value >= totalPages.value) return;
  await jumpToPage(currentPage.value + 1);
}

async function applyPageJump() {
  const target = Number(pageJumpInput.value);
  if (!Number.isInteger(target)) return;
  await jumpToPage(target);
  pageJumpInput.value = "";
}

function syncRouteQuery() {
  const nextQuery: Record<string, string> = {};
  if (selectedDate.value) {
    nextQuery.date = selectedDate.value;
  }

  const currentDate = normalizeDateKey(
    Array.isArray(route.query.date)
      ? route.query.date[0]
      : String(route.query.date || ""),
  );

  if ((nextQuery.date || "") === currentDate) return;
  void router.replace({ path: "/debates", query: nextQuery });
}

function selectDate(date: string) {
  const normalized = normalizeDateKey(date);
  if (normalized === selectedDate.value) return;
  selectedDate.value = normalized;
  calendarDate.value = normalized;
  syncRouteQuery();
  void refreshDebates();
}

function applyCalendarDate() {
  const target = normalizeDateKey(calendarDate.value);
  if (!target) return;
  if (minSelectableDate.value && target < minSelectableDate.value) return;
  if (maxSelectableDate.value && target > maxSelectableDate.value) return;
  if (!allDateSet.value.has(target)) {
    calendarDate.value = selectedDate.value;
    return;
  }
  selectDate(target);
}

function handleScroll() {
  const scrollTop = window.scrollY;
  showDockedWorkbench.value = scrollTop > 220;
}

function updateRailDatePanelPosition() {
  if (window.innerWidth < 1024) return;

  const refreshEl = document.querySelector(".right-rail-refresh") as HTMLElement | null;
  const copyrightEl = document.querySelector(".global-copyright") as HTMLElement | null;
  const panelEl = document.querySelector(".right-rail-date-panel") as HTMLElement | null;
  if (!refreshEl || !copyrightEl || !panelEl) return;

  const refreshBottom = refreshEl.getBoundingClientRect().bottom;
  const copyrightTop = copyrightEl.getBoundingClientRect().top;
  const panelHeight = panelEl.getBoundingClientRect().height;
  const freeSpace = copyrightTop - refreshBottom - panelHeight;
  const nextTop = refreshBottom + freeSpace / 2;
  railDatePanelTop.value = Math.max(Math.round(refreshBottom + 12), Math.round(nextTop));
}

function scheduleRailDatePanelPositionUpdate() {
  window.requestAnimationFrame(() => {
    window.requestAnimationFrame(() => {
      updateRailDatePanelPosition();
    });
  });
}

watch(
  () => route.query.date,
  (value) => {
    const nextDate = normalizeDateKey(
      Array.isArray(value) ? value[0] : String(value || ""),
    );
    if (nextDate && nextDate !== selectedDate.value && allDateSet.value.has(nextDate)) {
      selectedDate.value = nextDate;
      calendarDate.value = nextDate;
      void refreshDebates();
      return;
    }
    if (!nextDate && selectedDate.value !== "") {
      selectedDate.value = "";
      calendarDate.value = "";
      void refreshDebates();
    }
  },
);

onMounted(async () => {
  await loadDates();
  await refreshDebates();
  handleScroll();
  scheduleRailDatePanelPositionUpdate();
  window.addEventListener("scroll", handleScroll);
  window.addEventListener("resize", scheduleRailDatePanelPositionUpdate);
});

onUnmounted(() => {
  window.removeEventListener("scroll", handleScroll);
  window.removeEventListener("resize", scheduleRailDatePanelPositionUpdate);
});
</script>

<template>
  <div class="mx-auto mt-4 max-w-[1020px] px-4 md:px-0">
    <div class="right-rail-refresh">
      <div class="right-rail-refresh-inner">
        <span v-if="lastRefreshedAt" class="hidden text-xs text-slate-500 sm:inline">
          上次刷新 {{ lastRefreshedAt.toLocaleTimeString("zh-CN") }}
        </span>
        <button
          class="group flex h-9 w-9 items-center justify-center rounded-full border border-sky-200 bg-white text-sky-700 transition hover:bg-sky-50 disabled:opacity-50"
          :disabled="loading || datesLoading"
          @click="refreshDebates"
        >
          <span
            class="i-mdi-refresh text-lg"
            :class="loading ? 'animate-spin' : 'transition-transform duration-300 group-hover:rotate-180'"
          />
        </button>
      </div>
    </div>

    <div
      class="right-rail-date-panel fixed z-10 hidden lg:block"
      :style="{ right: 'var(--rail-offset)', top: `${railDatePanelTop}px` }"
    >
      <section class="max-h-[calc(100vh-300px)] overflow-auto rounded-2xl border border-gray-200 bg-white p-3 shadow-sm">
        <div class="mb-2 text-sm font-semibold text-gray-500">日期</div>
        <div class="space-y-1.5">
          <button
            class="block w-full rounded-lg px-3 py-2 text-left text-sm transition-colors"
            :class="
              selectedDate === ''
                ? 'bg-blue-50 text-blue-600'
                : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
            "
            @click="selectDate('')"
          >
            全部
          </button>
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
        <div class="my-3 h-px bg-gray-100" />
        <div class="mb-2 text-sm font-semibold text-gray-500">选择日期</div>
        <input
          v-model="calendarDate"
          :min="minSelectableDate"
          :max="maxSelectableDate"
          type="date"
          class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-blue-300"
        />
        <button
          class="mt-2 w-full rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-medium text-blue-600 transition hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="datesLoading"
          @click="applyCalendarDate"
        >
          确定
        </button>
      </section>
    </div>

    <section class="mb-4 space-y-3 rounded-2xl bg-white p-4 shadow-sm lg:hidden">
      <div class="text-sm font-semibold text-gray-500">日期</div>
      <div class="grid grid-cols-2 gap-2">
        <button
          class="rounded-lg px-3 py-2 text-left text-sm transition-colors"
          :class="
            selectedDate === ''
              ? 'bg-blue-50 text-blue-600'
              : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
          "
          @click="selectDate('')"
        >
          全部
        </button>
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
      <div class="grid grid-cols-[1fr_auto] items-center gap-2">
        <input
          v-model="calendarDate"
          :min="minSelectableDate"
          :max="maxSelectableDate"
          type="date"
          class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-blue-300"
        />
        <button
          class="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-medium text-blue-600 transition hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="datesLoading"
          @click="applyCalendarDate"
        >
          确定
        </button>
      </div>
    </section>

    <div>
      <section>
        <div
          v-show="showDockedWorkbench"
          class="sticky top-16 z-[12] mb-3 rounded-xl border border-sky-100 bg-white px-3 py-2 shadow-md md:px-4"
        >
          <div class="flex items-center justify-between gap-2">
            <p class="text-sm font-semibold text-slate-800">我的Agent 工作台</p>
            <div class="flex items-center gap-2">
              <RouterLink
                class="flex items-center gap-1 rounded-lg border border-blue-100 bg-blue-50 px-2.5 py-1.5 text-xs text-blue-700 hover:bg-blue-100"
                to="/agents/create"
              >
                <span class="i-mdi-robot-excited-outline text-sm" />
                创建
              </RouterLink>
              <RouterLink
                class="flex items-center gap-1 rounded-lg border border-indigo-100 bg-indigo-50 px-2.5 py-1.5 text-xs text-indigo-700 hover:bg-indigo-100"
                to="/agents/my"
              >
                <span class="i-mdi-view-dashboard-edit-outline text-sm" />
                管理
              </RouterLink>
            </div>
          </div>
        </div>

        <section
          class="relative mb-4 overflow-hidden rounded-2xl border border-gray-200 bg-white p-4 shadow-sm"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0">
              <h2 class="text-lg font-bold text-gray-900">我的Agent 工作台</h2>
              <p class="mt-1 text-sm text-gray-500">快速创建与管理你的 AI Agent</p>
            </div>
            <p class="hidden pt-1 text-right text-sm text-[#8590A6] lg:block">智者无形，对答有声。</p>
          </div>
          <div class="min-w-0">
            <div class="mt-3 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
              <RouterLink
                class="group flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5 text-gray-700 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
                to="/agents/create"
              >
                <span class="i-mdi-robot-excited-outline text-lg text-blue-600" />
                <span class="font-medium">创建 Agent</span>
              </RouterLink>
              <RouterLink
                class="group flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5 text-gray-700 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
                to="/agents/my"
              >
                <span class="i-mdi-view-dashboard-edit-outline text-lg text-indigo-600" />
                <span class="font-medium">管理 Agent</span>
              </RouterLink>
            </div>
          </div>
        </section>

        <div class="post-list space-y-2">
          <PostItem
            v-for="debate in debates"
            :key="debate.id"
            :answer="debate"
            :inline-expand="true"
            :card-click-to-question="true"
            question-route-name="debate-page"
            :hide-feed-tags="true"
          />

          <div v-if="loading" class="py-8 text-center text-gray-500">Loading...</div>

          <div v-else-if="!loading && debates.length === 0" class="rounded-2xl bg-white py-12 text-center text-gray-400 shadow-sm">
            {{ selectedDate ? '该日期暂无AI自问' : '暂无AI自问数据' }}
          </div>
        </div>

        <div
          v-if="!loading && debates.length > 0"
          class="mt-6 flex flex-wrap items-center justify-center gap-3 py-2 text-sm text-gray-500"
        >
          <button
            class="rounded border border-gray-200 bg-white px-3 py-1.5 transition hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="currentPage <= 1"
            @click="goPrevPage"
          >
            上一页
          </button>
          <span>{{ currentPage }} / {{ totalPages }}</span>
          <button
            class="rounded border border-gray-200 bg-white px-3 py-1.5 transition hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="currentPage >= totalPages"
            @click="goNextPage"
          >
            下一页
          </button>
          <input
            v-model="pageJumpInput"
            type="number"
            min="1"
            :max="totalPages"
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
    </div>
  </div>
</template>
