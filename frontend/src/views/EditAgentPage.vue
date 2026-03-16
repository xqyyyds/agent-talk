<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useToast } from "vue-toastification";
import { getAgent, updateAgent } from "@/api/agent";
import { optimizeAgentPrompt, playgroundChat } from "@/api/agent_python";
import type { AgentResponse, OptimizeAgentRequest } from "@/api/types";

const route = useRoute();
const router = useRouter();
const toast = useToast();

const agentId = Number(route.params.id);
const agent = ref<AgentResponse | null>(null);
const loading = ref(true);

// 表单数据
const formData = ref<{
  name: string;
  headline: string;
  bio: string;
  topics: string[];
  bias: string;
  style_tag: string;
  reply_mode: string;
  activity_level: "high" | "medium" | "low";
  expressiveness: "terse" | "balanced" | "verbose" | "dynamic";
  system_prompt: string;
  avatar?: string;
}>({
  name: "",
  headline: "",
  bio: "",
  topics: [],
  bias: "",
  style_tag: "",
  reply_mode: "balanced",
  activity_level: "medium",
  expressiveness: "balanced",
  system_prompt: "",
  avatar: undefined,
});

// 优化后的系统提示词
const optimizedPrompt = ref("");
const isOptimizing = ref(false);
const isFallback = ref(false);

// 测试对话
const testQuestion = ref("");
const testReply = ref("");
const isTesting = ref(false);

// 当前步骤: form | optimize | test
const currentStep = ref<"form" | "optimize" | "test">("form");

// 正在保存
const isSaving = ref(false);

// 表单验证错误
const errors = ref<Record<string, string>>({});

// 预设选项
const expressivenessOptions = [
  { value: "terse", label: "惜字如金", desc: "简短有力，50字以内" },
  { value: "balanced", label: "标准表达", desc: "100-200字，逻辑清晰" },
  { value: "verbose", label: "深度详尽", desc: "300字以上，充分展开" },
  {
    value: "dynamic",
    label: "🌟 动态表达",
    desc: "基于兴趣智能调整，最像真人",
  },
];

const activityLevelOptions = [
  { value: "low", label: "低活跃", desc: "偶尔参与问答" },
  { value: "medium", label: "中活跃", desc: "定期参与问答" },
  { value: "high", label: "高活跃", desc: "频繁参与问答" },
];

const replyModeOptions = [
  "理性客观",
  "幽默风趣",
  "温暖共情",
  "犀利批判",
  "严谨求实",
  "脑洞类比",
  "简洁直接",
];

// 擅长话题选项（预设）
const topicOptions = [
  { value: "日常生活", label: "日常生活", icon: "🏠" },
  { value: "情感关系", label: "情感关系", icon: "💕" },
  { value: "职场吐槽", label: "职场吐槽", icon: "💼" },
  { value: "社会热点", label: "社会热点", icon: "📰" },
  { value: "科技数码", label: "科技数码", icon: "💻" },
  { value: "互联网文化", label: "互联网文化", icon: "🌐" },
  { value: "心理咨询", label: "心理咨询", icon: "🧠" },
  { value: "人生建议", label: "人生建议", icon: "💡" },
  { value: "成长困惑", label: "成长困惑", icon: "🌱" },
  { value: "职场生存", label: "职场生存", icon: "🏢" },
  { value: "人际关系", label: "人际关系", icon: "🤝" },
  { value: "行业洞察", label: "行业洞察", icon: "🔍" },
  { value: "影视娱乐", label: "影视娱乐", icon: "🎬" },
  { value: "文学艺术", label: "文学艺术", icon: "🎨" },
  { value: "运动健康", label: "运动健康", icon: "🏃" },
  { value: "财经投资", label: "财经投资", icon: "💰" },
  { value: "教育学习", label: "教育学习", icon: "📚" },
  { value: "旅行探索", label: "旅行探索", icon: "✈️" },
  { value: "美食烹饪", label: "美食烹饪", icon: "🍳" },
  { value: "游戏电竞", label: "游戏电竞", icon: "🎮" },
];

// 立场观点选项
const biasOptions = [
  {
    value: "理性客观，基于事实和数据进行分析",
    label: "理性客观",
    desc: "基于事实和数据进行分析",
    icon: "⚖️",
  },
  {
    value: "感性共情，关注人的感受和情绪",
    label: "感性共情",
    desc: "关注人的感受和情绪",
    icon: "💗",
  },
  {
    value: "批判思维，质疑主流观点，独立思考",
    label: "批判思维",
    desc: "质疑主流观点，独立思考",
    icon: "🔍",
  },
  {
    value: "实用主义，注重解决实际问题",
    label: "实用主义",
    desc: "注重解决实际问题",
    icon: "🔧",
  },
  {
    value: "乐观积极，寻找机会和希望",
    label: "乐观积极",
    desc: "寻找机会和希望",
    icon: "☀️",
  },
  {
    value: "谨慎保守，强调风险和底线",
    label: "谨慎保守",
    desc: "强调风险和底线",
    icon: "🛡️",
  },
  {
    value: "人文关怀，重视个体体验和尊严",
    label: "人文关怀",
    desc: "重视个体体验和尊严",
    icon: "🤲",
  },
  {
    value: "幽默讽刺，用轻松的方式解构问题",
    label: "幽默讽刺",
    desc: "用轻松的方式解构问题",
    icon: "😄",
  },
];

// 风格标签选项
const styleTagOptions = [
  {
    value: "幽默吐槽",
    label: "幽默吐槽",
    desc: "机智风趣，爱开玩笑",
    icon: "😂",
  },
  {
    value: "温暖治愈",
    label: "温暖治愈",
    desc: "温柔体贴，给人安慰",
    icon: "🌸",
  },
  {
    value: "严谨专业",
    label: "严谨专业",
    desc: "专业可靠，逻辑清晰",
    icon: "📊",
  },
  {
    value: "脑洞类比",
    label: "脑洞类比",
    desc: "想象力丰富，善用比喻",
    icon: "💭",
  },
  {
    value: "犀利毒舌",
    label: "犀利毒舌",
    desc: "直击要害，不留情面",
    icon: "⚡",
  },
  {
    value: "简洁务实",
    label: "简洁务实",
    desc: "直截了当，不绕弯子",
    icon: "🎯",
  },
  {
    value: "文艺清新",
    label: "文艺清新",
    desc: "文笔优美，意境深远",
    icon: "📝",
  },
  {
    value: "热血激情",
    label: "热血激情",
    desc: "充满活力，感染力强",
    icon: "🔥",
  },
];

// 切换话题选择
function toggleTopic(topic: string) {
  const index = formData.value.topics.indexOf(topic);
  if (index > -1) {
    formData.value.topics.splice(index, 1);
  } else {
    formData.value.topics.push(topic);
  }
}

// 移除话题
function removeTopic(topic: string) {
  const index = formData.value.topics.indexOf(topic);
  if (index > -1) {
    formData.value.topics.splice(index, 1);
  }
}

// 验证表单
function validateForm(): boolean {
  errors.value = {};

  if (!formData.value.name.trim()) {
    errors.value.name = "请输入Agent名称";
  } else if (
    formData.value.name.length < 2 ||
    formData.value.name.length > 50
  ) {
    errors.value.name = "名称长度应在2-50字之间";
  }

  if (!formData.value.headline.trim()) {
    errors.value.headline = "请输入一句话介绍";
  } else if (formData.value.headline.length > 100) {
    errors.value.headline = "介绍不能超过100字";
  }

  if (!formData.value.bio.trim()) {
    errors.value.bio = "请输入详细描述";
  } else if (formData.value.bio.length > 1000) {
    errors.value.bio = "描述不能超过1000字";
  }

  if (formData.value.topics.length === 0) {
    errors.value.topics = "请至少添加一个擅长话题";
  }

  if (!formData.value.bias.trim()) {
    errors.value.bias = "请选择立场观点";
  }

  return Object.keys(errors.value).length === 0;
}

// 加载Agent数据
async function loadAgent() {
  loading.value = true;
  try {
    const response = await getAgent(agentId);
    if (response.data.code === 200 && response.data.data) {
      agent.value = response.data.data;
      const raw = agent.value.raw_config;

      // 填充表单数据
      formData.value = {
        name: agent.value.name,
        headline: raw.headline,
        bio: raw.bio,
        topics: raw.topics || [],
        bias: raw.bias,
        style_tag: raw.style_tag,
        reply_mode: raw.reply_mode,
        activity_level: raw.activity_level,
        expressiveness: raw.expressiveness || "balanced",
        system_prompt: "", // 编辑时先清空，需要重新生成
        avatar: agent.value.avatar || undefined,
      };
    }
  } catch (error: any) {
    console.error("加载失败:", error);
    toast.error("加载失败：" + (error.message || "未知错误"));
    router.push("/agents/my");
  } finally {
    loading.value = false;
  }
}

// 优化系统提示词
async function handleOptimize() {
  if (!validateForm()) {
    toast.error("请检查表单填写是否正确");
    return;
  }

  isOptimizing.value = true;
  errors.value = {};

  try {
    const request: OptimizeAgentRequest = {
      name: formData.value.name,
      headline: formData.value.headline,
      bio: formData.value.bio,
      topics: formData.value.topics.join(", "),
      bias: formData.value.bias,
      style_tag: formData.value.style_tag,
      reply_mode: formData.value.reply_mode,
      expressiveness: formData.value.expressiveness || "balanced",
    };

    const response = await optimizeAgentPrompt(request);

    if (response.code === 200) {
      optimizedPrompt.value = response.data.system_prompt;
      isFallback.value = response.data.is_fallback;
      formData.value.system_prompt = optimizedPrompt.value;
      currentStep.value = "optimize";

      if (isFallback.value) {
        toast.warning("使用基础模板生成（AI优化服务不可用）");
      } else {
        toast.success("系统提示词优化完成！");
      }
    } else {
      throw new Error("优化失败");
    }
  } catch (error: any) {
    console.error("优化失败:", error);
    toast.error("优化失败：" + (error.message || "未知错误"));
    errors.value.optimize = error.message;
  } finally {
    isOptimizing.value = false;
  }
}

// 重新生成
function handleRegenerate() {
  handleOptimize();
}

// 测试对话
async function handleTest() {
  if (!testQuestion.value.trim()) {
    toast.error("请输入测试问题");
    return;
  }

  isTesting.value = true;
  testReply.value = "";

  try {
    const response = await playgroundChat({
      system_prompt: formData.value.system_prompt || optimizedPrompt.value,
      question: testQuestion.value,
    });

    if (response.code === 200) {
      testReply.value = response.data.reply;
      toast.success("测试回答生成成功！");
    } else {
      throw new Error("测试失败");
    }
  } catch (error: any) {
    console.error("测试失败:", error);
    toast.error("测试失败：" + (error.message || "未知错误"));
  } finally {
    isTesting.value = false;
  }
}

// 返回编辑
function handleBackToForm() {
  currentStep.value = "form";
}

// 返回优化
function handleBackToOptimize() {
  currentStep.value = "optimize";
  testReply.value = "";
}

// 保存修改
async function handleSave() {
  isSaving.value = true;

  try {
    const response = await updateAgent(agentId, {
      name: formData.value.name,
      headline: formData.value.headline,
      bio: formData.value.bio,
      topics: formData.value.topics,
      bias: formData.value.bias,
      style_tag: formData.value.style_tag,
      reply_mode: formData.value.reply_mode,
      activity_level: formData.value.activity_level,
      expressiveness: formData.value.expressiveness,
      system_prompt: formData.value.system_prompt,
      avatar: formData.value.avatar,
    });

    if (response.data.code === 200) {
      toast.success("Agent更新成功！");
      router.push("/agents/my");
    } else {
      throw new Error(response.data.message || "更新失败");
    }
  } catch (error: any) {
    console.error("更新失败:", error);
    toast.error("更新失败：" + (error.message || "未知错误"));
  } finally {
    isSaving.value = false;
  }
}

// 取消编辑
function handleCancel() {
  router.back();
}

function goToAgentProfile() {
  if (!agent.value) return;
  router.push(`/profile/${agent.value.id}`);
}

onMounted(() => {
  loadAgent();
  window.scrollTo({ top: 0, behavior: "smooth" });
});
</script>

<template>
  <div
    class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 py-8 px-4"
  >
    <!-- 加载中 -->
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

    <div v-else class="max-w-4xl mx-auto">
      <!-- 顶部标题 -->
      <div class="mb-8">
        <div class="flex items-center gap-4">
          <button
            @click="handleCancel"
            class="text-gray-600 hover:text-gray-900 transition"
          >
            <svg
              class="w-6 h-6"
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
          </button>
          <div>
            <h1 class="text-2xl font-bold text-gray-900">编辑 Agent</h1>
            <p class="text-gray-600">修改您的 AI Agent 配置</p>
          </div>
          <button
            v-if="agent"
            @click="goToAgentProfile"
            class="ml-auto cursor-pointer rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100 transition"
          >
            查看主页
          </button>
        </div>

        <!-- 进度指示 -->
        <div class="mt-8 flex items-center justify-center space-x-4">
          <div
            class="flex items-center"
            :class="currentStep === 'form' ? 'text-blue-600' : 'text-gray-400'"
          >
            <div
              class="w-8 h-8 rounded-full flex items-center justify-center border-2 font-semibold"
              :class="
                currentStep === 'form'
                  ? 'border-blue-600 bg-blue-50'
                  : 'border-gray-300 bg-gray-50'
              "
            >
              1
            </div>
            <span class="ml-2 font-medium">修改配置</span>
          </div>
          <div class="w-16 h-0.5 bg-gray-300"></div>
          <div
            class="flex items-center"
            :class="
              currentStep === 'optimize' || currentStep === 'test'
                ? 'text-blue-600'
                : 'text-gray-400'
            "
          >
            <div
              class="w-8 h-8 rounded-full flex items-center justify-center border-2 font-semibold"
              :class="
                currentStep === 'optimize' || currentStep === 'test'
                  ? 'border-blue-600 bg-blue-50'
                  : 'border-gray-300 bg-gray-50'
              "
            >
              2
            </div>
            <span class="ml-2 font-medium">生成提示词</span>
          </div>
          <div class="w-16 h-0.5 bg-gray-300"></div>
          <div
            class="flex items-center"
            :class="currentStep === 'test' ? 'text-blue-600' : 'text-gray-400'"
          >
            <div
              class="w-8 h-8 rounded-full flex items-center justify-center border-2 font-semibold"
              :class="
                currentStep === 'test'
                  ? 'border-blue-600 bg-blue-50'
                  : 'border-gray-300 bg-gray-50'
              "
            >
              3
            </div>
            <span class="ml-2 font-medium">测试保存</span>
          </div>
        </div>
      </div>

      <!-- 步骤1: 表单 -->
      <div
        v-if="currentStep === 'form'"
        class="bg-white rounded-2xl shadow-xl p-8"
      >
        <h2 class="text-2xl font-bold text-gray-900 mb-6">基本信息</h2>

        <!-- Agent名称 -->
        <div class="mb-6">
          <label class="block text-sm font-semibold text-gray-700 mb-2">
            Agent 名称 <span class="text-red-500">*</span>
          </label>
          <input
            v-model="formData.name"
            type="text"
            placeholder="例如：毒舌影评人、温柔心理医生"
            class="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
            :class="errors.name ? 'border-red-500' : 'border-gray-300'"
          />
          <p v-if="errors.name" class="mt-1 text-sm text-red-500">
            {{ errors.name }}
          </p>
          <p v-else class="mt-1 text-sm text-gray-500">
            2-50字，简洁好记的名字
          </p>
        </div>

        <!-- 头像预览（默认头像） -->
        <div class="mb-8">
          <label class="block text-sm font-semibold text-gray-700 mb-2">
            Agent 头像
          </label>
          <div class="flex items-center gap-6">
            <div
              class="w-32 h-32 rounded-xl overflow-hidden bg-white shadow-lg border-4 border-white"
            >
              <img
                :src="`https://api.dicebear.com/7.x/notionists/svg?seed=${encodeURIComponent(formData.name || 'default')}`"
                :alt="formData.name || 'Avatar'"
                class="w-full h-full object-cover"
              />
            </div>
            <div class="text-sm text-gray-600">
              <p class="font-medium mb-1">默认头像</p>
              <p class="text-gray-500">系统根据 Agent 名称自动生成唯一头像</p>
            </div>
          </div>
        </div>

        <!-- 一句话介绍 -->
        <div class="mb-6">
          <label class="block text-sm font-semibold text-gray-700 mb-2">
            一句话介绍 <span class="text-red-500">*</span>
          </label>
          <input
            v-model="formData.headline"
            type="text"
            placeholder="例如：专业毒舌，但影评犀利"
            class="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
            :class="errors.headline ? 'border-red-500' : 'border-gray-300'"
          />
          <p v-if="errors.headline" class="mt-1 text-sm text-red-500">
            {{ errors.headline }}
          </p>
          <p v-else class="mt-1 text-sm text-gray-500">
            简短描述Agent的核心特点（最大100字）
          </p>
        </div>

        <!-- 详细描述 -->
        <div class="mb-6">
          <label class="block text-sm font-semibold text-gray-700 mb-2">
            详细描述 <span class="text-red-500">*</span>
          </label>
          <textarea
            v-model="formData.bio"
            rows="4"
            placeholder="详细描述Agent的性格、背景、说话风格等..."
            class="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition resize-none"
            :class="errors.bio ? 'border-red-500' : 'border-gray-300'"
          ></textarea>
          <p v-if="errors.bio" class="mt-1 text-sm text-red-500">
            {{ errors.bio }}
          </p>
          <p v-else class="mt-1 text-sm text-gray-500">
            越详细越好，AI会基于此生成更准确的系统提示词（最大1000字）
          </p>
        </div>

        <!-- 擅长话题 -->
        <div class="mb-6">
          <label class="block text-sm font-semibold text-gray-700 mb-2">
            擅长话题 <span class="text-red-500">*</span>
          </label>
          <p v-if="errors.topics" class="mb-2 text-sm text-red-500">
            {{ errors.topics }}
          </p>
          <!-- 预设话题选择 -->
          <div
            class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 mb-3"
          >
            <button
              v-for="option in topicOptions"
              :key="option.value"
              @click="toggleTopic(option.value)"
              class="px-3 py-2 rounded-lg text-sm transition border-2 flex items-center justify-center gap-1"
              :class="
                formData.topics.includes(option.value)
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-200 hover:border-gray-300 text-gray-700'
              "
            >
              <span>{{ option.icon }}</span>
              <span>{{ option.label }}</span>
            </button>
          </div>
          <!-- 已选话题标签 -->
          <div
            v-if="formData.topics.length > 0"
            class="flex flex-wrap gap-2 mb-2"
          >
            <span
              v-for="topic in formData.topics"
              :key="topic"
              class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800"
            >
              {{ topic }}
              <button
                @click="removeTopic(topic)"
                class="ml-2 text-blue-600 hover:text-blue-800"
              >
                ×
              </button>
            </span>
          </div>
          <p class="mt-1 text-sm text-gray-500">
            至少选择一个擅长话题（可多选）
          </p>
        </div>

        <!-- 立场观点 -->
        <div class="mb-6">
          <label class="block text-sm font-semibold text-gray-700 mb-2">
            立场观点 <span class="text-red-500">*</span>
          </label>
          <p v-if="errors.bias" class="mb-2 text-sm text-red-500">
            {{ errors.bias }}
          </p>
          <div class="grid grid-cols-2 gap-3">
            <button
              v-for="option in biasOptions"
              :key="option.value"
              @click="formData.bias = option.value"
              class="p-3 border-2 rounded-xl transition text-left"
              :class="
                formData.bias === option.value
                  ? 'border-blue-600 bg-blue-50 text-blue-700'
                  : 'border-gray-300 hover:border-gray-400'
              "
            >
              <div class="flex items-center gap-2">
                <span class="text-xl">{{ option.icon }}</span>
                <div>
                  <div class="font-semibold">{{ option.label }}</div>
                  <div class="text-xs opacity-75">{{ option.desc }}</div>
                </div>
              </div>
            </button>
          </div>
          <p class="mt-2 text-sm text-gray-500">选择Agent的核心思维倾向</p>
        </div>

        <!-- 风格标签 -->
        <div class="mb-6">
          <label class="block text-sm font-semibold text-gray-700 mb-2">
            风格标签
          </label>
          <div class="grid grid-cols-2 gap-3">
            <button
              v-for="option in styleTagOptions"
              :key="option.value"
              @click="formData.style_tag = option.value"
              class="p-3 border-2 rounded-xl transition text-left"
              :class="
                formData.style_tag === option.value
                  ? 'border-blue-600 bg-blue-50 text-blue-700'
                  : 'border-gray-300 hover:border-gray-400'
              "
            >
              <div class="flex items-center gap-2">
                <span class="text-xl">{{ option.icon }}</span>
                <div>
                  <div class="font-semibold">{{ option.label }}</div>
                  <div class="text-xs opacity-75">{{ option.desc }}</div>
                </div>
              </div>
            </button>
          </div>
          <p class="mt-2 text-sm text-gray-500">选择Agent的说话风格（可选）</p>
        </div>

        <!-- 回复模式 -->
        <div class="mb-6">
          <label class="block text-sm font-semibold text-gray-700 mb-2">
            回复模式
          </label>
          <select
            v-model="formData.reply_mode"
            class="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
          >
            <option v-for="mode in replyModeOptions" :key="mode" :value="mode">
              {{ mode }}
            </option>
          </select>
          <p class="mt-1 text-sm text-gray-500">选择Agent的主要回复风格</p>
        </div>

        <!-- 活跃度 -->
        <div class="mb-6">
          <label class="block text-sm font-semibold text-gray-700 mb-2">
            活跃度
          </label>
          <div class="grid grid-cols-3 gap-4">
            <button
              v-for="option in activityLevelOptions"
              :key="option.value"
              @click="
                formData.activity_level = option.value as
                  | 'high'
                  | 'medium'
                  | 'low'
              "
              class="p-4 border-2 rounded-xl transition text-center"
              :class="
                formData.activity_level === option.value
                  ? 'border-blue-600 bg-blue-50 text-blue-700'
                  : 'border-gray-300 hover:border-gray-400'
              "
            >
              <div class="font-semibold">{{ option.label }}</div>
              <div class="text-sm mt-1 opacity-75">{{ option.desc }}</div>
            </button>
          </div>
        </div>

        <!-- 表达欲 -->
        <div class="mb-8">
          <label class="block text-sm font-semibold text-gray-700 mb-2">
            表达欲
          </label>
          <div class="grid grid-cols-2 gap-4">
            <button
              v-for="option in expressivenessOptions"
              :key="option.value"
              @click="
                formData.expressiveness = option.value as
                  | 'terse'
                  | 'balanced'
                  | 'verbose'
                  | 'dynamic'
              "
              class="p-4 border-2 rounded-xl transition"
              :class="
                formData.expressiveness === option.value
                  ? 'border-blue-600 bg-blue-50 text-blue-700'
                  : 'border-gray-300 hover:border-gray-400'
              "
            >
              <div class="font-semibold">{{ option.label }}</div>
              <div class="text-sm mt-1 opacity-75">{{ option.desc }}</div>
            </button>
          </div>
          <p class="mt-2 text-sm text-gray-500">控制Agent回复的篇幅和频率</p>
        </div>

        <!-- 提交按钮 -->
        <div class="flex justify-end">
          <button
            @click="handleOptimize"
            :disabled="isOptimizing"
            class="px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:from-blue-700 hover:to-indigo-700 transition font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            <svg
              v-if="isOptimizing"
              class="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
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
            {{ isOptimizing ? "AI优化中..." : "生成系统提示词" }}
          </button>
        </div>
      </div>

      <!-- 步骤2: 优化结果 -->
      <div
        v-else-if="currentStep === 'optimize'"
        class="bg-white rounded-2xl shadow-xl p-8"
      >
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-2xl font-bold text-gray-900">系统提示词</h2>
          <div class="flex gap-2">
            <button
              @click="handleRegenerate"
              :disabled="isOptimizing"
              class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition text-sm flex items-center"
            >
              <svg
                v-if="isOptimizing"
                class="animate-spin -ml-1 mr-2 h-4 w-4"
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
              重新生成
            </button>
            <button
              @click="handleBackToForm"
              class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition text-sm"
            >
              返回修改
            </button>
          </div>
        </div>

        <!-- 提示词展示 -->
        <div class="mb-6">
          <div
            class="bg-gradient-to-br from-gray-50 to-blue-50 rounded-xl p-6 border border-gray-200"
          >
            <textarea
              v-model="formData.system_prompt"
              rows="15"
              class="w-full bg-transparent border-0 focus:ring-0 resize-none text-gray-800 font-mono text-sm leading-relaxed"
              placeholder="系统提示词将显示在这里..."
            ></textarea>
          </div>
          <p class="mt-2 text-sm text-gray-500">
            💡 提示：您可以手动编辑上面的系统提示词，直到满意为止
          </p>
        </div>

        <!-- 警告信息 -->
        <div
          v-if="isFallback"
          class="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-xl"
        >
          <div class="flex">
            <svg
              class="w-5 h-5 text-yellow-400 mr-2"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fill-rule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clip-rule="evenodd"
              />
            </svg>
            <div class="text-sm text-yellow-800">
              使用了基础模板生成。AI优化服务暂时不可用，但您的Agent仍然可以正常使用。
            </div>
          </div>
        </div>

        <!-- 下一步按钮 -->
        <div class="flex justify-end">
          <button
            @click="currentStep = 'test'"
            class="px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:from-blue-700 hover:to-indigo-700 transition font-semibold"
          >
            测试对话 →
          </button>
        </div>
      </div>

      <!-- 步骤3: 测试对话 -->
      <div
        v-else-if="currentStep === 'test'"
        class="bg-white rounded-2xl shadow-xl p-8"
      >
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-2xl font-bold text-gray-900">测试对话</h2>
          <button
            @click="handleBackToOptimize"
            class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition text-sm"
          >
            返回修改
          </button>
        </div>

        <!-- 测试问题输入 -->
        <div class="mb-6">
          <label class="block text-sm font-semibold text-gray-700 mb-2">
            测试问题
          </label>
          <textarea
            v-model="testQuestion"
            rows="3"
            placeholder="输入一个问题，看看Agent如何回答..."
            class="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition resize-none"
          ></textarea>
        </div>

        <!-- 测试按钮 -->
        <div class="mb-6 flex justify-end">
          <button
            @click="handleTest"
            :disabled="isTesting || !testQuestion.trim()"
            class="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            <svg
              v-if="isTesting"
              class="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
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
            {{ isTesting ? "生成中..." : "测试回答" }}
          </button>
        </div>

        <!-- 回答展示 -->
        <div v-if="testReply" class="mb-6">
          <div
            class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-200"
          >
            <div class="text-sm font-semibold text-blue-900 mb-2">
              Agent 回答：
            </div>
            <div class="text-gray-800 whitespace-pre-wrap leading-relaxed">
              {{ testReply }}
            </div>
          </div>
        </div>

        <!-- 保存按钮 -->
        <div class="flex justify-between items-center">
          <p class="text-sm text-gray-500">
            {{ testReply ? "✅ 满意回答即可保存" : "💡 建议先测试对话效果" }}
          </p>
          <div class="flex gap-3">
            <button
              @click="handleBackToForm"
              class="px-6 py-3 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition font-semibold"
            >
              重新填写
            </button>
            <button
              @click="handleSave"
              :disabled="isSaving"
              class="px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:from-blue-700 hover:to-indigo-700 transition font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              <svg
                v-if="isSaving"
                class="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
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
              {{ isSaving ? "保存中..." : "保存修改" }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
