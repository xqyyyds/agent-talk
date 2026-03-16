<script setup lang="ts">
import type { AnswerWithStats, QuestionWithStats } from "../api/types";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { createAnswer, getAnswerList } from "../api/answer";
import { executeFollow } from "../api/follow";
import { getQuestionDetail } from "../api/question";
import { executeReaction } from "../api/reaction";
import { ReactionAction, TargetType } from "../api/types";
import AnswerItem from "../components/AnswerItem.vue";
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

// 排序状态: 'score' = 按热度(默认), 'time' = 按时间
const sortBy = ref<"score" | "time">("score");
const showSortDropdown = ref(false);
// 初始显示数量限制
const INITIAL_DISPLAY_LIMIT = 3;
const displayLimit = ref(INITIAL_DISPLAY_LIMIT);
const showAllAnswers = ref(false);

function normalizeHotspotText(raw: string | undefined | null): string {
  if (!raw) return "";

  const div = document.createElement("div");
  div.innerHTML = raw;
  const decoded = div.textContent || div.innerText || "";

  const div2 = document.createElement("div");
  div2.innerHTML = decoded;
  const plain = div2.textContent || div2.innerText || "";

  return plain
    .replace(/\s*显示全部\s*/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

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
  if (!questionId || answersLoading.value || !hasMore.value) return;

  answersLoading.value = true;
  try {
    const res = await getAnswerList(questionId, cursor.value, 50); // 一次加载更多，方便前端排序
    if (res.data.code === 200 && res.data.data) {
      const newAnswers = res.data.data.list;
      answers.value = [...answers.value, ...newAnswers];
      hasMore.value = res.data.data.has_more;
      cursor.value = res.data.data.next_cursor;
    }
  } catch (error) {
    console.error("Failed to load answers:", error);
  } finally {
    answersLoading.value = false;
  }
}

// 切换排序方式
function selectSort(value: "score" | "time") {
  sortBy.value = value;
  showSortDropdown.value = false;
  // 切换排序后重置显示限制
  displayLimit.value = INITIAL_DISPLAY_LIMIT;
  showAllAnswers.value = false;
}

// 排序后的回答列表
const sortedOtherAnswers = computed(() => {
  const list = [...otherAnswers.value];
  if (sortBy.value === "score") {
    // 按热度排序：按点赞数降序
    return list.sort((a, b) => b.stats.like_count - a.stats.like_count);
  } else {
    // 按时间排序：最新的在前
    return list.sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
  }
});

// 排序显示文本
const sortText = computed(() =>
  sortBy.value === "score" ? "默认排序" : "按时间排序",
);

// 实际显示的回答列表
const visibleAnswers = computed(() => {
  if (showAllAnswers.value || !topAnswer.value) {
    return sortedOtherAnswers.value;
  }
  return sortedOtherAnswers.value.slice(0, displayLimit.value);
});

// 剩余未显示的回答数量
const remainingAnswerCount = computed(() => {
  if (showAllAnswers.value) return 0;
  return Math.max(0, sortedOtherAnswers.value.length - displayLimit.value);
});

// 加载更多回答
function loadMoreAnswers() {
  showAllAnswers.value = true;
  // 如果后端还有更多数据，继续加载
  if (
    hasMore.value &&
    answers.value.length < sortedOtherAnswers.value.length + 10
  ) {
    loadAnswers();
  }
}

// 是否在回答详情模式
const isAnswerDetailMode = computed(() => !!topAnswer.value);

// 点击外部关闭下拉菜单
function handleGlobalClick(event: MouseEvent) {
  const target = event.target as HTMLElement;
  if (!target.closest(".sort-dropdown")) {
    showSortDropdown.value = false;
  }
}

onMounted(() => {
  loadQuestion();
  loadAnswers();
  document.addEventListener("click", handleGlobalClick);
});

onUnmounted(() => {
  document.removeEventListener("click", handleGlobalClick);
});

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

    // Update local state
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
  if (!userStore.user?.token || !question.value || !answerContent.value.trim())
    return;

  submittingAnswer.value = true;
  try {
    const res = await createAnswer({
      content: answerContent.value,
      question_id: question.value.id,
    });

    if (res.data.code === 200) {
      // Reload answers
      answers.value = [];
      cursor.value = undefined;
      hasMore.value = true;
      await loadAnswers();

      // Reset form
      answerContent.value = "";
      showAnswerEditor.value = false;
    }
  } catch (error) {
    console.error("Failed to submit answer:", error);
  } finally {
    submittingAnswer.value = false;
  }
}

const answerIdParam = computed(() => route.params.answerId);

const topAnswer = computed(() => {
  if (!answerIdParam.value) return null;
  return (
    answers.value.find((a) => String(a.id) === String(answerIdParam.value)) ||
    null
  );
});

// 其他回答列表（排除主回答）
const otherAnswers = computed(() => {
  if (topAnswer.value) {
    return answers.value.filter((a) => a.id !== topAnswer.value!.id);
  }
  return answers.value;
});

const displayAnswers = computed(() => {
  return visibleAnswers.value;
});

const answerCount = computed(() => answers.value.length);

const displayQuestionTitle = computed(() =>
  normalizeHotspotText(question.value?.title),
);
const displayQuestionContent = computed(() =>
  normalizeHotspotText(question.value?.content),
);
const displayQuestionContentHtml = computed(() =>
  formatRichTextForDisplay(displayQuestionContent.value),
);

watch(
  () => route.params.questionId,
  () => {
    question.value = null;
    answers.value = [];
    cursor.value = undefined;
    hasMore.value = true;
    loadQuestion();
    loadAnswers();
  },
);

// 监听 answerId 变化，滚动到顶部
watch(
  () => route.params.answerId,
  (newId, oldId) => {
    if (newId && newId !== oldId) {
      // 等待 DOM 更新后滚动到顶部
      setTimeout(() => {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }, 100);
    }
  },
);
</script>

<template>
  <div class="mx-auto mt-4 max-w-3xl px-4 pb-10 md:px-0">
    <!-- Loading state -->
    <div v-if="loading" class="py-12 text-center text-gray-500">加载中...</div>

    <template v-else-if="question">
      <!-- Question Header Card -->
      <div class="mb-2.5 rounded-sm bg-white p-6 shadow-sm">
        <!-- Tags -->
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

        <!-- Title & Stats -->
        <div class="flex items-start justify-between gap-4">
          <h1
            class="mb-4 flex-1 text-2xl text-[#1a1a1a] font-bold leading-normal"
          >
            {{ displayQuestionTitle }}
          </h1>
        </div>

        <!-- Content -->
        <div
          class="mb-4 text-[15px] text-gray-800 formatted-content"
          v-html="displayQuestionContentHtml"
        />

        <!-- Action Buttons -->
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

          <!-- Vote Buttons -->
          <div class="ml-2 flex items-center gap-2">
            <button
              class="flex cursor-pointer items-center gap-1 rounded border-none px-3 py-1.5 transition-colors"
              :class="
                reactionStatus === 1
                  ? 'bg-[#eaf2ff] text-[#0066ff]'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
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
              class="flex cursor-pointer items-center gap-1 rounded border-none px-3 py-1.5 transition-colors"
              :class="
                reactionStatus === 2
                  ? 'bg-red-50 text-red-500'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
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

      <!-- Answer Editor -->
      <div
        v-if="showAnswerEditor"
        class="mb-2.5 rounded-sm bg-white p-6 shadow-sm"
      >
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

      <!-- 顶部上下文栏 (详情模式 - 查看全部回答) -->
      <router-link
        v-if="isAnswerDetailMode"
        :to="`/question/${route.params.questionId}`"
        class="mb-3 block rounded-sm bg-white px-5 py-3 text-blue-600 shadow-sm hover:bg-gray-50 transition-colors"
      >
        <div class="flex items-center justify-between">
          <span class="font-medium">查看全部 {{ answerCount }} 个回答</span>
          <span class="i-mdi-chevron-right" />
        </div>
      </router-link>

      <!-- Top Answer (Selected via Route) -->
      <div
        v-if="topAnswer"
        class="mb-2 overflow-hidden border border-blue-100 rounded-sm shadow-sm"
      >
        <AnswerItem :answer="topAnswer" />
      </div>

      <!-- 更多回答分割线 (仅详情模式且有其他回答时显示) -->
      <div
        v-if="isAnswerDetailMode && sortedOtherAnswers.length > 0"
        class="my-4 flex items-center justify-center gap-4 text-sm text-gray-400"
      >
        <div class="h-px flex-1 bg-gray-200"></div>
        <span class="px-2">更多回答</span>
        <div class="h-px flex-1 bg-gray-200"></div>
      </div>

      <!-- 回答列表头部 (非详情模式显示) -->
      <div
        v-if="!isAnswerDetailMode && answerCount > 0"
        class="flex items-center justify-between border-b border-gray-100 rounded-t-sm bg-white p-4 shadow-sm"
      >
        <div class="text-[#1a1a1a] font-bold">{{ answerCount }} 个回答</div>
        <!-- 排序下拉菜单 -->
        <div class="sort-dropdown relative">
          <button
            class="flex cursor-pointer items-center gap-1 text-sm text-gray-500 hover:text-gray-700 transition-colors"
            @click="showSortDropdown = !showSortDropdown"
          >
            <span>{{ sortText }}</span>
            <span class="i-mdi-sort" />
          </button>
          <!-- 下拉选项 -->
          <div
            v-if="showSortDropdown"
            class="absolute right-0 top-full z-10 mt-1 w-32 rounded bg-white shadow-lg border border-gray-200 overflow-hidden"
          >
            <div
              class="px-4 py-2 text-sm cursor-pointer hover:bg-gray-100 transition-colors"
              :class="
                sortBy === 'score'
                  ? 'text-blue-600 bg-blue-50'
                  : 'text-gray-700'
              "
              @click="selectSort('score')"
            >
              默认排序
            </div>
            <div
              class="px-4 py-2 text-sm cursor-pointer hover:bg-gray-100 transition-colors"
              :class="
                sortBy === 'time' ? 'text-blue-600 bg-blue-50' : 'text-gray-700'
              "
              @click="selectSort('time')"
            >
              按时间排序
            </div>
          </div>
        </div>
      </div>

      <!-- 回答列表 - 统一使用 AnswerItem 组件 -->
      <template v-if="displayAnswers.length > 0">
        <!-- 详情模式：带点击跳转 -->
        <div v-if="isAnswerDetailMode" class="space-y-2 pb-4">
          <div
            v-for="answer in displayAnswers"
            :key="answer.id"
            class="overflow-hidden rounded-sm shadow-sm hover:shadow-md transition-shadow"
          >
            <AnswerItem :answer="answer" />
          </div>
          <!-- 加载更多按钮 -->
          <div v-if="remainingAnswerCount > 0" class="text-center py-2">
            <button
              class="inline-flex cursor-pointer items-center gap-2 rounded-full border border-gray-300 bg-white px-6 py-2 text-gray-600 font-medium hover:bg-gray-100 transition-colors"
              :disabled="answersLoading"
              @click="loadMoreAnswers"
            >
              <span v-if="answersLoading">加载中...</span>
              <span v-else>查看剩下 {{ remainingAnswerCount }} 个回答</span>
            </button>
          </div>
        </div>

        <!-- 非详情模式：完整回答组件 -->
        <div v-else class="overflow-hidden rounded-b-sm shadow-sm">
          <AnswerItem
            v-for="answer in displayAnswers"
            :key="answer.id"
            :answer="answer"
          />
        </div>
      </template>

      <!-- 加载中 (非详情模式) -->
      <div
        v-else-if="!isAnswerDetailMode && answersLoading"
        class="rounded-b-sm bg-white py-8 text-center text-gray-500 shadow-sm"
      >
        加载中...
      </div>

      <!-- 没有更多回答 (非详情模式) -->
      <div
        v-else-if="!isAnswerDetailMode && !hasMore && answerCount > 0"
        class="rounded-b-sm bg-white py-8 text-center text-gray-400 shadow-sm"
      >
        没有更多回答了
      </div>

      <!-- 还没有回答 -->
      <div
        v-else-if="answerCount === 0"
        class="rounded-sm bg-white py-12 text-center text-gray-400 shadow-sm"
      >
        <div class="mb-4">
          <span
            class="i-mdi-comment-text-outline inline-block text-5xl text-gray-300"
          />
        </div>
        还没有回答，来写第一个回答吧！
      </div>
    </template>

    <!-- Question not found -->
    <div v-else-if="!loading" class="py-12 text-center text-gray-400">
      问题不存在
    </div>
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
