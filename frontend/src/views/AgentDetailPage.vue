<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useToast } from "vue-toastification";

import { getAgent } from "@/api/agent";
import type { AgentResponse } from "@/api/types";
import AvatarImage from "@/components/AvatarImage.vue";
import { getAgentModelLabel, getStylePresetLabel } from "@/utils/agentMeta";

const route = useRoute();
const router = useRouter();
const toast = useToast();

const agentId = Number(route.params.id);
const agent = ref<AgentResponse | null>(null);
const loading = ref(true);
const showSystemPrompt = ref(false);

const avatarUrl = computed(() => {
  if (!agent.value) return "";
  if (agent.value.avatar) return agent.value.avatar;
  return `https://api.dicebear.com/7.x/notionists/svg?seed=${encodeURIComponent(agent.value.name)}`;
});

const activityLabel = computed(() => {
  const level = agent.value?.raw_config?.activity_level || "medium";
  if (level === "high") return "高活跃";
  if (level === "low") return "低活跃";
  return "中活跃";
});
const styleLabel = computed(() =>
  getStylePresetLabel(agent.value?.raw_config?.style_tag || ""),
);
const modelLabel = computed(() => getAgentModelLabel(agent.value?.model_info));

async function loadAgent() {
  loading.value = true;
  try {
    const res = await getAgent(agentId);
    if (res.data.code === 200 && res.data.data) {
      agent.value = res.data.data;
      return;
    }
    toast.error("Agent 不存在");
  } catch (error: any) {
    console.error("Failed to load agent:", error);
    toast.error(`加载失败: ${error?.message || "未知错误"}`);
  } finally {
    loading.value = false;
  }
}

function goBack() {
  router.back();
}

async function copyApiKey() {
  if (!agent.value?.api_key) return;
  try {
    await navigator.clipboard.writeText(agent.value.api_key);
    toast.success("API Key 已复制");
  } catch {
    toast.error("复制失败，请手动复制");
  }
}

async function copySystemPrompt() {
  if (!agent.value?.system_prompt) return;
  try {
    await navigator.clipboard.writeText(agent.value.system_prompt);
    toast.success("系统提示词已复制");
  } catch {
    toast.error("复制失败，请手动复制");
  }
}

onMounted(() => {
  void loadAgent();
});
</script>

<template>
  <div class="min-h-screen bg-[#f5f7fa] px-4 py-8">
    <div v-if="loading" class="flex items-center justify-center py-20 text-gray-600">加载中...</div>

    <div v-else-if="agent" class="mx-auto max-w-4xl">
      <button
        class="mb-6 inline-flex items-center gap-1 text-gray-600 transition hover:text-gray-900"
        @click="goBack"
      >
        <span class="i-mdi-chevron-left text-lg" />
        返回
      </button>

      <div class="overflow-hidden rounded-2xl bg-white shadow-xl">
        <div class="relative h-52 bg-gradient-to-br from-blue-500 to-indigo-600 p-8">
          <span
            v-if="agent.is_system"
            class="absolute right-6 top-6 rounded-full bg-yellow-300 px-3 py-1 text-xs font-semibold text-yellow-900"
          >
            官方 Agent
          </span>
          <span
            v-else
            class="absolute right-6 top-6 rounded-full bg-green-300 px-3 py-1 text-xs font-semibold text-green-900"
          >
            用户创建
          </span>
          <div class="flex items-end gap-5">
            <AvatarImage
              :src="avatarUrl"
              :alt="agent.name"
              img-class="h-28 w-28 cursor-zoom-in rounded-2xl border-4 border-white bg-white object-cover shadow-xl"
            />
            <div class="pb-1 text-white">
              <h1 class="mb-2 text-3xl font-bold">{{ agent.name }}</h1>
              <p class="text-blue-100">{{ agent.raw_config.headline || "暂无一句话介绍" }}</p>
            </div>
          </div>
        </div>

        <div class="space-y-8 p-8">
          <div class="grid grid-cols-3 gap-6 border-b border-gray-200 pb-8 text-center">
            <div>
              <div class="text-4xl font-bold text-gray-900">{{ agent.stats.questions_count }}</div>
              <div class="mt-2 text-sm text-gray-500">提问数</div>
            </div>
            <div>
              <div class="text-4xl font-bold text-gray-900">{{ agent.stats.answers_count }}</div>
              <div class="mt-2 text-sm text-gray-500">回答数</div>
            </div>
            <div>
              <div class="text-4xl font-bold text-gray-900">{{ agent.stats.followers_count }}</div>
              <div class="mt-2 text-sm text-gray-500">粉丝数</div>
            </div>
          </div>

          <section>
            <h2 class="mb-3 text-lg font-semibold text-gray-900">详细描述</h2>
            <p class="leading-relaxed text-gray-700">{{ agent.raw_config.bio || "暂无" }}</p>
          </section>

          <section v-if="agent.system_prompt">
            <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 class="text-lg font-semibold text-gray-900">系统提示词</h2>
                <p class="mt-1 text-sm text-gray-500">
                  公开展示该 Agent 的系统提示词，方便了解它的行为设定与回答风格。
                </p>
              </div>
              <div class="flex items-center gap-2">
                <button
                  class="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 transition hover:border-gray-300 hover:bg-gray-50 hover:text-gray-900"
                  @click="showSystemPrompt = !showSystemPrompt"
                >
                  {{ showSystemPrompt ? "收起" : "展开查看" }}
                </button>
                <button
                  v-if="showSystemPrompt"
                  class="rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white transition hover:bg-blue-700"
                  @click="copySystemPrompt"
                >
                  复制
                </button>
              </div>
            </div>
            <div
              v-if="showSystemPrompt"
              class="rounded-xl border border-gray-200 bg-gray-50 p-5"
            >
              <pre
                class="font-sans whitespace-pre-wrap break-words text-sm leading-7 text-gray-700"
              >{{ agent.system_prompt }}</pre>
            </div>
          </section>

          <section>
            <h2 class="mb-3 text-lg font-semibold text-gray-900">擅长话题</h2>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="topic in agent.raw_config.topics || []"
                :key="topic"
                class="rounded-lg bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700"
              >
                {{ topic }}
              </span>
            </div>
          </section>

          <section class="grid grid-cols-2 gap-6">
            <div>
              <h3 class="mb-2 font-semibold text-gray-900">人设风格</h3>
              <div class="rounded-lg bg-purple-50 px-4 py-2 text-purple-700">
                {{ styleLabel || "未设置" }}
              </div>
            </div>
            <div>
              <h3 class="mb-2 font-semibold text-gray-900">使用模型</h3>
              <div class="rounded-lg bg-emerald-50 px-4 py-2 text-emerald-700">
                {{ modelLabel || "默认系统模型" }}
              </div>
            </div>
            <div>
              <h3 class="mb-2 font-semibold text-gray-900">回复模式</h3>
              <div class="rounded-lg bg-indigo-50 px-4 py-2 text-indigo-700">
                {{ agent.raw_config.reply_mode || "未设置" }}
              </div>
            </div>
            <div>
              <h3 class="mb-2 font-semibold text-gray-900">活跃度</h3>
              <div class="rounded-lg bg-green-50 px-4 py-2 text-green-700">{{ activityLabel }}</div>
            </div>
            <div>
              <h3 class="mb-2 font-semibold text-gray-900">表达控制</h3>
              <div class="rounded-lg bg-orange-50 px-4 py-2 text-orange-700">
                {{ agent.raw_config.expressiveness || "balanced" }}
              </div>
            </div>
          </section>

          <section
            v-if="agent.api_key"
            class="rounded-xl border border-yellow-200 bg-yellow-50 p-5"
          >
            <div class="mb-2 text-sm font-semibold text-yellow-900">API Key（仅显示一次）</div>
            <div class="flex items-center gap-2">
              <code class="min-w-0 flex-1 overflow-x-auto rounded-lg bg-white px-3 py-2 text-sm text-yellow-800">
                {{ agent.api_key }}
              </code>
              <button
                class="rounded-lg bg-yellow-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-yellow-700"
                @click="copyApiKey"
              >
                复制
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>

    <div v-else class="py-20 text-center text-gray-600">
      <p>Agent 不存在</p>
      <button
        class="mt-4 rounded-lg bg-blue-600 px-5 py-2 text-white transition hover:bg-blue-700"
        @click="goBack"
      >
        返回
      </button>
    </div>
  </div>
</template>
