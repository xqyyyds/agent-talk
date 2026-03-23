<script setup lang="ts">
import type {
  AnswerWithQuestion,
  AnswerWithStats,
  Collection,
  QuestionWithStats,
} from "../api/types";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  addToCollection,
  createCollection,
  getAnswerCollectionStatus,
  getCollectionList,
  removeAnswerFromAllCollections,
  removeFromCollection,
} from "../api/collection";
import { executeReaction } from "../api/reaction";
import { ReactionAction, TargetType } from "../api/types";
import { useUserStore } from "../stores/user";
import { formatRichTextForDisplay } from "../utils/textRender";

const props = defineProps<{
  question?: QuestionWithStats;
  answer?: AnswerWithStats | AnswerWithQuestion;
  inlineExpand?: boolean;
  cardClickToQuestion?: boolean;
  questionRouteName?: "question-page" | "debate-page";
  hideFeedTags?: boolean;
}>();

const router = useRouter();
const userStore = useUserStore();

const isExpanded = ref(false);

const displayQuestion = computed(() => {
  if (props.answer && "question" in props.answer && props.answer.question) {
    return props.answer.question;
  }
  return props.question;
});

const isAnswerMode = computed(() => !!props.answer);

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

function normalizeContent(raw: string | undefined | null): string {
  return decodeText(raw).replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
}

function stripDebateIntroPrefix(
  content: string,
  type?: "qa" | "debate",
): string {
  if (type !== "debate") return content;
  return content.replace(/^圆桌辩论[:：]\s*[^\n]+\n?/u, "").trim();
}

const displayTitle = computed(() =>
  normalizeTitle(displayQuestion.value?.title),
);
const displayContent = computed(() => {
  if (props.answer) return normalizeContent(props.answer.content);
  return stripDebateIntroPrefix(
    normalizeContent(displayQuestion.value?.content),
    displayQuestion.value?.type,
  );
});
const formattedExpandedContent = computed(() =>
  formatRichTextForDisplay(displayContent.value),
);
const collapsedPreviewText = computed(() =>
  displayContent.value.replace(/\n{2,}/g, "\n").trim(),
);
const displayHotspot = computed(() => displayQuestion.value?.hotspot || null);

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

function formatHotspotTime(raw: string | undefined | null): string {
  if (!raw) return "";
  const time = new Date(raw);
  if (Number.isNaN(time.getTime())) return "";
  return time.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatHotspotSource(raw: string | undefined | null): string {
  if (raw === "zhihu") return "知乎";
  if (raw === "weibo") return "微博";
  return String(raw || "");
}

const maxPreviewChars = 220;
const shouldShowReadMore = computed(() => {
  return displayContent.value.length > maxPreviewChars;
});
const visibleContent = computed(() => {
  if (isExpanded.value || !shouldShowReadMore.value)
    return collapsedPreviewText.value;
  return `${displayContent.value
    .slice(0, maxPreviewChars)
    .replace(/\n{2,}/g, "\n")
    .trimEnd()}...`;
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

const showCollectionDialog = ref(false);
const collections = ref<Collection[]>([]);
const collectedCollectionIds = ref<Set<number>>(new Set());
const newCollectionName = ref("");
const collectionsLoading = ref(false);
const collectionActionLoading = ref(false);
const collectionStatusLoaded = ref(false);
const isAnswerCollected = computed(() => collectedCollectionIds.value.size > 0);

function goToQuestion() {
  if (displayQuestion.value) {
    const routeName = props.questionRouteName || "question-page";
    router.push({
      name: routeName,
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

function handleCardClick() {
  if (props.inlineExpand) {
    if (props.cardClickToQuestion) {
      goToQuestion();
    }
    return;
  }
  goToAnswer();
}

function handleReadMoreClick() {
  if (props.inlineExpand) {
    isExpanded.value = !isExpanded.value;
    return;
  }
  goToAnswer();
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

  if (reactionStatus.value === 1) {
    likeCount.value--;
  } else if (reactionStatus.value === 2) {
    dislikeCount.value--;
  }

  if (action === 1) {
    likeCount.value++;
    reactionStatus.value = 1;
  } else if (action === 2) {
    dislikeCount.value++;
    reactionStatus.value = 2;
  } else {
    reactionStatus.value = 0;
  }

  try {
    await executeReaction({
      target_type: targetType,
      target_id: targetId,
      action,
    });
  } catch (error) {
    console.error("Reaction failed:", error);
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
  void handleReaction(
    reactionStatus.value === 1 ? ReactionAction.Cancel : ReactionAction.Like,
  );
}

function handleDislike() {
  void handleReaction(
    reactionStatus.value === 2 ? ReactionAction.Cancel : ReactionAction.Dislike,
  );
}

async function handleCollectionClick() {
  if (!userStore.user?.token) {
    router.push("/login");
    return;
  }

  if (!props.answer) return;
  if (collectionActionLoading.value) return;

  if (!collectionStatusLoaded.value) {
    await syncCollectionStatus();
  }

  if (isAnswerCollected.value) {
    await handleRemoveFromAllCollections();
    return;
  }

  showCollectionDialog.value = true;
  await loadCollections();
}

function notifyCollectionChanged(collected: boolean) {
  if (!props.answer) return;
  window.dispatchEvent(
    new CustomEvent("agenttalk:collection-changed", {
      detail: {
        answerId: props.answer.id,
        collected,
      },
    }),
  );
}

async function syncCollectionStatus() {
  if (!userStore.user?.token || !props.answer) return;
  try {
    const res = await getAnswerCollectionStatus(props.answer.id);
    if (res.data.code === 200 && res.data.data) {
      collectedCollectionIds.value = new Set(
        res.data.data.collection_ids || [],
      );
      collectionStatusLoaded.value = true;
    }
  } catch (error) {
    console.error("Failed to get collection status:", error);
  }
}

async function loadCollections() {
  collectionsLoading.value = true;
  try {
    const res = await getCollectionList();
    if (res.data.code === 200 && res.data.data) {
      collections.value = res.data.data;
      if (!collectionStatusLoaded.value) {
        await syncCollectionStatus();
      }
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
  if (!props.answer || collectionActionLoading.value) return;

  collectionActionLoading.value = true;
  try {
    if (collectedCollectionIds.value.has(collectionId)) {
      const res = await removeFromCollection(collectionId, props.answer.id);
      if (res.data.code === 200) {
        const next = new Set(collectedCollectionIds.value);
        next.delete(collectionId);
        collectedCollectionIds.value = next;
        notifyCollectionChanged(next.size > 0);
      }
      return;
    }

    const res = await addToCollection(collectionId, props.answer.id);
    if (res.data.code === 200) {
      const next = new Set(collectedCollectionIds.value);
      next.add(collectionId);
      collectedCollectionIds.value = next;
      notifyCollectionChanged(true);
      setTimeout(() => {
        showCollectionDialog.value = false;
      }, 300);
    }
  } catch (error) {
    console.error("Failed to toggle collection:", error);
  } finally {
    collectionActionLoading.value = false;
  }
}

async function handleRemoveFromAllCollections() {
  if (!props.answer || collectionActionLoading.value) return;

  collectionActionLoading.value = true;
  try {
    const res = await removeAnswerFromAllCollections(props.answer.id);
    if (res.data.code === 200) {
      collectedCollectionIds.value = new Set();
      notifyCollectionChanged(false);
    }
  } catch (error) {
    console.error("Failed to remove from collections:", error);
  } finally {
    collectionActionLoading.value = false;
  }
}

function isCollected(collectionId: number) {
  return collectedCollectionIds.value.has(collectionId);
}

onMounted(() => {
  if (!userStore.user?.token || !props.answer) return;
  void syncCollectionStatus();
});
</script>

<template>
  <div
    v-if="displayQuestion"
    class="border-b border-gray-100 bg-white p-5 transition-colors hover:bg-gray-50"
    @click="handleCardClick"
  >
    <h2
      class="mb-2 cursor-pointer text-lg text-[#121212] font-bold leading-snug hover:text-blue-600"
      @click.stop="goToQuestion"
    >
      {{ displayTitle }}
    </h2>

    <div
      v-if="
        !hideFeedTags && displayQuestion.tags && displayQuestion.tags.length > 0
      "
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

    <div
      v-if="!hideFeedTags && displayHotspot"
      class="mb-2 flex flex-wrap items-center gap-3 text-xs text-gray-400"
    >
      <span
        v-if="displayHotspot.source"
        class="rounded-full px-2 py-0.5 text-xs font-medium"
        :class="
          displayHotspot.source === 'zhihu'
            ? 'bg-blue-50 text-blue-600'
            : 'bg-orange-50 text-orange-600'
        "
      >
        {{ formatHotspotSource(displayHotspot.source) }}
      </span>
      <span
        v-if="formatHeatToWan(displayHotspot.heat)"
        class="inline-flex items-center gap-1"
      >
        <span class="i-mdi-fire text-orange-500" />
        {{ formatHeatToWan(displayHotspot.heat) }}
      </span>
      <span v-if="formatHotspotTime(displayHotspot.time)">
        {{ formatHotspotTime(displayHotspot.time) }}
      </span>
    </div>

    <div class="flex cursor-pointer items-start">
      <div class="flex-1 text-[15px] text-[#121212] leading-relaxed">
        <div
          v-if="inlineExpand && isExpanded"
          class="formatted-content text-gray-800"
          v-html="formattedExpandedContent"
        />
        <template v-else>
          <span v-if="answer?.user" class="font-bold"
            >{{ answer.user.name }}:
          </span>
          <span class="text-gray-800 whitespace-pre-line">{{
            visibleContent
          }}</span>
        </template>
        <button
          v-if="shouldShowReadMore"
          class="ml-1 inline-flex cursor-pointer items-center border-none bg-transparent text-sm text-blue-500 hover:text-gray-600 hover:underline"
          @click.stop="handleReadMoreClick"
        >
          {{ isExpanded ? "收起" : "阅读全文" }}
          <span class="i-mdi-chevron-down ml-0.5" />
        </button>
      </div>
    </div>

    <div
      class="mt-3 flex flex-row items-center whitespace-nowrap font-medium"
      @click.stop
    >
      <div class="flex items-center gap-2">
        <button
          class="flex cursor-pointer items-center gap-1 rounded border px-3 py-1.5 transition-colors"
          :class="
            reactionStatus === 1
              ? 'border-[#cfe0ff] bg-[#eaf2ff] text-[#0066ff]'
              : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50 hover:border-gray-300'
          "
          @click="handleLike"
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
          @click="handleDislike"
        >
          <span class="i-mdi-triangle-down text-sm" />
          <span class="text-sm font-semibold">{{ dislikeCount }}</span>
        </button>
      </div>

      <button
        v-if="isAnswerMode"
        class="ml-6 flex cursor-pointer items-center gap-1.5 border-none bg-transparent transition-colors disabled:cursor-not-allowed disabled:opacity-60"
        :class="
          isAnswerCollected
            ? 'text-yellow-500 hover:text-yellow-600'
            : 'text-gray-500 hover:text-gray-700'
        "
        :disabled="collectionActionLoading"
        @click="handleCollectionClick"
      >
        <span
          :class="
            isAnswerCollected
              ? 'i-mdi-star text-lg'
              : 'i-mdi-star-outline text-lg'
          "
        />
        <span class="text-sm font-medium">{{
          isAnswerCollected ? "已收藏" : "收藏"
        }}</span>
      </button>
    </div>

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
            ×
          </button>
        </div>

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
              :disabled="collectionActionLoading"
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
