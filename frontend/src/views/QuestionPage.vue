<script setup lang="ts">
import type { AnswerWithStats, QuestionWithStats } from "../api/types";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { createAnswer, getAnswerList } from "../api/answer";
import { executeFollow } from "../api/follow";
import { getQuestionDetail } from "../api/question";
import { executeReaction } from "../api/reaction";
import { ReactionAction, TargetType } from "../api/types";
import AnswerItem from "../components/AnswerItem.vue";
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
const hasMore = ref(true);
const cursor = ref<number | undefined>(undefined);

const likeCount = ref(0);
const dislikeCount = ref(0);
const reactionStatus = ref<0 | 1 | 2>(0);
const isFollowingQuestion = ref(false);

const showAnswerEditor = ref(false);
const answerContent = ref("");
const submittingAnswer = ref(false);
const isAnswerDetailMode = computed(() => !!route.params.answerId);

function normalizeHotspotText(raw: string | undefined | null): string {
  if (!raw) return "";
  const div = document.createElement("div");
  div.innerHTML = raw;
  const decoded = div.textContent || div.innerText || "";
  const div2 = document.createElement("div");
  div2.innerHTML = decoded;
  const plain = div2.textContent || div2.innerText || "";
  return plain.replace(/\s+/g, " ").trim();
}

const displayQuestionTitle = computed(() => normalizeHotspotText(question.value?.title));
const displayQuestionContent = computed(() => normalizeHotspotText(question.value?.content));
const displayQuestionContentHtml = computed(() => formatRichTextForDisplay(displayQuestionContent.value));

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

async function loadAnswers(reset = false) {
  const questionId = Number(route.params.questionId);
  if (!questionId) return;

  if (reset) {
    answers.value = [];
    cursor.value = undefined;
    hasMore.value = true;
  }

  if (answersLoading.value) return;
  if (!isAnswerDetailMode.value && !hasMore.value && !reset) return;

  answersLoading.value = true;
  try {
    const limit = isAnswerDetailMode.value ? 1 : 20;
    const res = await getAnswerList(
      questionId,
      isAnswerDetailMode.value ? undefined : cursor.value,
      limit,
    );

    if (res.data.code === 200 && res.data.data) {
      const newAnswers = res.data.data.list || [];
      if (isAnswerDetailMode.value) {
        answers.value = newAnswers.slice(0, 1);
        hasMore.value = false;
        cursor.value = undefined;
      } else {
        answers.value = reset ? newAnswers : [...answers.value, ...newAnswers];
        hasMore.value = res.data.data.has_more;
        cursor.value = res.data.data.next_cursor;
      }
    }
  } catch (error) {
    console.error("Failed to load answers:", error);
  } finally {
    answersLoading.value = false;
  }
}

const latestAnswer = computed(() => answers.value[0] || null);

const topAnswer = computed(() => latestAnswer.value);

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

function handleWriteAnswer() {
  if (!userStore.user?.token) {
    router.push("/login");
    return;
  }
  showAnswerEditor.value = true;
}

async function submitAnswer() {
  if (!userStore.user?.token || !question.value || !answerContent.value.trim()) return;

  submittingAnswer.value = true;
  try {
    const res = await createAnswer({
      content: answerContent.value,
      question_id: question.value.id,
    });

    if (res.data.code === 200) {
      await loadAnswers(true);
      answerContent.value = "";
      showAnswerEditor.value = false;
    }
  } catch (error) {
    console.error("Failed to submit answer:", error);
  } finally {
    submittingAnswer.value = false;
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

useStreamChannel("questions", (message) => {
  const eventName = String(message?.event || "");
  if (eventName !== "answer_created") return;

  const payload = parseEventPayload(message);
  const currentQuestionId = Number(route.params.questionId);
  if (Number(payload?.question_id || 0) !== currentQuestionId) return;

  void loadAnswers(true);
});

onMounted(async () => {
  await loadQuestion();
  await loadAnswers(true);
});

watch(
  () => route.params.questionId,
  async () => {
    question.value = null;
    answers.value = [];
    cursor.value = undefined;
    hasMore.value = true;
    await loadQuestion();
    await loadAnswers(true);
  },
);

watch(
  () => route.params.answerId,
  async () => {
    await loadAnswers(true);
  },
);
</script>

<template>
  <div class="mx-auto mt-4 max-w-3xl px-4 pb-10 md:px-0">
    <div v-if="loading" class="py-12 text-center text-gray-500">加载中...</div>

    <template v-else-if="question">
      <div class="mb-2.5 rounded-sm bg-white p-6 shadow-sm">
        <div v-if="question.tags && question.tags.length > 0" class="mb-4 flex flex-wrap gap-2">
          <span
            v-for="tag in question.tags"
            :key="tag.id"
            class="cursor-pointer rounded-full bg-blue-50 px-3 py-1 text-sm text-blue-600 font-medium hover:bg-blue-100"
          >
            {{ tag.name }}
          </span>
        </div>

        <h1 class="mb-4 text-2xl text-[#1a1a1a] font-bold leading-normal">
          {{ displayQuestionTitle }}
        </h1>

        <div class="mb-4 text-[15px] text-gray-800 formatted-content" v-html="displayQuestionContentHtml" />

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
              @click="handleWriteAnswer"
            >
              <span class="i-mdi-pencil-outline" />
              写回答
            </button>
          </div>

          <div class="ml-2 flex items-center gap-2">
            <button
              class="flex cursor-pointer items-center gap-1 rounded border-none px-3 py-1.5 transition-colors"
              :class="
                reactionStatus === 1
                  ? 'bg-[#eaf2ff] text-[#0066ff]'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              "
              @click="handleReaction(reactionStatus === 1 ? ReactionAction.Cancel : ReactionAction.Like)"
            >
              <span class="i-mdi-triangle text-sm" />
              <span class="text-sm font-semibold">{{ likeCount }}</span>
            </button>
            <button
              class="flex cursor-pointer items-center gap-1 rounded border-none px-3 py-1.5 transition-colors"
              :class="
                reactionStatus === 2
                  ? 'bg-red-50 text-red-500'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              "
              @click="handleReaction(reactionStatus === 2 ? ReactionAction.Cancel : ReactionAction.Dislike)"
            >
              <span class="i-mdi-triangle-down text-sm" />
              <span class="text-sm font-semibold">{{ dislikeCount }}</span>
            </button>
          </div>
        </div>
      </div>

      <div v-if="showAnswerEditor" class="mb-2.5 rounded-sm bg-white p-6 shadow-sm">
        <h3 class="mb-4 text-lg font-bold">写回答</h3>
        <textarea
          v-model="answerContent"
          class="mb-4 w-full border border-gray-300 rounded p-3 text-sm"
          rows="8"
          placeholder="写下你的回答..."
        />
        <div class="flex gap-2">
          <button
            class="cursor-pointer rounded border-none bg-blue-600 px-4 py-2 text-white font-medium disabled:bg-gray-300 hover:bg-blue-700"
            :disabled="submittingAnswer || !answerContent.trim()"
            @click="submitAnswer"
          >
            {{ submittingAnswer ? "提交中..." : "发布回答" }}
          </button>
          <button
            class="cursor-pointer border border-gray-300 rounded bg-white px-4 py-2 text-gray-700 font-medium hover:bg-gray-50"
            @click="showAnswerEditor = false"
          >
            取消
          </button>
        </div>
      </div>

      <template v-if="!isAnswerDetailMode">
        <div v-if="answers.length > 0" class="overflow-hidden rounded-sm bg-white shadow-sm">
          <div class="border-b border-gray-100 px-4 py-3 text-sm text-gray-500">
            全部回答（最新在前）
          </div>
          <div
            v-for="answer in answers"
            :key="answer.id"
            class="border-b border-gray-100 last:border-b-0"
          >
            <AnswerItem :answer="answer" />
          </div>
        </div>
        <div v-else class="rounded-sm bg-white py-12 text-center text-gray-400 shadow-sm">
          还没有回答，来写第一个回答吧！
        </div>

        <div v-if="hasMore" class="py-4 text-center">
          <button
            class="inline-flex cursor-pointer items-center gap-2 rounded-full border border-gray-300 bg-white px-6 py-2 text-gray-600 font-medium hover:bg-gray-100 transition-colors"
            :disabled="answersLoading"
            @click="loadAnswers()"
          >
            {{ answersLoading ? "加载中..." : "加载更多" }}
          </button>
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

        <div v-if="topAnswer" class="overflow-hidden rounded-sm bg-white shadow-sm">
          <div class="border-b border-gray-100 px-4 py-3 text-sm text-gray-500">
            最新回答（自动热更新）
          </div>
          <AnswerItem :answer="topAnswer" />
        </div>
        <div v-else class="rounded-sm bg-white py-12 text-center text-gray-400 shadow-sm">
          还没有回答，来写第一个回答吧！
        </div>
      </template>
    </template>

    <div v-else-if="!loading" class="py-12 text-center text-gray-400">问题不存在</div>
  </div>
</template>

<style scoped>
.formatted-content {
  word-break: break-word;
  overflow-wrap: anywhere;
}
.formatted-content :deep(a) {
  color: #175199;
  text-decoration: none;
}
.formatted-content :deep(a:hover) {
  text-decoration: underline;
}
</style>
