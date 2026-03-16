<script setup lang="ts">
import type { Comment, CommentWithStats } from "../api/types";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { createComment, getCommentList } from "../api/comment";
import { executeReaction } from "../api/reaction";
import { ReactionAction, TargetType } from "../api/types";
import { useUserStore } from "../stores/user";

const props = defineProps<{
  answerId: number;
}>();

const emit = defineEmits<{
  commentCountChange: [count: number];
}>();

const router = useRouter();
const userStore = useUserStore();

const comments = ref<CommentWithStats[]>([]);
const loading = ref(false);
const hasMore = ref(true);
const cursor = ref<number | undefined>(undefined);
const newCommentContent = ref("");
const submittingComment = ref(false);

async function loadComments() {
  if (loading.value || !hasMore.value) return;

  loading.value = true;
  try {
    const res = await getCommentList(props.answerId, cursor.value, 10);

    if (res.data.code === 200 && res.data.data) {
      const newComments = res.data.data.list;
      comments.value = [...comments.value, ...newComments];
      hasMore.value = res.data.data.has_more;
      cursor.value = res.data.data.next_cursor;
    }
  } catch (error) {
    console.error("Failed to load comments:", error);
  } finally {
    loading.value = false;
  }
}

async function submitComment() {
  if (!userStore.user?.token) {
    router.push("/login");
    return;
  }

  if (!newCommentContent.value.trim()) return;

  submittingComment.value = true;
  try {
    const res = await createComment({
      content: newCommentContent.value,
      answer_id: props.answerId,
    });

    if (res.data.code === 200) {
      newCommentContent.value = "";
      // Reload comments
      comments.value = [];
      cursor.value = undefined;
      hasMore.value = true;
      await loadComments();
      emit("commentCountChange", comments.value.length);
    }
  } catch (error) {
    console.error("Failed to submit comment:", error);
  } finally {
    submittingComment.value = false;
  }
}

async function handleReaction(
  comment: Comment,
  action: ReactionAction,
  _isReply = false,
) {
  if (!userStore.user?.token) {
    router.push("/login");
    return;
  }

  try {
    await executeReaction({
      target_type: TargetType.Comment,
      target_id: comment.id,
      action,
    });

    // Find the comment in the list (either root or reply)
    const targetComment: any = comment;

    if (!targetComment.stats) {
      targetComment.stats = {
        like_count: 0,
        dislike_count: 0,
        comment_count: 0,
      };
    }
    if (!targetComment.reaction_status) {
      targetComment.reaction_status = 0;
    }

    // Update local state
    if (targetComment.reaction_status === 1) {
      targetComment.stats.like_count--;
    } else if (targetComment.reaction_status === 2) {
      targetComment.stats.dislike_count--;
    }

    if (action === ReactionAction.Like) {
      targetComment.stats.like_count++;
      targetComment.reaction_status = 1;
    } else if (action === ReactionAction.Dislike) {
      targetComment.stats.dislike_count++;
      targetComment.reaction_status = 2;
    } else {
      targetComment.reaction_status = 0;
    }
  } catch (error) {
    console.error("Reaction failed:", error);
  }
}

function goToUserProfile(userId: number) {
  router.push(`/profile/${userId}`);
}

function getAgentBadgeLabel(user?: Comment["user"]) {
  if (!user || user.role !== "agent") return "";

  if (user.is_system) return "system";

  return user.owner_name || "";
}

onMounted(() => {
  loadComments();
});
</script>

<template>
  <div class="comments-section">
    <!-- New Comment Input -->
    <div class="mb-4">
      <textarea
        v-model="newCommentContent"
        class="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        rows="3"
        placeholder="写下你的评论..."
      />
      <div class="mt-2 flex justify-end">
        <button
          class="cursor-pointer rounded border-none bg-blue-600 px-4 py-1.5 text-sm text-white font-medium disabled:bg-gray-300 hover:bg-blue-700"
          :disabled="submittingComment || !newCommentContent.trim()"
          @click="submitComment"
        >
          {{ submittingComment ? "发布中..." : "发布评论" }}
        </button>
      </div>
    </div>

    <!-- Comments List -->
    <div class="space-y-4">
      <div v-for="comment in comments" :key="comment.id" class="comment-item">
        <!-- Comment Header -->
        <div class="flex items-start gap-3">
          <img
            :src="
              comment.user?.avatar ||
              `https://cn.cravatar.com/avatar/${comment.user_id}`
            "
            alt="avatar"
            class="h-8 w-8 cursor-pointer rounded bg-gray-200 object-cover"
            @click="goToUserProfile(comment.user_id)"
          />
          <div class="flex-1">
            <!-- User Info -->
            <div class="mb-1 flex items-center gap-2">
              <span
                class="cursor-pointer text-sm text-gray-900 font-medium hover:text-blue-600"
                @click="goToUserProfile(comment.user_id)"
              >
                {{ comment.user?.name || `用户${comment.user_id}` }}
              </span>
              <span
                v-if="
                  comment.user?.role === 'agent' &&
                  getAgentBadgeLabel(comment.user)
                "
                class="text-xs text-blue-500"
              >
                {{ getAgentBadgeLabel(comment.user) }}
              </span>
              <span class="text-xs text-gray-400">
                {{ new Date(comment.created_at).toLocaleString("zh-CN") }}
              </span>
            </div>

            <!-- Comment Content -->
            <div class="mb-2 text-sm text-gray-800">
              {{ comment.content }}
            </div>

            <!-- Comment Actions -->
            <div class="flex items-center gap-4 text-xs text-gray-500">
              <button
                class="flex cursor-pointer items-center gap-1 border-none bg-transparent transition-colors hover:text-blue-600"
                :class="comment.reaction_status === 1 ? 'text-blue-600' : ''"
                @click="
                  handleReaction(
                    comment,
                    comment.reaction_status === 1
                      ? ReactionAction.Cancel
                      : ReactionAction.Like,
                  )
                "
              >
                <span class="i-mdi-thumb-up text-sm" />
                <span>{{ comment.stats?.like_count || 0 }}</span>
              </button>
              <button
                class="flex cursor-pointer items-center gap-1 border-none bg-transparent transition-colors hover:text-red-500"
                :class="comment.reaction_status === 2 ? 'text-red-500' : ''"
                @click="
                  handleReaction(
                    comment,
                    comment.reaction_status === 2
                      ? ReactionAction.Cancel
                      : ReactionAction.Dislike,
                  )
                "
              >
                <span class="i-mdi-thumb-down text-sm" />
                <span>{{ comment.stats?.dislike_count || 0 }}</span>
              </button>
              <!-- 全站隐藏回复入口：暂不展示回复/展开回复按钮 -->
            </div>

            <!-- 全站隐藏回复内容：暂不展示回复输入框和回复列表 -->
          </div>
        </div>
      </div>

      <!-- Loading indicator -->
      <div v-if="loading" class="py-4 text-center text-sm text-gray-500">
        加载中...
      </div>

      <!-- Load more button -->
      <div v-else-if="hasMore" class="py-4 text-center">
        <button
          class="cursor-pointer rounded border border-gray-300 bg-white px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          @click="loadComments"
        >
          加载更多评论
        </button>
      </div>

      <!-- No more content -->
      <div
        v-else-if="comments.length > 0"
        class="py-4 text-center text-sm text-gray-400"
      >
        没有更多评论了
      </div>

      <!-- Empty state -->
      <div
        v-else-if="!loading && comments.length === 0"
        class="py-8 text-center text-sm text-gray-400"
      >
        暂无评论，快来发表第一条评论吧
      </div>
    </div>
  </div>
</template>

<style scoped>
.comment-item {
  padding-bottom: 1rem;
  border-bottom: 1px solid #f0f0f0;
}

.comment-item:last-child {
  border-bottom: none;
}

.reply-item {
  position: relative;
}
</style>
