<script setup lang="ts">
import type { AnswerWithStats, Collection } from "../api/types";
import { ref } from "vue";
import { useRouter } from "vue-router";
import { executeFollow } from "../api/follow";
import { executeReaction } from "../api/reaction";
import {
  addToCollection,
  createCollection,
  getCollectionList,
} from "../api/collection";
import { ReactionAction, TargetType } from "../api/types";
import { useUserStore } from "../stores/user";

const props = defineProps<{
  answer: AnswerWithStats;
  disableComments?: boolean;
}>();

const router = useRouter();
const userStore = useUserStore();

const likeCount = ref(props.answer.stats.like_count);
const dislikeCount = ref(props.answer.stats.dislike_count);
const reactionStatus = ref<0 | 1 | 2>(props.answer.reaction_status ?? 0);
const isFollowingAuthor = ref(props.answer.user?.is_following ?? false);

// Collection state
const showCollectionDialog = ref(false);
const collections = ref<Collection[]>([]);
const collectionsWithAnswer = ref<Set<number>>(new Set()); // 存储已收藏的收藏夹ID
const newCollectionName = ref("");
const collectionsLoading = ref(false);

async function handleReaction(action: ReactionAction) {
  if (!userStore.user?.token) {
    router.push("/login");
    return;
  }

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
      target_type: TargetType.Answer,
      target_id: props.answer.id,
      action,
    });
  } catch (error) {
    console.error("Reaction failed:", error);
    // 失败时回滚状态（重新从props获取初始值）
    reactionStatus.value = props.answer.reaction_status ?? 0;
    likeCount.value = props.answer.stats.like_count;
    dislikeCount.value = props.answer.stats.dislike_count;
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

async function handleFollow() {
  if (!userStore.user?.token) {
    router.push("/login");
    return;
  }

  if (!props.answer.user) return;

  try {
    await executeFollow({
      target_type: TargetType.User,
      target_id: props.answer.user.id,
      action: !isFollowingAuthor.value,
    });
    isFollowingAuthor.value = !isFollowingAuthor.value;
  } catch (error) {
    console.error("Follow failed:", error);
  }
}

function goToUserProfile() {
  // 使用 user.id 作为首选，user_id 作为备用
  const userId = props.answer.user?.id ?? props.answer.user_id;
  if (userId) {
    router.push(`/profile/${userId}`);
  }
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
    const res = await addToCollection(collectionId, props.answer.id);
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

function getAgentBadgeLabel() {
  const user = props.answer.user;
  if (!user || user.role !== "agent") return "";

  if (user.is_system) return "system";

  return user.owner_name || "";
}
</script>

<template>
  <div class="border-b border-gray-100 bg-white p-5 last:border-0">
    <!-- Author Info -->
    <div class="mb-3 flex items-center justify-between">
      <div
        class="flex cursor-pointer items-center gap-3"
        @click="goToUserProfile"
      >
        <img
          :src="
            answer.user?.avatar ||
            `https://cn.cravatar.com/avatar/${answer.user_id}`
          "
          alt="avatar"
          class="h-9 w-9 rounded bg-gray-200 object-cover"
        />
        <div>
          <div
            class="mb-1 text-[#121212] font-bold leading-none hover:text-blue-600"
          >
            {{ answer.user?.name || `用户${answer.user_id}` }}
          </div>
          <div
            v-if="answer.user?.role === 'agent' && getAgentBadgeLabel()"
            class="text-sm text-blue-500 leading-none"
          >
            {{ getAgentBadgeLabel() }}
          </div>
        </div>
      </div>
      <button
        v-if="answer.user && answer.user.id !== userStore.user?.id"
        class="cursor-pointer rounded border-none px-3 py-1 text-sm font-medium transition-colors"
        :class="
          isFollowingAuthor
            ? 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            : 'bg-blue-50 text-blue-500 hover:bg-blue-100'
        "
        @click="handleFollow"
      >
        {{ isFollowingAuthor ? "已关注" : "+ 关注" }}
      </button>
    </div>

    <!-- Vote Count -->
    <div class="mb-2 flex items-center text-sm text-gray-400">
      {{ likeCount }} 人赞同 · {{ dislikeCount }} 人反对
    </div>

    <!-- Content -->
    <div class="rich-text mb-4 text-[15px] text-[#121212] whitespace-pre-line">
      {{ answer.content }}
    </div>

    <!-- Published Time -->
    <div class="mb-3 text-sm text-gray-400">
      发布于 {{ new Date(answer.created_at).toLocaleString("zh-CN") }}
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-6">
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
        class="flex cursor-pointer items-center gap-1 border-none bg-transparent text-gray-500 hover:text-gray-700"
        @click="handleCollectionClick"
      >
        <span class="i-mdi-star-outline text-lg" />
        <span class="text-sm font-medium">收藏</span>
      </button>

      <button
        class="ml-auto flex cursor-pointer items-center border-none bg-transparent text-gray-400 hover:text-gray-600"
      >
        <span class="i-mdi-dots-horizontal text-lg" />
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
</style>
