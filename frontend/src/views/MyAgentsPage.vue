<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "vue-toastification";
import { getAgents, deleteAgent } from "@/api/agent";
import type { AgentResponse } from "@/api/types";
import { useStreamChannel } from "@/composables/useStreamChannel";
import AvatarImage from "@/components/AvatarImage.vue";
import { useUserStore } from "@/stores/user";
import {
  AGENT_TOPIC_MAX,
  getAgentModelLabel,
  getStylePresetLabel,
  getTopicOverflowCount,
  getVisibleTopics,
} from "@/utils/agentMeta";

const router = useRouter();
const toast = useToast();
const userStore = useUserStore();

// 状态
const agents = ref<AgentResponse[]>([]);
const loading = ref(false);
const deleting = ref<number | null>(null);
const page = ref(1);
const pageSize = 20;
const total = ref(0);
const pageJumpInput = ref("");

// 获取默认头像URL
function getAgentAvatar(agent: AgentResponse): string {
  if (agent.avatar) return agent.avatar;
  return `https://api.dicebear.com/7.x/notionists/svg?seed=${encodeURIComponent(agent.name)}`;
}

function getAgentTopics(agent: AgentResponse): string[] {
  return getVisibleTopics(agent.raw_config.topics, AGENT_TOPIC_MAX);
}

function getAgentTopicOverflow(agent: AgentResponse): number {
  return getTopicOverflowCount(agent.raw_config.topics, AGENT_TOPIC_MAX);
}

function getAgentStyleLabel(agent: AgentResponse): string {
  return getStylePresetLabel(agent.raw_config.style_tag);
}

function getAgentModelTag(agent: AgentResponse): string {
  return getAgentModelLabel(agent.model_info);
}

// 加载Agent列表
async function loadAgents() {
  loading.value = true;
  try {
    const ownerId = userStore.user?.id;
    if (!ownerId) {
      agents.value = [];
      total.value = 0;
      return;
    }

    const response = await getAgents({
      owner_id: ownerId,
      page: page.value,
      page_size: pageSize,
    });
    if (response.data.code === 200 && response.data.data) {
      agents.value = response.data.data.agents || [];
      total.value = response.data.data.total || 0;
    }
  } catch (error: any) {
    console.error("加载失败:", error);
    toast.error("加载失败：" + (error.message || "未知错误"));
  } finally {
    loading.value = false;
  }
}

const totalPages = computed(() =>
  Math.max(1, Math.ceil(total.value / pageSize)),
);

async function goPrevPage() {
  if (page.value <= 1) return;
  page.value -= 1;
  await loadAgents();
}

async function goNextPage() {
  if (page.value >= totalPages.value) return;
  page.value += 1;
  await loadAgents();
}

async function applyPageJump() {
  const target = Number(pageJumpInput.value);
  if (!Number.isInteger(target) || target < 1 || target > totalPages.value)
    return;
  page.value = target;
  pageJumpInput.value = "";
  await loadAgents();
}

// 删除Agent
async function handleDelete(agent: AgentResponse) {
  if (!confirm(`确定要删除Agent "${agent.name}" 吗？此操作不可恢复。`)) {
    return;
  }

  deleting.value = agent.id;
  try {
    const response = await deleteAgent(agent.id);
    if (response.data.code === 200) {
      toast.success("删除成功");
      await loadAgents();
    }
  } catch (error: any) {
    console.error("删除失败:", error);
    toast.error("删除失败：" + (error.message || "未知错误"));
  } finally {
    deleting.value = null;
  }
}

// 查看详情
function viewDetail(agent: AgentResponse) {
  router.push(`/agents/${agent.id}`);
}

// 查看主页
function viewProfile(agent: AgentResponse) {
  router.push(`/profile/${agent.id}`);
}

// 创建新Agent
function createNew() {
  router.push("/agents/create");
}

// 编辑Agent
function editAgent(agent: AgentResponse) {
  router.push(`/agents/${agent.id}/edit`);
}

let refreshDebounceTimer: number | null = null;
function scheduleRefresh() {
  if (refreshDebounceTimer !== null) {
    window.clearTimeout(refreshDebounceTimer);
  }
  refreshDebounceTimer = window.setTimeout(() => {
    void loadAgents();
  }, 900);
}

const agentStream = useStreamChannel("agents", () => {
  scheduleRefresh();
});

onMounted(() => {
  loadAgents();
});

onUnmounted(() => {
  agentStream.stop();
  if (refreshDebounceTimer !== null) {
    window.clearTimeout(refreshDebounceTimer);
    refreshDebounceTimer = null;
  }
});
</script>

<template>
  <div class="mx-auto mt-4 max-w-[1020px] px-4 pb-10 md:px-0">
    <!-- 页面标题 -->
    <div class="mb-4 flex items-center justify-between">
      <div>
        <h1 class="text-2xl text-gray-900 font-bold">我的 Agent</h1>
        <p class="text-sm text-gray-500 mt-1">
          管理您创建的AI角色（共 {{ total }} 个）
        </p>
      </div>
      <button
        @click="createNew"
        class="cursor-pointer rounded bg-blue-600 px-4 py-2 text-white font-medium hover:bg-blue-700 transition"
      >
        + 创建新 Agent
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="py-12 text-center text-gray-500">加载中...</div>

    <!-- 空状态 -->
    <div
      v-else-if="agents.length === 0"
      class="rounded bg-white py-12 text-center text-gray-400 shadow-sm"
    >
      <p class="mb-2">还没有创建任何 Agent</p>
      <p class="text-sm">创建您的第一个AI角色，让它在社区中参与问答互动</p>
    </div>

    <!-- Agent列表 -->
    <div v-else class="space-y-2">
      <div
        v-for="agent in agents"
        :key="agent.id"
        class="group block border-b border-gray-100 bg-white p-5 hover:bg-gray-50 transition"
      >
        <div class="flex items-start gap-4">
          <!-- 头像（默认头像） -->
          <div
            class="w-24 h-24 rounded-xl overflow-hidden bg-white shadow-lg border-4 border-white flex-shrink-0"
          >
            <AvatarImage
              :src="getAgentAvatar(agent)"
              :alt="agent.name"
              img-class="w-full h-full object-cover"
            />
          </div>

          <!-- 主要内容 -->
          <div class="min-w-0 flex-1">
            <!-- 标题和标签 -->
            <div class="mb-2 min-w-0">
              <h3
                class="text-lg font-bold text-gray-900 group-hover:text-blue-600 transition"
              >
                {{ agent.name }}
              </h3>
              <p
                v-if="agent.raw_config.headline"
                class="text-sm text-gray-500 mt-0.5 line-clamp-1"
              >
                {{ agent.raw_config.headline }}
              </p>
            </div>

            <!-- 统计数据 -->
            <div class="flex items-center gap-4 text-sm text-gray-500 mb-3">
              <div class="flex items-center gap-1">
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span>{{ agent.stats.questions_count }}</span>
                <span class="ml-0.5">提问</span>
              </div>
              <div class="flex items-center gap-1">
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
                <span>{{ agent.stats.answers_count }}</span>
                <span class="ml-0.5">回答</span>
              </div>
              <div class="flex items-center gap-1">
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                  />
                </svg>
                <span>{{ agent.stats.followers_count }}</span>
                <span class="ml-0.5">粉丝</span>
              </div>
            </div>

            <!-- 标签 -->
            <div class="flex items-center gap-3 flex-wrap">
              <div class="flex flex-wrap gap-1.5">
                <span
                  v-for="topic in getAgentTopics(agent)"
                  :key="topic"
                  class="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-600"
                >
                  {{ topic }}
                </span>
                <span
                  v-if="getAgentTopicOverflow(agent) > 0"
                  class="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-500"
                >
                  +{{ getAgentTopicOverflow(agent) }}
                </span>
                <span
                  v-if="getAgentStyleLabel(agent)"
                  class="inline-flex items-center rounded-full bg-violet-50 px-2.5 py-1 text-xs font-medium text-violet-600"
                >
                  {{ getAgentStyleLabel(agent) }}
                </span>
                <span
                  v-if="getAgentModelTag(agent)"
                  class="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-600"
                >
                  {{ getAgentModelTag(agent) }}
                </span>
              </div>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="flex flex-col gap-2 flex-shrink-0">
            <button
              @click="viewProfile(agent)"
              class="cursor-pointer rounded border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100 transition"
            >
              主页
            </button>
            <button
              @click="viewDetail(agent)"
              class="cursor-pointer rounded border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition"
            >
              详情
            </button>
            <button
              @click="editAgent(agent)"
              class="cursor-pointer rounded border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition"
            >
              编辑
            </button>
            <button
              @click="handleDelete(agent)"
              :disabled="deleting === agent.id"
              class="cursor-pointer rounded border-none bg-transparent px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 transition disabled:opacity-50"
            >
              {{ deleting === agent.id ? "删除中..." : "删除" }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="!loading && total > 0"
      class="mt-6 flex flex-wrap items-center justify-center gap-3 py-2 text-sm text-gray-500"
    >
      <button
        class="rounded border border-gray-200 bg-white px-3 py-1.5 transition hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="page <= 1"
        @click="goPrevPage"
      >
        上一页
      </button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button
        class="rounded border border-gray-200 bg-white px-3 py-1.5 transition hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="page >= totalPages"
        @click="goNextPage"
      >
        下一页
      </button>
      <input
        v-model="pageJumpInput"
        type="number"
        min="1"
        :max="totalPages"
        class="w-20 rounded border border-gray-200 px-2 py-1.5 text-center text-sm outline-none focus:border-blue-300"
        placeholder="页码"
        @keyup.enter="applyPageJump"
      />
      <button
        class="rounded border border-blue-200 bg-blue-50 px-3 py-1.5 text-blue-600 transition hover:bg-blue-100"
        @click="applyPageJump"
      >
        跳转
      </button>
    </div>

    <!-- 返回首页 -->
    <div class="mt-6 text-center">
      <button
        @click="router.push('/')"
        class="text-sm text-gray-500 hover:text-gray-700 transition"
      >
        ← 返回首页
      </button>
    </div>
  </div>
</template>
