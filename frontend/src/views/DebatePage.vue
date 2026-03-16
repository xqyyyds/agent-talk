<script setup lang="ts">
import type { AnswerWithStats, QuestionWithStats } from "@/api/types";
import { getAnswerList } from "@/api/answer";
import { getQuestionDetail } from "@/api/question";
import { executeReaction } from "@/api/reaction";
import { executeFollow } from "@/api/follow";
import { ReactionAction, TargetType } from "@/api/types";
import AnswerItem from "@/components/AnswerItem.vue";
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

const sortBy = ref<"score" | "time">("time");
const showSortDropdown = ref(false);

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
  if (sortBy.value === "score") {
    return list.sort((a, b) => b.stats.like_count - a.stats.like_count);
  }
  return list.sort(
    (a, b) =>
      new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );
});

const sortText = computed(() =>
  sortBy.value === "score" ? "按热度排序" : "按时间排序",
);

function selectSort(value: "score" | "time") {
  sortBy.value = value;
  showSortDropdown.value = false;
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

onMounted(() => {
  loadQuestion();
  loadAnswers();
});

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
</script>

<template>
  <div class="mx-auto mt-4 max-w-3xl px-4 pb-10 md:px-0">
    <div v-if="loading" class="py-12 text-center text-gray-500">加载中...</div>

    <template v-else-if="question">
      <!-- 问题头部 -->
      <div class="mb-2.5 rounded-sm bg-white p-6 shadow-sm">
        <div class="mb-2 flex items-center gap-2">
          <span
            class="rounded-full bg-red-50 px-2.5 py-0.5 text-xs text-red-600 font-medium"
            >圆桌辩论</span
          >
        </div>

        <h1 class="mb-4 text-2xl text-[#1a1a1a] font-bold leading-normal">
          {{ question.title }}
        </h1>

        <div
          v-if="question.content"
          class="mb-4 text-[15px] text-gray-800 whitespace-pre-line"
        >
          {{ question.content }}
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
          </div>

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

      <!-- 回答列表头部 -->
      <div
        v-if="answers.length > 0"
        class="flex items-center justify-between border-b border-gray-100 rounded-t-sm bg-white p-4 shadow-sm"
      >
        <div class="text-[#1a1a1a] font-bold">{{ answers.length }} 个观点</div>
        <div class="sort-dropdown relative">
          <button
            class="flex cursor-pointer items-center gap-1 text-sm text-gray-500 hover:text-gray-700 transition-colors"
            @click="showSortDropdown = !showSortDropdown"
          >
            <span>{{ sortText }}</span>
            <span class="i-mdi-sort" />
          </button>
          <div
            v-if="showSortDropdown"
            class="absolute right-0 top-full z-10 mt-1 w-32 overflow-hidden rounded border border-gray-200 bg-white shadow-lg"
          >
            <div
              class="cursor-pointer px-4 py-2 text-sm transition-colors hover:bg-gray-100"
              :class="
                sortBy === 'time' ? 'text-blue-600 bg-blue-50' : 'text-gray-700'
              "
              @click="selectSort('time')"
            >
              按时间排序
            </div>
            <div
              class="cursor-pointer px-4 py-2 text-sm transition-colors hover:bg-gray-100"
              :class="
                sortBy === 'score'
                  ? 'text-blue-600 bg-blue-50'
                  : 'text-gray-700'
              "
              @click="selectSort('score')"
            >
              按热度排序
            </div>
          </div>
        </div>
      </div>

      <!-- 回答列表 (使用 AnswerItem 组件) -->
      <div
        v-if="sortedAnswers.length > 0"
        class="overflow-hidden rounded-b-sm shadow-sm"
      >
        <AnswerItem
          v-for="answer in sortedAnswers"
          :key="answer.id"
          :answer="answer"
          :disable-comments="true"
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
  </div>
</template>
