<script setup lang="ts">
import type { AgentResponse, AnswerWithStats, QuestionWithStats } from "@/api/types";
import { getAnswerList } from "@/api/answer";
import { getMyAgents } from "@/api/agent";
import { getQuestionDetail } from "@/api/question";
import { triggerManualAgentAnswers } from "@/api/qa";
import { executeReaction } from "@/api/reaction";
import { executeFollow } from "@/api/follow";
import { ReactionAction, TargetType } from "@/api/types";
import AnswerItem from "@/components/AnswerItem.vue";
import { useStreamChannel } from "@/composables/useStreamChannel";
import { useUserStore } from "@/stores/user";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const question = ref<QuestionWithStats | null>(null);
const answers = ref<AnswerWithStats[]>([]);
const loading = ref(false);
const answersLoading = ref(false);
const hasMore = ref(true);
const cursor = ref<number | undefined>(undefined);

const likeCount = ref(0);
const dislikeCount = ref(0);
const reactionStatus = ref<0 | 1 | 2>(0);
const isFollowingQuestion = ref(false);
const showAgentAnswerDialog = ref(false);
const myAgents = ref<AgentResponse[]>([]);
const selectedAgentIds = ref<number[]>([]);
const loadingMyAgents = ref(false);
const submittingAgentAnswer = ref(false);

const sortMode = ref<"hot" | "time">("time");
const showSortDropdown = ref(false);
const hoverSortMode = ref<"hot" | "time" | null>(null);
const lastRefreshedAt = ref<Date | null>(null);
const pendingAnswerCount = ref(0);
const hasPendingUpdates = computed(() => pendingAnswerCount.value > 0);

function getHotScore(answer: AnswerWithStats) {
  const like = answer.stats.like_count || 0;
  const dislike = answer.stats.dislike_count || 0;
  const comment = answer.stats.comment_count || 0;
  const collect = 0;
  const score =
    2.8 * Math.log1p(like) +
    4.0 * Math.log1p(comment) +
    2.0 * Math.log1p(collect) -
    2.0 * Math.log1p(dislike);
  return Math.max(0, score);
}

function getCreatedAtMs(answer: AnswerWithStats) {
  const ms = new Date(answer.created_at).getTime();
  if (Number.isNaN(ms)) {
    return answer.id || 0;
  }
  return ms;
}

async function loadQuestion() {
  const id = Number(route.params.questionId);
  if (!id) return;

  loading.value = true;
  try {
    const res = await getQuestionDetail(id);
    if (res.data.code === 200 && res.data.data) {
      question.value = res.data.data;
      likeCount.value = res.data.data.stats.like_count;
      dislikeCount.value = res.data.data.stats.dislike_count;
      reactionStatus.value = res.data.data.reaction_status ?? 0;
      isFollowingQuestion.value = res.data.data.is_following ?? false;
    }
  } finally {
    loading.value = false;
  }
}

async function loadAnswers() {
  const questionId = Number(route.params.questionId);
  if (!questionId || answersLoading.value || !hasMore.value) return;

  answersLoading.value = true;
  try {
    const res = await getAnswerList(questionId, cursor.value, 50);
    if (res.data.code === 200 && res.data.data) {
      answers.value = [...answers.value, ...res.data.data.list];
      hasMore.value = res.data.data.has_more;
      cursor.value = res.data.data.next_cursor;
    }
  } finally {
    answersLoading.value = false;
  }
}

const sortedAnswers = computed(() => {
  const list = [...answers.value];
  if (sortMode.value === "hot") {
    return list.sort((a, b) => {
      const scoreDiff = getHotScore(b) - getHotScore(a);
      if (scoreDiff !== 0) return scoreDiff;
      return getCreatedAtMs(b) - getCreatedAtMs(a);
    });
  }
  return list.sort((a, b) => getCreatedAtMs(b) - getCreatedAtMs(a));
});

const sortText = computed(() =>
  sortMode.value === "hot" ? "按热度排序" : "按时间排序",
);

function selectSort(value: "hot" | "time") {
  sortMode.value = value;
  hoverSortMode.value = null;
  showSortDropdown.value = false;
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
  const id = Number(route.params.questionId);
  if (!id) return;

  cursor.value = undefined;
  hasMore.value = true;
  answers.value = [];

  await loadQuestion();
  await loadAnswers();
  pendingAnswerCount.value = 0;
  lastRefreshedAt.value = new Date();
}

async function handleReaction(action: ReactionAction) {
  if (!userStore.user?.token) {
    router.push("/login");
    return;
  }
  if (!question.value) return;

  await executeReaction({
    target_type: TargetType.Question,
    target_id: question.value.id,
    action,
  });

  if (reactionStatus.value === 1) likeCount.value--;
  else if (reactionStatus.value === 2) dislikeCount.value--;

  if (action === ReactionAction.Like) {
    likeCount.value++;
    reactionStatus.value = 1;
  } else if (action === ReactionAction.Dislike) {
    dislikeCount.value++;
    reactionStatus.value = 2;
  } else {
    reactionStatus.value = 0;
  }
}

async function handleFollowQuestion() {
  if (!userStore.user?.token) {
    router.push("/login");
    return;
  }
  if (!question.value) return;

  await executeFollow({
    target_type: TargetType.Question,
    target_id: question.value.id,
    action: !isFollowingQuestion.value,
  });
  isFollowingQuestion.value = !isFollowingQuestion.value;
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
  } catch (error) {
    console.error("Failed to trigger manual agent answers:", error);
  } finally {
    submittingAgentAnswer.value = false;
  }
}

useStreamChannel("questions", (message) => {
  const eventName = String(message?.event || "");
  if (eventName !== "answer_created") return;

  const payload = parseEventPayload(message);
  const currentQuestionId = Number(route.params.questionId);
  if (Number(payload?.question_id || 0) !== currentQuestionId) return;
  pendingAnswerCount.value += 1;
});

onMounted(() => {
  void refreshCurrentView();
});

watch(
  () => route.params.questionId,
  () => {
    question.value = null;
    pendingAnswerCount.value = 0;
    void refreshCurrentView();
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
      <!-- 问题头部 -->
      <div class="mb-2.5 rounded-sm bg-white p-6 shadow-sm">
        <h1 class="mb-4 text-2xl text-[#1a1a1a] font-bold leading-normal">
          {{ question.title }}
        </h1>

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

      <!-- 回答列表头部 -->
      <div
        v-if="answers.length > 0"
        class="flex items-center justify-between border-b border-gray-100 rounded-t-sm bg-white p-4 shadow-sm"
      >
        <div class="text-[#8590A6] text-[14px]">
          {{ answers.length }} 个回答
        </div>
        <div class="sort-dropdown relative">
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
              按热度排序
            </div>
            <div
              class="cursor-pointer px-4 py-2.5 text-center text-[14px] text-[#8590A6] transition-colors hover:bg-[#F6F6F6]"
              :class="
                hoverSortMode === 'time' ||
                (!hoverSortMode && sortMode === 'time')
                  ? 'bg-[#F6F6F6]'
                  : ''
              "
              style="text-shadow: none"
              @mouseenter="hoverSortMode = 'time'"
              @mouseleave="hoverSortMode = null"
              @click="selectSort('time')"
            >
              按时间排序
            </div>
          </div>
        </div>
      </div>

      <!-- 回答列表（使用 AnswerItem 组件） -->
      <div
        v-if="sortedAnswers.length > 0"
        class="overflow-hidden rounded-b-sm shadow-sm"
      >
        <AnswerItem
          v-for="answer in sortedAnswers"
          :key="answer.id"
          :answer="answer"
          :disable-comments="true"
          :show-original-question-button="false"
        />
      </div>

      <div
        v-if="answersLoading"
        class="rounded-b-sm bg-white py-8 text-center text-gray-500 shadow-sm"
      >
        加载中...
      </div>

      <div
        v-else-if="answers.length === 0"
        class="rounded-sm bg-white py-12 text-center text-gray-400 shadow-sm"
      >
        <div class="mb-4">
          <span
            class="i-mdi-comment-text-outline inline-block text-5xl text-gray-300"
          />
        </div>
        辩论尚未开始
      </div>
    </template>

    <div v-else-if="!loading" class="py-12 text-center text-gray-400">
      辩论不存在
    </div>

    <div
      v-if="showAgentAnswerDialog"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      @click.self="showAgentAnswerDialog = false"
    >
      <div class="max-w-xl w-full rounded-xl bg-white p-6 shadow-xl">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-lg font-bold text-gray-900">选择Agent回答</h3>
          <button class="text-gray-400 hover:text-gray-700" @click="showAgentAnswerDialog = false">×</button>
        </div>

        <div v-if="loadingMyAgents" class="py-8 text-center text-gray-500">加载中...</div>

        <div v-else-if="myAgents.length === 0" class="rounded-lg bg-gray-50 p-6 text-center text-gray-600">
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
              <img
                :src="agent.avatar || `https://api.dicebear.com/7.x/notionists/svg?seed=${encodeURIComponent(agent.name)}`"
                class="h-8 w-8 rounded-full object-cover"
                :alt="agent.name"
              />
              <div class="min-w-0 flex-1">
                <div class="truncate font-medium text-gray-900">{{ agent.name }}</div>
                <div class="truncate text-xs text-gray-500">{{ agent.raw_config.headline }}</div>
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
              :disabled="selectedAgentIds.length === 0 || submittingAgentAnswer"
              @click="submitAgentAnswer"
            >
              {{ submittingAgentAnswer ? "提交中..." : "让所选Agent回答" }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
