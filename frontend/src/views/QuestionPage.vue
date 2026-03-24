<script setup lang="ts">
import type {
  AgentResponse,
  AnswerWithStats,
  QuestionWithStats,
} from "../api/types";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getAnswerDetail, getAnswerList } from "../api/answer";
import { getMyAgents } from "../api/agent";
import { getAnswerCollectionStatuses } from "../api/collection";
import { executeFollow } from "../api/follow";
import { getHotspotByQuestionId } from "../api/hotspot";
import { getQuestionDetail } from "../api/question";
import { triggerManualAgentAnswers } from "../api/qa";
import { executeReaction } from "../api/reaction";
import { ReactionAction, TargetType } from "../api/types";
import AnswerItem from "../components/AnswerItem.vue";
import AvatarImage from "../components/AvatarImage.vue";
import { useStreamChannel } from "../composables/useStreamChannel";
import { useUserStore } from "../stores/user";
import { formatRichTextForDisplay } from "../utils/textRender";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const question = ref<QuestionWithStats | null>(null);
const answers = ref<AnswerWithStats[]>([]);
const loading = ref(false);
const answersLoading = ref(false);
const answersCursor = ref<number | undefined>(undefined);
const answersHasMore = ref(true);
const collectionStatusMap = ref<Record<number, number[]>>({});

const likeCount = ref(0);
const dislikeCount = ref(0);
const reactionStatus = ref<0 | 1 | 2>(0);
const isFollowingQuestion = ref(false);

const showAgentAnswerDialog = ref(false);
const myAgents = ref<AgentResponse[]>([]);
const selectedAgentIds = ref<number[]>([]);
const loadingMyAgents = ref(false);
const submittingAgentAnswer = ref(false);
const hotspotMetaFallback = ref<{
  source: string;
  heat: string;
  time: string;
  url: string;
} | null>(null);

const sortMode = ref<"desc" | "asc" | "hot">("desc");
const showSortDropdown = ref(false);
const hoverSortMode = ref<"desc" | "asc" | "hot" | null>(null);
const lastRefreshedAt = ref<Date | null>(null);
const pendingAnswerCount = ref(0);
const isAnswerDetailMode = computed(() => !!route.params.answerId);
const isAgentAnswerRoute = computed(
  () => route.name === "question-agent-answer-page",
);
const hasPendingUpdates = computed(() => pendingAnswerCount.value > 0);

function decodeText(raw: string | undefined | null): string {
  if (!raw) return "";
  const div = document.createElement("div");
  div.innerHTML = raw;
  const decoded = div.textContent || div.innerText || "";
  const div2 = document.createElement("div");
  div2.innerHTML = decoded;
  return (div2.textContent || div2.innerText || "").trim();
}

function normalizeTitle(raw: string | undefined | null): string {
  return decodeText(raw).replace(/\s+/g, " ").trim();
}

function parseHeatValue(raw: string | undefined | null): number {
  const text = String(raw || "")
    .replace(/,/g, "")
    .replace(/\s+/g, "")
    .trim();
  if (!text) return 0;

  const match = text.match(/(\d+(?:\.\d+)?)/);
  if (!match) return 0;

  let value = Number.parseFloat(match[1] || "0");
  if (Number.isNaN(value)) return 0;

  if (text.includes("亿")) value *= 100000000;
  else if (text.includes("万")) value *= 10000;
  else if (text.includes("千")) value *= 1000;

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

const displayQuestionTitle = computed(() =>
  normalizeTitle(question.value?.title),
);
const displayQuestionContent = computed(() =>
  decodeText(question.value?.content),
);
const shouldShowQuestionContent = computed(() => {
  if ((question.value?.type || "") === "debate") return false;
  return displayQuestionContent.value.length > 0;
});
const displayQuestionContentHtml = computed(() =>
  formatRichTextForDisplay(displayQuestionContent.value),
);
const hotspotMeta = computed(() => {
  const source = String(
    question.value?.hotspot?.source || hotspotMetaFallback.value?.source || "",
  );
  const heat = formatHeatToWan(
    String(
      question.value?.hotspot?.heat || hotspotMetaFallback.value?.heat || "",
    ),
  );
  const time = String(
    question.value?.hotspot?.time || hotspotMetaFallback.value?.time || "",
  );
  const url = String(
    question.value?.hotspot?.url || hotspotMetaFallback.value?.url || "",
  );
  return {
    source,
    heat,
    time,
    url,
    hasAny: Boolean(source || heat || time || url),
  };
});

async function loadHotspotMetaFallback() {
  const questionId = Number(route.params.questionId);
  if (!questionId) return;
  if (question.value?.hotspot) {
    return;
  }

  try {
    const res = await getHotspotByQuestionId(questionId);
    if (res.data.code === 200 && res.data.data) {
      hotspotMetaFallback.value = {
        source: res.data.data.source || "",
        heat: res.data.data.heat || "",
        time: res.data.data.crawled_at || res.data.data.hotspot_date || "",
        url: res.data.data.url || "",
      };
      return;
    }
  } catch {
    // Not all questions come from hotspot sources.
  }

  hotspotMetaFallback.value = null;
}

function getAnswerHotScore(answer: AnswerWithStats) {
  const like = answer.stats.like_count || 0;
  const dislike = answer.stats.dislike_count || 0;
  const comment = answer.stats.comment_count || 0;
  const collect = 0;
  return (
    2.8 * Math.log1p(like) +
    4.0 * Math.log1p(comment) +
    2.0 * Math.log1p(collect) -
    2.0 * Math.log1p(dislike)
  );
}

function getCreatedAtMs(answer: AnswerWithStats) {
  const ms = new Date(answer.created_at).getTime();
  if (Number.isNaN(ms)) {
    return answer.id || 0;
  }
  return ms;
}

const sortedAnswers = computed(() => {
  const list = [...answers.value];
  if (sortMode.value === "hot") {
    return list.sort((a, b) => {
      const scoreDiff = getAnswerHotScore(b) - getAnswerHotScore(a);
      if (scoreDiff !== 0) return scoreDiff;
      return getCreatedAtMs(b) - getCreatedAtMs(a);
    });
  }
  if (sortMode.value === "asc") {
    return list.sort((a, b) => getCreatedAtMs(a) - getCreatedAtMs(b));
  }
  return list.sort((a, b) => getCreatedAtMs(b) - getCreatedAtMs(a));
});

const sortText = computed(() => {
  if (sortMode.value === "asc") return "正序";
  if (sortMode.value === "hot") return "按热度";
  return "倒序";
});

function selectSort(mode: "desc" | "asc" | "hot") {
  sortMode.value = mode;
  hoverSortMode.value = null;
  showSortDropdown.value = false;
}

const latestAnswer = computed(() => {
  if (answers.value.length === 0) return null;
  return [...answers.value].sort((a, b) => b.id - a.id)[0] || null;
});

async function loadQuestion() {
  const questionId = Number(route.params.questionId);
  if (!questionId) return;

  loading.value = true;
  try {
    const res = await getQuestionDetail(questionId);
    if (res.data.code === 200 && res.data.data) {
      question.value = res.data.data;
      likeCount.value = res.data.data.stats.like_count;
      dislikeCount.value = res.data.data.stats.dislike_count;
      reactionStatus.value = res.data.data.reaction_status ?? 0;
      isFollowingQuestion.value = res.data.data.is_following ?? false;
    }
  } catch (error) {
    console.error("Failed to load question:", error);
  } finally {
    loading.value = false;
  }
}

async function loadAnswers() {
  const questionId = Number(route.params.questionId);
  if (!questionId || answersLoading.value) return;

  answersLoading.value = true;
  try {
    if (isAnswerDetailMode.value) {
      const answerId = Number(route.params.answerId || 0);
      if (!answerId) {
        answers.value = [];
        return;
      }
      const res = await getAnswerDetail(answerId);
      if (
        res.data.code === 200 &&
        res.data.data &&
        Number(res.data.data.question_id || 0) === questionId
      ) {
        answers.value = [res.data.data];
        answersHasMore.value = false;
        answersCursor.value = undefined;
        await loadCollectionStatuses([res.data.data.id]);
      } else {
        answers.value = [];
      }
      return;
    }

    if (!answersHasMore.value) {
      return;
    }

    const res = await getAnswerList(questionId, answersCursor.value, 20);
    if (!(res.data.code === 200 && res.data.data)) return;

    const seen = new Set(answers.value.map((item) => item.id));
    const merged = [...answers.value];
    const newAnswerIds: number[] = [];
    for (const item of res.data.data.list || []) {
      if (seen.has(item.id)) continue;
      seen.add(item.id);
      merged.push(item);
      newAnswerIds.push(item.id);
    }

    answers.value = merged;
    answersHasMore.value = res.data.data.has_more;
    answersCursor.value = res.data.data.next_cursor || undefined;
    await loadCollectionStatuses(newAnswerIds);
  } catch (error) {
    console.error("Failed to load answers:", error);
  } finally {
    answersLoading.value = false;
  }
}

async function loadCollectionStatuses(answerIds: number[]) {
  if (!userStore.user?.token || answerIds.length === 0) {
    return;
  }

  try {
    const res = await getAnswerCollectionStatuses(answerIds);
    if (!(res.data.code === 200 && res.data.data)) return;

    const nextMap: Record<number, number[]> = { ...collectionStatusMap.value };
    for (const item of res.data.data.items || []) {
      nextMap[item.answer_id] = item.collection_ids || [];
    }
    collectionStatusMap.value = nextMap;
  } catch (error) {
    console.error("Failed to load collection statuses:", error);
  }
}

async function handleReaction(action: ReactionAction) {
  if (!userStore.user?.token) {
    router.push("/login");
    return;
  }
  if (!question.value) return;

  try {
    await executeReaction({
      target_type: TargetType.Question,
      target_id: question.value.id,
      action,
    });

    if (reactionStatus.value === 1) {
      likeCount.value--;
    } else if (reactionStatus.value === 2) {
      dislikeCount.value--;
    }

    if (action === ReactionAction.Like) {
      likeCount.value++;
      reactionStatus.value = 1;
    } else if (action === ReactionAction.Dislike) {
      dislikeCount.value++;
      reactionStatus.value = 2;
    } else {
      reactionStatus.value = 0;
    }
  } catch (error) {
    console.error("Reaction failed:", error);
  }
}

async function handleFollowQuestion() {
  if (!userStore.user?.token) {
    router.push("/login");
    return;
  }
  if (!question.value) return;

  try {
    await executeFollow({
      target_type: TargetType.Question,
      target_id: question.value.id,
      action: !isFollowingQuestion.value,
    });
    isFollowingQuestion.value = !isFollowingQuestion.value;
  } catch (error) {
    console.error("Follow failed:", error);
  }
}

async function openAgentAnswerDialog() {
  if (!userStore.user?.token) {
    router.push("/login");
    return;
  }
  showAgentAnswerDialog.value = true;

  loadingMyAgents.value = true;
  try {
    const res = await getMyAgents();
    if (res.data.code === 200 && res.data.data) {
      myAgents.value = res.data.data;
    }
  } catch (error) {
    console.error("Failed to load my agents:", error);
  } finally {
    loadingMyAgents.value = false;
  }
}

async function submitAgentAnswer() {
  const questionId = Number(route.params.questionId);
  if (!questionId || selectedAgentIds.value.length === 0) return;

  submittingAgentAnswer.value = true;
  try {
    await triggerManualAgentAnswers(questionId, selectedAgentIds.value);
    showAgentAnswerDialog.value = false;
    selectedAgentIds.value = [];
    await loadAnswers();
  } catch (error) {
    console.error("Failed to trigger manual agent answers:", error);
  } finally {
    submittingAgentAnswer.value = false;
  }
}

function parseEventPayload(raw: any): Record<string, any> {
  const data = raw?.data;
  if (typeof data === "string") {
    try {
      const parsed = JSON.parse(data);
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
      return {};
    }
  }
  return data && typeof data === "object" ? data : {};
}

async function refreshCurrentView() {
  answers.value = [];
  answersCursor.value = undefined;
  answersHasMore.value = true;
  collectionStatusMap.value = {};
  await loadQuestion();
  await loadHotspotMetaFallback();
  await loadAnswers();
  pendingAnswerCount.value = 0;
  lastRefreshedAt.value = new Date();
}

useStreamChannel("questions", (message) => {
  const eventName = String(message?.event || "");
  if (eventName !== "answer_created") return;

  const payload = parseEventPayload(message);
  const currentQuestionId = Number(route.params.questionId);
  if (Number(payload?.question_id || 0) !== currentQuestionId) return;
  pendingAnswerCount.value += 1;
});

onMounted(async () => {
  await refreshCurrentView();
  if (isAgentAnswerRoute.value) {
    await openAgentAnswerDialog();
  }
});

watch(
  () => route.params.questionId,
  async () => {
    question.value = null;
    answers.value = [];
    hotspotMetaFallback.value = null;
    pendingAnswerCount.value = 0;
    await refreshCurrentView();
  },
);

watch(
  () => route.params.answerId,
  async () => {
    await loadAnswers();
  },
);
</script>

<template>
  <div class="mx-auto mt-4 max-w-[1020px] px-4 pb-10 md:px-0">
    <div class="right-rail-refresh">
      <div class="right-rail-refresh-inner">
        <span class="hidden text-xs text-slate-500 sm:inline">
          {{
            hasPendingUpdates
              ? `有新回答 ${pendingAnswerCount} 条`
              : lastRefreshedAt
                ? `上次刷新 ${lastRefreshedAt.toLocaleTimeString("zh-CN")}`
                : "点击刷新"
          }}
        </span>
        <button
          class="group flex h-9 w-9 items-center justify-center rounded-full border border-sky-200 bg-white text-sky-700 transition hover:bg-sky-50 disabled:opacity-50"
          :disabled="loading || answersLoading"
          @click="refreshCurrentView"
        >
          <span
            class="i-mdi-refresh text-lg"
            :class="
              loading || answersLoading
                ? 'animate-spin'
                : 'transition-transform duration-300 group-hover:rotate-180'
            "
          />
        </button>
      </div>
    </div>

    <div v-if="loading" class="py-12 text-center text-gray-500">加载中...</div>

    <template v-else-if="question">
      <div class="mb-2.5 rounded-sm bg-white p-6 shadow-sm">
        <div
          v-if="question.tags && question.tags.length > 0"
          class="mb-4 flex flex-wrap gap-2"
        >
          <span
            v-for="tag in question.tags"
            :key="tag.id"
            class="cursor-pointer rounded-full bg-blue-50 px-3 py-1 text-sm text-blue-600 font-medium hover:bg-blue-100"
          >
            {{ tag.name }}
          </span>
        </div>
        <div
          v-if="hotspotMeta.hasAny"
          class="mb-4 flex flex-wrap items-center gap-2 text-xs"
        >
          <span
            v-if="hotspotMeta.source"
            class="rounded-full bg-orange-50 px-2.5 py-1 font-medium text-orange-600"
          >
            来源：{{
              hotspotMeta.source === "zhihu"
                ? "知乎"
                : hotspotMeta.source === "weibo"
                  ? "微博"
                  : hotspotMeta.source
            }}
          </span>
          <span
            v-if="hotspotMeta.heat"
            class="rounded-full bg-red-50 px-2.5 py-1 font-medium text-red-600"
          >
            热度：{{ hotspotMeta.heat }}
          </span>
          <span
            v-if="hotspotMeta.time"
            class="rounded-full bg-gray-100 px-2.5 py-1 font-medium text-gray-600"
          >
            时间：{{ new Date(hotspotMeta.time).toLocaleString("zh-CN") }}
          </span>
          <a
            v-if="hotspotMeta.url"
            :href="hotspotMeta.url"
            target="_blank"
            rel="noopener noreferrer"
            class="rounded-full bg-indigo-50 px-2.5 py-1 font-medium text-indigo-600 hover:bg-indigo-100"
          >
            跳转原链接
          </a>
        </div>

        <h1 class="mb-4 text-2xl text-[#1a1a1a] font-bold leading-normal">
          {{ displayQuestionTitle }}
        </h1>

        <div
          v-if="shouldShowQuestionContent"
          class="mb-4 text-[15px] text-gray-800 formatted-content"
          v-html="displayQuestionContentHtml"
        />

        <div class="flex items-center gap-4">
          <div class="flex gap-2">
            <button
              class="cursor-pointer rounded border-none px-4 py-2 font-medium transition-colors"
              :class="
                isFollowingQuestion
                  ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              "
              @click="handleFollowQuestion"
            >
              {{ isFollowingQuestion ? "已关注" : "关注问题" }}
            </button>
            <button
              class="flex cursor-pointer items-center gap-1 border border-blue-600 rounded bg-white px-4 py-2 text-blue-600 font-medium hover:bg-blue-50"
              @click="openAgentAnswerDialog"
            >
              <span class="i-mdi-robot-outline" />
              让我的Agent回答
            </button>
          </div>

          <div class="ml-2 flex items-center gap-2">
            <button
              class="flex cursor-pointer items-center gap-1 rounded border px-3 py-1.5 transition-colors"
              :class="
                reactionStatus === 1
                  ? 'border-[#cfe0ff] bg-[#eaf2ff] text-[#0066ff]'
                  : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50 hover:border-gray-300'
              "
              @click="
                handleReaction(
                  reactionStatus === 1
                    ? ReactionAction.Cancel
                    : ReactionAction.Like,
                )
              "
            >
              <span class="i-mdi-triangle text-sm" />
              <span class="text-sm font-semibold">{{ likeCount }}</span>
            </button>
            <button
              class="flex cursor-pointer items-center gap-1 rounded border px-3 py-1.5 transition-colors"
              :class="
                reactionStatus === 2
                  ? 'border-red-200 bg-red-50 text-red-500'
                  : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50 hover:border-gray-300'
              "
              @click="
                handleReaction(
                  reactionStatus === 2
                    ? ReactionAction.Cancel
                    : ReactionAction.Dislike,
                )
              "
            >
              <span class="i-mdi-triangle-down text-sm" />
              <span class="text-sm font-semibold">{{ dislikeCount }}</span>
            </button>
          </div>
        </div>
      </div>

      <template v-if="!isAnswerDetailMode">
        <div
          v-if="sortedAnswers.length > 0"
          class="overflow-hidden rounded-sm bg-white shadow-sm"
        >
          <div
            class="flex items-center justify-between border-b border-gray-100 px-4 py-3 text-sm text-gray-500"
          >
            <span>{{ sortedAnswers.length }} 个回答</span>
            <div class="relative">
              <button
                class="inline-flex cursor-pointer items-center gap-1 bg-transparent border-none p-0 text-[14px] transition-colors"
                style="text-shadow: none"
                @click="showSortDropdown = !showSortDropdown"
              >
                <span class="text-[#8590A6]">{{ sortText }}</span>
                <span
                  class="ml-1 inline-flex h-[14px] w-[10px] flex-col items-center justify-center gap-[4px] text-[#8590A6]"
                >
                  <svg
                    viewBox="0 0 8 5"
                    class="h-[5px] w-[8px] shrink-0"
                    fill="none"
                    aria-hidden="true"
                  >
                    <path
                      d="M1 4L4 1L7 4"
                      stroke="currentColor"
                      stroke-width="1.2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                  <svg
                    viewBox="0 0 8 5"
                    class="h-[5px] w-[8px] shrink-0"
                    fill="none"
                    aria-hidden="true"
                  >
                    <path
                      d="M1 1L4 4L7 1"
                      stroke="currentColor"
                      stroke-width="1.2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                </span>
              </button>

              <div
                v-if="showSortDropdown"
                class="absolute right-0 top-full z-10 mt-2 w-[128px] overflow-hidden rounded-lg border border-[#EBEEF5] bg-white shadow-[0_5px_20px_rgba(18,18,18,0.1)]"
              >
                <div
                  class="cursor-pointer px-4 py-2.5 text-center text-[14px] text-[#8590A6] transition-colors hover:bg-[#F6F6F6]"
                  :class="
                    hoverSortMode === 'desc' ||
                    (!hoverSortMode && sortMode === 'desc')
                      ? 'bg-[#F6F6F6]'
                      : ''
                  "
                  style="text-shadow: none"
                  @mouseenter="hoverSortMode = 'desc'"
                  @mouseleave="hoverSortMode = null"
                  @click="selectSort('desc')"
                >
                  倒序
                </div>
                <div
                  class="cursor-pointer px-4 py-2.5 text-center text-[14px] text-[#8590A6] transition-colors hover:bg-[#F6F6F6]"
                  :class="
                    hoverSortMode === 'asc' ||
                    (!hoverSortMode && sortMode === 'asc')
                      ? 'bg-[#F6F6F6]'
                      : ''
                  "
                  style="text-shadow: none"
                  @mouseenter="hoverSortMode = 'asc'"
                  @mouseleave="hoverSortMode = null"
                  @click="selectSort('asc')"
                >
                  正序
                </div>
                <div
                  class="cursor-pointer px-4 py-2.5 text-center text-[14px] text-[#8590A6] transition-colors hover:bg-[#F6F6F6]"
                  :class="
                    hoverSortMode === 'hot' ||
                    (!hoverSortMode && sortMode === 'hot')
                      ? 'bg-[#F6F6F6]'
                      : ''
                  "
                  style="text-shadow: none"
                  @mouseenter="hoverSortMode = 'hot'"
                  @mouseleave="hoverSortMode = null"
                  @click="selectSort('hot')"
                >
                  按热度
                </div>
              </div>
            </div>
          </div>

          <div
            v-for="answer in sortedAnswers"
            :key="answer.id"
            class="border-b border-gray-100 last:border-b-0"
          >
            <AnswerItem
              :answer="answer"
              :show-original-question-button="false"
              :initial-collection-ids="collectionStatusMap[answer.id]"
              :defer-collection-status="Boolean(userStore.user?.token)"
            />
          </div>
        </div>
        <div
          v-if="answers.length > 0 && answersHasMore"
          class="mt-3 flex justify-center"
        >
          <button
            class="rounded-lg border border-blue-200 bg-white px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 disabled:opacity-50"
            :disabled="answersLoading"
            @click="loadAnswers"
          >
            {{ answersLoading ? "加载中..." : "加载更多回答" }}
          </button>
        </div>
        <div
          v-else-if="answers.length === 0"
          class="rounded-sm bg-white py-12 text-center text-gray-400 shadow-sm"
        >
          还没有回答
        </div>
      </template>

      <template v-else>
        <router-link
          :to="`/question/${route.params.questionId}`"
          class="mb-3 block rounded-sm bg-white px-5 py-3 text-blue-600 shadow-sm hover:bg-gray-50 transition-colors"
        >
          <div class="flex items-center justify-between">
            <span class="font-medium">返回问题页（查看全部回答）</span>
            <span class="i-mdi-chevron-right" />
          </div>
        </router-link>

        <div
          v-if="latestAnswer"
          class="overflow-hidden rounded-sm bg-white shadow-sm"
        >
          <div class="border-b border-gray-100 px-4 py-3 text-sm text-gray-500">
            回答详情
          </div>
          <AnswerItem
            :answer="latestAnswer"
            :show-original-question-button="false"
            :initial-collection-ids="collectionStatusMap[latestAnswer.id]"
            :defer-collection-status="Boolean(userStore.user?.token)"
          />
        </div>
        <div
          v-else
          class="rounded-sm bg-white py-12 text-center text-gray-400 shadow-sm"
        >
          还没有回答
        </div>
      </template>

      <div
        v-if="showAgentAnswerDialog"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
        @click.self="showAgentAnswerDialog = false"
      >
        <div class="max-w-xl w-full rounded-xl bg-white p-6 shadow-xl">
          <div class="mb-4 flex items-center justify-between">
            <h3 class="text-lg font-bold text-gray-900">选择Agent回答</h3>
            <button
              class="text-gray-400 hover:text-gray-700"
              @click="showAgentAnswerDialog = false"
            >
              ×
            </button>
          </div>

          <div v-if="loadingMyAgents" class="py-8 text-center text-gray-500">
            加载中...
          </div>

          <div
            v-else-if="myAgents.length === 0"
            class="rounded-lg bg-gray-50 p-6 text-center text-gray-600"
          >
            <p>你还没有创建Agent</p>
            <button
              class="mt-3 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-100"
              @click="router.push('/agents/create')"
            >
              去创建Agent
            </button>
          </div>

          <div v-else>
            <div class="max-h-72 space-y-2 overflow-y-auto pr-1">
              <label
                v-for="agent in myAgents"
                :key="agent.id"
                class="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 px-3 py-2 hover:bg-gray-50"
              >
                <input
                  v-model="selectedAgentIds"
                  type="checkbox"
                  :value="agent.id"
                  class="h-4 w-4"
                />
                <AvatarImage
                  :src="
                    agent.avatar ||
                    `https://api.dicebear.com/7.x/notionists/svg?seed=${encodeURIComponent(agent.name)}`
                  "
                  :alt="agent.name"
                  img-class="h-8 w-8 rounded-full object-cover"
                />
                <div class="min-w-0 flex-1">
                  <div class="truncate font-medium text-gray-900">
                    {{ agent.name }}
                  </div>
                  <div class="truncate text-xs text-gray-500">
                    {{ agent.raw_config.headline }}
                  </div>
                </div>
              </label>
            </div>

            <div class="mt-5 flex justify-end gap-2">
              <button
                class="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                @click="showAgentAnswerDialog = false"
              >
                取消
              </button>
              <button
                class="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                :disabled="
                  selectedAgentIds.length === 0 || submittingAgentAnswer
                "
                @click="submitAgentAnswer"
              >
                {{ submittingAgentAnswer ? "提交中..." : "让所选Agent回答" }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-else-if="!loading" class="py-12 text-center text-gray-400">
      问题不存在
    </div>
  </div>
</template>

<style scoped>
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
</style>
