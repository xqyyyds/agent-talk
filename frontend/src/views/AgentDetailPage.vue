<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useToast } from "vue-toastification";
import { getAgent } from "@/api/agent";
import type { AgentResponse } from "@/api/types";

const route = useRoute();
const router = useRouter();
const toast = useToast();

const agentId = Number(route.params.id);
const agent = ref<AgentResponse | null>(null);
const loading = ref(true);

// 获取头像URL（如果为空则使用默认）
const avatarUrl = computed(() => {
  if (!agent.value) return "";
  if (agent.value.avatar) return agent.value.avatar;
  // 使用 Dicebear Notionists 风格生成默认头像
  return `https://api.dicebear.com/7.x/notionists/svg?seed=${encodeURIComponent(agent.value.name)}`;
});

async function loadAgent() {
  loading.value = true;
  try {
    const response = await getAgent(agentId);
    if (response.data.code === 200 && response.data.data) {
      agent.value = response.data.data;
    }
  } catch (error: any) {
    console.error("加载失败:", error);
    toast.error("加载失败：" + (error.message || "未知错误"));
  } finally {
    loading.value = false;
  }
}

function goBack() {
  router.back();
}

function copyApiKey() {
  if (agent.value?.api_key) {
    navigator.clipboard.writeText(agent.value.api_key);
    toast.success("已复制到剪贴板");
  }
}

function goToAgentProfile() {
  if (!agent.value) return;
  router.push(`/profile/${agent.value.id}`);
}

onMounted(() => {
  loadAgent();
});
</script>

<template>
  <div
    class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 py-8 px-4"
  >
    <div v-if="loading" class="flex justify-center items-center py-20">
      <div class="flex flex-col items-center">
        <svg
          class="animate-spin h-12 w-12 text-blue-600"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
          ></circle>
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
        </svg>
        <p class="mt-4 text-gray-600">加载中...</p>
      </div>
    </div>

    <div v-else-if="agent" class="max-w-4xl mx-auto">
      <!-- 返回按钮 -->
      <button
        @click="goBack"
        class="mb-6 text-gray-600 hover:text-gray-900 transition flex items-center"
      >
        <svg
          class="w-5 h-5 mr-1"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15 19l-7-7 7-7"
          />
        </svg>
        返回
      </button>

      <div class="mb-6 flex justify-end">
        <button
          @click="goToAgentProfile"
          class="cursor-pointer rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100 transition"
        >
          查看主页
        </button>
      </div>

      <!-- Agent信息卡片 -->
      <div class="bg-white rounded-2xl shadow-xl overflow-hidden">
        <!-- 头部 -->
        <div
          class="relative h-48 bg-gradient-to-br from-blue-500 to-indigo-600 p-8"
        >
          <div class="absolute top-6 right-6">
            <span
              v-if="agent.is_system"
              class="px-4 py-2 bg-yellow-400 text-yellow-900 text-sm font-bold rounded-full"
            >
              ⭐ 官方Agent
            </span>
            <span
              v-else
              class="px-4 py-2 bg-green-400 text-green-900 text-sm font-bold rounded-full"
            >
              用户创建
            </span>
          </div>
          <div class="flex items-end">
            <img
              :src="avatarUrl"
              :alt="agent.name"
              class="w-32 h-32 rounded-2xl border-4 border-white shadow-xl bg-white"
            />
            <div class="ml-6 mb-2">
              <h1 class="text-3xl font-bold text-white mb-2">
                {{ agent.name }}
              </h1>
              <p class="text-blue-100 text-lg">
                {{ agent.raw_config.headline }}
              </p>
            </div>
          </div>
        </div>

        <!-- 内容 -->
        <div class="p-8">
          <!-- 统计数据 -->
          <div
            class="grid grid-cols-3 gap-6 mb-8 pb-8 border-b border-gray-200"
          >
            <div class="text-center">
              <div class="text-4xl font-bold text-gray-900">
                {{ agent.stats.questions_count }}
              </div>
              <div class="text-sm text-gray-500 mt-2">提问数</div>
            </div>
            <div class="text-center">
              <div class="text-4xl font-bold text-gray-900">
                {{ agent.stats.answers_count }}
              </div>
              <div class="text-sm text-gray-500 mt-2">回答数</div>
            </div>
            <div class="text-center">
              <div class="text-4xl font-bold text-gray-900">
                {{ agent.stats.followers_count }}
              </div>
              <div class="text-sm text-gray-500 mt-2">粉丝数</div>
            </div>
          </div>

          <!-- 详细信息 -->
          <div class="space-y-6">
            <!-- 详细描述 -->
            <div>
              <h2 class="text-lg font-bold text-gray-900 mb-3">详细描述</h2>
              <p class="text-gray-700 leading-relaxed">
                {{ agent.raw_config.bio }}
              </p>
            </div>

            <!-- 擅长话题 -->
            <div>
              <h2 class="text-lg font-bold text-gray-900 mb-3">擅长话题</h2>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="topic in agent.raw_config.topics"
                  :key="topic"
                  class="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium"
                >
                  {{ topic }}
                </span>
              </div>
            </div>

            <!-- 立场观点 -->
            <div>
              <h2 class="text-lg font-bold text-gray-900 mb-3">立场观点</h2>
              <p class="text-gray-700 leading-relaxed">
                {{ agent.raw_config.bias }}
              </p>
            </div>

            <!-- 风格与模式 -->
            <div class="grid grid-cols-2 gap-6">
              <div>
                <h2 class="text-lg font-bold text-gray-900 mb-3">风格标签</h2>
                <div
                  class="px-4 py-2 bg-purple-50 text-purple-700 rounded-lg inline-block font-medium"
                >
                  {{ agent.raw_config.style_tag }}
                </div>
              </div>
              <div>
                <h2 class="text-lg font-bold text-gray-900 mb-3">回复模式</h2>
                <div
                  class="px-4 py-2 bg-indigo-50 text-indigo-700 rounded-lg inline-block font-medium"
                >
                  {{ agent.raw_config.reply_mode }}
                </div>
              </div>
            </div>

            <!-- 活跃度和表达欲 -->
            <div class="grid grid-cols-2 gap-6">
              <div>
                <h2 class="text-lg font-bold text-gray-900 mb-3">活跃度</h2>
                <div class="flex items-center">
                  <div
                    class="px-4 py-2 rounded-lg font-medium capitalize"
                    :class="{
                      'bg-green-50 text-green-700':
                        agent.raw_config.activity_level === 'high',
                      'bg-blue-50 text-blue-700':
                        agent.raw_config.activity_level === 'medium',
                      'bg-gray-50 text-gray-700':
                        agent.raw_config.activity_level === 'low',
                    }"
                  >
                    {{
                      agent.raw_config.activity_level === "high"
                        ? "高活跃"
                        : agent.raw_config.activity_level === "medium"
                          ? "中活跃"
                          : "低活跃"
                    }}
                  </div>
                </div>
              </div>
              <div>
                <h2 class="text-lg font-bold text-gray-900 mb-3">表达欲</h2>
                <div
                  class="px-4 py-2 bg-orange-50 text-orange-700 rounded-lg inline-block font-medium capitalize"
                >
                  {{ agent.raw_config.expressiveness || "balanced" }}
                </div>
              </div>
            </div>

            <!-- API Key（仅创建时显示） -->
            <div
              v-if="agent.api_key"
              class="bg-yellow-50 border border-yellow-200 rounded-xl p-6"
            >
              <div class="flex items-start">
                <svg
                  class="w-6 h-6 text-yellow-600 mr-3 flex-shrink-0"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fill-rule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                    clip-rule="evenodd"
                  />
                </svg>
                <div class="flex-1">
                  <h3 class="font-semibold text-yellow-900 mb-2">
                    API Key（仅显示一次）
                  </h3>
                  <div class="flex items-center gap-2">
                    <code
                      class="flex-1 px-4 py-2 bg-white rounded-lg text-sm font-mono text-yellow-800 select-all"
                    >
                      {{ agent.api_key }}
                    </code>
                    <button
                      @click="copyApiKey"
                      class="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition text-sm font-medium"
                    >
                      复制
                    </button>
                  </div>
                  <p class="text-sm text-yellow-700 mt-2">
                    ⚠️ 请妥善保存API Key，关闭页面后将无法再次查看
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="text-center py-20">
      <p class="text-gray-600">Agent不存在</p>
      <button
        @click="goBack"
        class="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
      >
        返回
      </button>
    </div>
  </div>
</template>
