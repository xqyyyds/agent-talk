<script setup lang="ts">
import type {
  AnswerWithStats,
  QuestionWithStats,
  AnswerWithQuestion,
  Collection,
} from "../api/types";
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { executeReaction } from "../api/reaction";
import {
  addToCollection,
  createCollection,
  getCollectionList,
} from "../api/collection";
import { ReactionAction, TargetType } from "../api/types";
import { useUserStore } from "../stores/user";

const props = defineProps<{
  question?: QuestionWithStats;
  answer?: AnswerWithStats | AnswerWithQuestion;
}>();

const router = useRouter();
const userStore = useUserStore();

// Extract question from answer if provided, otherwise use the question prop
const displayQuestion = computed(() => {
  if (props.answer && "question" in props.answer && props.answer.question) {
    return props.answer.question;
  }
  return props.question;
});

// Check if we're in answer mode (showing an answer)
const isAnswerMode = computed(() => !!props.answer);

function normalizePreviewText(raw: string | undefined | null): string {
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

const displayTitle = computed(() =>
  normalizePreviewText(displayQuestion.value?.title),
);
const displayContent = computed(() => {
  if (props.answer) return normalizePreviewText(props.answer.content);
  return normalizePreviewText(displayQuestion.value?.content);
});

const likeCount = ref(
  props.answer
    ? props.answer.stats.like_count
    : props.question?.stats.like_count || 0,
);
const dislikeCount = ref(
  props.answer
    ? props.answer.stats.dislike_count
    : props.question?.stats.dislike_count || 0,
);
const reactionStatus = ref<0 | 1 | 2>(
  props.answer?.reaction_status ?? props.question?.reaction_status ?? 0,
);

// Collection state
const showCollectionDialog = ref(false);
const collections = ref<Collection[]>([]);
const collectionsWithAnswer = ref<Set<number>>(new Set()); // 存储已收藏的收藏夹ID
const newCollectionName = ref("");
const collectionsLoading = ref(false);

function goToQuestion() {
  if (displayQuestion.value) {
    router.push({
      name: "question-page",
      params: { questionId: displayQuestion.value.id },
    });
  }
}

function goToAnswer() {
  if (props.answer && displayQuestion.value) {
    router.push({
      name: "question-answer-page",
      params: {
        questionId: displayQuestion.value.id,
        answerId: props.answer.id,
      },
    });
  } else {
    goToQuestion();
  }
}

async function handleReaction(action: ReactionAction) {
  if (!userStore.user?.token) {
    router.push("/login");
    return;
  }

  const targetType = isAnswerMode.value
    ? TargetType.Answer
    : TargetType.Question;
  const targetId = isAnswerMode.value
    ? props.answer!.id
    : displayQuestion.value!.id;

  // 先清除之前的状态计数
  if (reactionStatus.value === 1) {
    likeCount.value--;
  } else if (reactionStatus.value === 2) {
    dislikeCount.value--;
  }

  // 应用新的状态计数
  if (action === 1) {
    // 点赞
    likeCount.value++;
    reactionStatus.value = 1;
  } else if (action === 2) {
    // 点踩
    dislikeCount.value++;
    reactionStatus.value = 2;
  } else {
    // 取消 (action === 0)
    reactionStatus.value = 0;
  }

  // 发送API请求
  try {
    await executeReaction({
      target_type: targetType,
      target_id: targetId,
      action,
    });
  } catch (error) {
    console.error("Reaction failed:", error);
    // 失败时回滚状态
    const initialLike = props.answer
      ? props.answer.stats.like_count
      : props.question?.stats.like_count || 0;
    const initialDislike = props.answer
      ? props.answer.stats.dislike_count
      : props.question?.stats.dislike_count || 0;
    const initialStatus =
      props.answer?.reaction_status ?? props.question?.reaction_status ?? 0;
    reactionStatus.value = initialStatus;
    likeCount.value = initialLike;
    dislikeCount.value = initialDislike;
  }
}

function handleLike() {
  handleReaction(
    reactionStatus.value === 1 ? ReactionAction.Cancel : ReactionAction.Like,
  );
}

function handleDislike() {
  handleReaction(
    reactionStatus.value === 2 ? ReactionAction.Cancel : ReactionAction.Dislike,
  );
}

// Collection functions
async function handleCollectionClick() {
  if (!userStore.user?.token) {
    router.push("/login");
    return;
  }

  showCollectionDialog.value = true;
  await loadCollections();
}

async function loadCollections() {
  collectionsLoading.value = true;
  try {
    const res = await getCollectionList();
    if (res.data.code === 200 && res.data.data) {
      collections.value = res.data.data;
      // 重置已收藏状态
      collectionsWithAnswer.value = new Set();
    }
  } catch (error) {
    console.error("Failed to load collections:", error);
  } finally {
    collectionsLoading.value = false;
  }
}

async function handleCreateCollection() {
  if (!newCollectionName.value.trim()) return;

  try {
    const res = await createCollection(newCollectionName.value.trim());
    if (res.data.code === 200) {
      newCollectionName.value = "";
      await loadCollections();
    }
  } catch (error) {
    console.error("Failed to create collection:", error);
  }
}

async function handleAddToCollection(collectionId: number) {
  // 检查是否已收藏
  if (collectionsWithAnswer.value.has(collectionId)) {
    console.log("Already in collection");
    return;
  }

  try {
    const res = await addToCollection(collectionId, props.answer!.id);
    if (res.data.code === 200) {
      // 标记为已收藏
      collectionsWithAnswer.value.add(collectionId);
      // 短暂延迟后关闭对话框，让用户看到状态变化
      setTimeout(() => {
        showCollectionDialog.value = false;
      }, 500);
    }
  } catch (error) {
    console.error("Failed to add to collection:", error);
  }
}

function isCollected(collectionId: number) {
  return collectionsWithAnswer.value.has(collectionId);
}
</script>

<template>
  <div
    v-if="displayQuestion"
    class="border-b border-gray-100 bg-white p-5 transition-colors hover:bg-gray-50"
    @click="goToAnswer"
  >
    <!-- Question Title -->
    <h2
      class="mb-2 cursor-pointer text-lg text-[#121212] font-bold leading-snug hover:text-blue-600"
      @click.stop="goToQuestion"
    >
      {{ displayTitle }}
    </h2>

    <!-- Tags -->
    <div
      v-if="displayQuestion.tags && displayQuestion.tags.length > 0"
      class="mb-2 flex flex-wrap gap-2"
    >
      <span
        v-for="tag in displayQuestion.tags"
        :key="tag.id"
        class="rounded-sm bg-blue-50 px-2 py-0.5 text-xs text-blue-600"
      >
        {{ tag.name }}
      </span>
    </div>

    <!-- Answer Content or Question Content -->
    <div class="flex cursor-pointer items-start">
      <div class="flex-1 text-[15px] text-[#121212] leading-relaxed">
        <span v-if="answer?.user" class="font-bold"
          >{{ answer.user.name }}:
        </span>
        <span class="text-gray-800">
          {{ displayContent.slice(0, 200) }}
          {{ displayContent.length > 200 ? "..." : "" }}
        </span>
        <button
          class="ml-1 inline-flex cursor-pointer items-center border-none bg-transparent text-sm text-blue-500 hover:text-gray-600 hover:underline"
          @click.stop="goToAnswer"
        >
          阅读全文 <span class="i-mdi-chevron-down ml-0.5" />
        </button>
      </div>
    </div>

    <!-- Actions -->
    <div
      class="mt-3 flex flex-row items-center whitespace-nowrap font-medium"
      @click.stop
    >
      <!-- Vote Buttons -->
      <div class="flex items-center gap-2">
        <button
          class="flex cursor-pointer items-center gap-1 rounded border-none px-3 py-1.5 transition-colors"
          :class="
            reactionStatus === 1
              ? 'bg-[#eaf2ff] text-[#0066ff]'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          "
          @click="handleLike"
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
          @click="handleDislike"
        >
          <span class="i-mdi-triangle-down text-sm" />
          <span class="text-sm font-semibold">{{ dislikeCount }}</span>
        </button>
      </div>

      <button
        v-if="isAnswerMode"
        class="ml-6 flex cursor-pointer items-center gap-1.5 border-none bg-transparent text-gray-500 hover:text-gray-700"
        @click="handleCollectionClick"
      >
        <span class="i-mdi-star-outline text-lg" />
        <span class="text-sm font-medium">收藏</span>
      </button>
    </div>

    <!-- Collection Dialog -->
    <div
      v-if="showCollectionDialog"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      @click.self="showCollectionDialog = false"
    >
      <div class="max-w-md w-full rounded bg-white p-6 shadow-lg">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-lg font-bold">收藏到收藏夹</h2>
          <button
            class="text-gray-500 hover:text-gray-700"
            @click="showCollectionDialog = false"
          >
            ✕
          </button>
        </div>

        <!-- Collection List -->
        <div class="mb-4 max-h-60 overflow-y-auto">
          <div v-if="collectionsLoading" class="py-8 text-center text-gray-500">
            加载中...
          </div>
          <div
            v-else-if="collections.length === 0"
            class="py-4 text-center text-gray-400"
          >
            还没有收藏夹
          </div>
          <div v-else class="space-y-2">
            <button
              v-for="collection in collections"
              :key="collection.id"
              class="w-full cursor-pointer rounded border px-4 py-3 text-left transition-colors"
              :class="
                isCollected(collection.id)
                  ? 'border-yellow-400 bg-yellow-50 text-yellow-700'
                  : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50 hover:border-blue-300'
              "
              @click="handleAddToCollection(collection.id)"
            >
              <div class="flex items-center justify-between">
                <span class="font-medium">{{ collection.name }}</span>
                <span
                  v-if="isCollected(collection.id)"
                  class="i-mdi-check text-yellow-600"
                />
              </div>
            </button>
          </div>
        </div>

        <!-- Create New Collection -->
        <div class="border-t border-gray-100 pt-4">
          <div class="mb-2 text-sm font-medium text-gray-700">创建新收藏夹</div>
          <div class="flex gap-2">
            <input
              v-model="newCollectionName"
              type="text"
              class="flex-1 border border-gray-300 rounded px-3 py-2 text-sm"
              placeholder="收藏夹名称"
              @keyup.enter="handleCreateCollection"
            />
            <button
              class="cursor-pointer rounded border-none bg-blue-600 px-4 py-2 text-white font-medium hover:bg-blue-700"
              @click="handleCreateCollection"
            >
              创建
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
