<script setup lang="ts">
import type { AnswerWithStats, QuestionWithStats } from "../api/types";
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { ReactionAction, TargetType } from "../api/types";
import { executeReaction } from "../api/reaction";
import AvatarImage from "./AvatarImage.vue";

const props = defineProps<{
  question: QuestionWithStats;
  answer: AnswerWithStats;
}>();

const router = useRouter();

// 3 行截断
const excerpt = computed(() => {
  const text = props.answer.content || "";
  const lines = text.split("\n").slice(0, 3).join("\n");
  return lines.length > 100 ? lines.slice(0, 100) + "..." : lines;
});

const likeCount = ref(props.answer.stats.like_count);
const dislikeCount = ref(props.answer.stats.dislike_count);
const reactionStatus = ref<0 | 1 | 2>(props.answer.reaction_status ?? 0);

async function handleReaction(action: ReactionAction) {
  // 先更新状态（乐观更新）
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
      target_type: TargetType.Answer,
      target_id: props.answer.id,
      action,
    });
  } catch {
    // 失败回滚
    likeCount.value = props.answer.stats.like_count;
    dislikeCount.value = props.answer.stats.dislike_count;
    reactionStatus.value = props.answer.reaction_status ?? 0;
  }
}

function goToQuestion() {
  router.push(`/question/${props.question.id}`);
}
</script>

<template>
  <div
    class="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden"
  >
    <!-- 问题标题（第一层级） -->
    <div class="px-5 pt-4 pb-2">
      <a
        :href="`/question/${question.id}`"
        class="text-lg font-bold text-gray-900 hover:text-blue-600 transition-colors"
        @click.prevent="goToQuestion"
      >
        {{ question.title }}
      </a>
    </div>

    <!-- 回答摘要（第二层级） -->
    <div class="px-5 py-3">
      <!-- 作者栏 -->
      <div class="flex items-center gap-2 mb-3">
        <AvatarImage
          :src="answer.user?.avatar || `https://cn.cravatar.com/avatar/${answer.user_id}`"
          :alt="answer.user?.name || `用户${answer.user_id}`"
          img-class="h-5 w-5 rounded-full bg-gray-200"
        />
        <span class="text-xs text-gray-500">
          {{ answer.user?.name || `用户${answer.user_id}` }}
        </span>
        <span class="text-xs text-gray-400">的回答</span>
      </div>

      <!-- 摘要文本 -->
      <div class="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
        {{ excerpt }}
      </div>

      <!-- 阅读全文 -->
      <router-link
        :to="`/question/${question.id}/answer/${answer.id}`"
        class="inline-block mt-2 text-sm text-blue-600 hover:underline"
      >
        阅读全文 &rarr;
      </router-link>
    </div>

    <!-- 操作栏（第三层级） -->
    <div
      class="flex items-center justify-between px-5 py-3 bg-gray-50 border-t border-gray-100"
    >
      <div class="flex items-center gap-3">
        <!-- 赞同按钮（蓝色药丸） -->
        <button
          class="flex items-center gap-1.5 rounded-full border-none px-4 py-1.5 text-sm font-medium transition-colors"
          :class="
            reactionStatus === 1
              ? 'bg-blue-600 text-white'
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
          <span class="i-mdi-triangle text-xs" />
          <span>赞同</span>
          <span class="font-semibold">{{ likeCount }}</span>
        </button>

        <!-- 评论入口已关闭 -->
      </div>

      <!-- 查看原问题 -->
      <router-link
        :to="`/question/${question.id}`"
        class="text-sm text-blue-600 hover:underline"
      >
        查看原问题 &rarr;
      </router-link>
    </div>
  </div>
</template>
