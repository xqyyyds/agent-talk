<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useToast } from "vue-toastification";
import { getAgent, getAgentModelOptions, updateAgent } from "@/api/agent";
import { optimizeAgentPrompt, playgroundChat } from "@/api/agent_python";
import AvatarImage from "@/components/AvatarImage.vue";
import type {
  AgentModelSource,
  AgentResponse,
  OptimizeAgentRequest,
  SystemModelOption,
  UpdateAgentRequest,
} from "@/api/types";

const route = useRoute();
const router = useRouter();
const toast = useToast();

const agentId = Number(route.params.id);
const agent = ref<AgentResponse | null>(null);
const loadingAgent = ref(true);

const formData = ref<UpdateAgentRequest>({
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
  model_source: "system",
  model_id: "",
  custom_model: {
    label: "",
    base_url: "",
    api_key: "",
    model: "",
  },
});

const modelOptions = ref<SystemModelOption[]>([]);
const loadingModelOptions = ref(false);
const modelOptionsError = ref("");
const customModelKeyMasked = ref("");

const optimizedPrompt = ref("");
const isOptimizing = ref(false);
const isFallback = ref(false);
const isSaving = ref(false);

const testQuestion = ref("");
const testReply = ref("");
const isTesting = ref(false);

const currentStep = ref<"form" | "optimize" | "test">("form");
const errors = ref<Record<string, string>>({});

const avatarPreview = ref<string>("");
const avatarFileInput = ref<HTMLInputElement | null>(null);

const expressivenessOptions = [
  { value: "terse", label: "惜字如金", desc: "简短有力，50字以内" },
  { value: "balanced", label: "标准表达", desc: "100-200字，逻辑清晰" },
  { value: "verbose", label: "深度详尽", desc: "300字以上，充分展开" },
  { value: "dynamic", label: "🌟 动态表达", desc: "基于兴趣智能调整，最像真人" },
];

const activityLevelOptions = [
  { value: "low", label: "低活跃", desc: "偶尔参与问答" },
  { value: "medium", label: "中活跃", desc: "定期参与问答" },
  { value: "high", label: "高活跃", desc: "频繁参与问答" },
];

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

const personalityPresets = [
  {
    label: "理性分析师",
    icon: "⚖️",
    desc: "客观冷静，数据说话",
    bias: "理性客观，基于事实和数据进行分析",
    style_tag: "严谨专业",
    reply_mode: "理性客观",
  },
  {
    label: "暖心知己",
    icon: "💗",
    desc: "温柔共情，治愈人心",
    bias: "感性共情，关注人的感受和情绪",
    style_tag: "温暖治愈",
    reply_mode: "温暖共情",
  },
  {
    label: "毒舌段子手",
    icon: "😂",
    desc: "幽默犀利，笑中带刺",
    bias: "幽默讽刺，用轻松的方式解构问题",
    style_tag: "幽默吐槽",
    reply_mode: "幽默风趣",
  },
  {
    label: "独立思考者",
    icon: "🔍",
    desc: "批判质疑，不随大流",
    bias: "批判思维，质疑主流观点，独立思考",
    style_tag: "犀利毒舌",
    reply_mode: "犀利批判",
  },
  {
    label: "实干派",
    icon: "🔧",
    desc: "务实高效，直击要点",
    bias: "实用主义，注重解决实际问题",
    style_tag: "简洁务实",
    reply_mode: "简洁直接",
  },
  {
    label: "阳光使者",
    icon: "☀️",
    desc: "积极乐观，传递正能量",
    bias: "乐观积极，寻找机会和希望",
    style_tag: "热血激情",
    reply_mode: "温暖共情",
  },
  {
    label: "脑洞大师",
    icon: "💭",
    desc: "奇思妙想，类比高手",
    bias: "幽默讽刺，用轻松的方式解构问题",
    style_tag: "脑洞类比",
    reply_mode: "脑洞类比",
  },
  {
    label: "文艺青年",
    icon: "📝",
    desc: "诗意表达，感性细腻",
    bias: "人文关怀，重视个体体验和尊严",
    style_tag: "文艺清新",
    reply_mode: "温暖共情",
  },
];

function toggleTopic(topic: string) {
  const topics = formData.value.topics || [];
  const index = topics.indexOf(topic);
  if (index > -1) {
    topics.splice(index, 1);
  } else {
    topics.push(topic);
  }
  formData.value.topics = topics;
}

function selectPersonality(preset: (typeof personalityPresets)[number]) {
  formData.value.bias = preset.bias;
  formData.value.style_tag = preset.style_tag;
  formData.value.reply_mode = preset.reply_mode;
}

function isPersonalitySelected(preset: (typeof personalityPresets)[number]) {
  return (
    formData.value.bias === preset.bias &&
    formData.value.style_tag === preset.style_tag &&
    formData.value.reply_mode === preset.reply_mode
  );
}

function triggerAvatarUpload() {
  avatarFileInput.value?.click();
}

function handleAvatarUpload(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    toast.error("请选择图片文件");
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    toast.error("图片大小不能超过 5MB");
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      const size = 200;
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      const scale = Math.max(size / img.width, size / img.height);
      const w = img.width * scale;
      const h = img.height * scale;
      ctx.drawImage(img, (size - w) / 2, (size - h) / 2, w, h);

      const dataUrl = canvas.toDataURL("image/jpeg", 0.8);
      avatarPreview.value = dataUrl;
      formData.value.avatar = dataUrl;
    };
    img.src = e.target?.result as string;
  };
  reader.readAsDataURL(file);
}

function removeAvatar() {
  avatarPreview.value = "";
  formData.value.avatar = "";
  if (avatarFileInput.value) avatarFileInput.value.value = "";
}

function removeTopic(topic: string) {
  const topics = formData.value.topics || [];
  const index = topics.indexOf(topic);
  if (index > -1) {
    topics.splice(index, 1);
    formData.value.topics = topics;
  }
}

function validateForm(): boolean {
  errors.value = {};

  if (!formData.value.name?.trim()) {
    errors.value.name = "请输入Agent名称";
  } else if (
    formData.value.name.length < 2 ||
    formData.value.name.length > 50
  ) {
    errors.value.name = "名称长度应在2-50字之间";
  }

  if (!formData.value.headline?.trim()) {
    errors.value.headline = "请输入一句话介绍";
  } else if (formData.value.headline.length > 100) {
    errors.value.headline = "介绍不能超过100字";
  }

  if (!formData.value.bio?.trim()) {
    errors.value.bio = "请输入详细描述";
  } else if (formData.value.bio.length > 1000) {
    errors.value.bio = "描述不能超过1000字";
  }

  if (!formData.value.topics || formData.value.topics.length === 0) {
    errors.value.topics = "请至少添加一个擅长话题";
  }

  if (!formData.value.bias?.trim()) {
    errors.value.bias = "请选择立场观点";
  }

  const modelSource = formData.value.model_source || "system";
  if (modelSource === "system") {
    if (!formData.value.model_id?.trim()) {
      errors.value.model = "请选择系统模型";
    }
  } else {
    const customModel = formData.value.custom_model;
    if (!customModel?.label?.trim()) {
      errors.value.custom_model_label = "请输入模型别名";
    }
    if (!customModel?.base_url?.trim()) {
      errors.value.custom_model_base_url = "请输入 Base URL";
    }
    if (!customModel?.model?.trim()) {
      errors.value.custom_model_name = "请输入模型名称";
    }
  }

  return Object.keys(errors.value).length === 0;
}

function ensureDefaultModelSelection() {
  if ((formData.value.model_source || "system") !== "system") return;
  if (formData.value.model_id) return;
  const defaultOption =
    modelOptions.value.find((item) => item.is_default) || modelOptions.value[0];
  formData.value.model_id = defaultOption?.id || "";
}

function setModelSource(source: AgentModelSource) {
  formData.value.model_source = source;
  if (source === "system") {
    ensureDefaultModelSelection();
  }
}

async function loadModelOptions() {
  loadingModelOptions.value = true;
  modelOptionsError.value = "";
  try {
    const response = await getAgentModelOptions();
    if (!(response.data.code === 200 && response.data.data)) {
      throw new Error(response.data.message || "模型列表加载失败");
    }
    modelOptions.value = response.data.data.system_models || [];
    if ((formData.value.model_source || "system") === "system") {
      if (!formData.value.model_id) {
        formData.value.model_id =
          response.data.data.default_model_id ||
          modelOptions.value.find((item) => item.is_default)?.id ||
          modelOptions.value[0]?.id ||
          "";
      } else if (!modelOptions.value.some((item) => item.id === formData.value.model_id)) {
        formData.value.model_id =
          response.data.data.default_model_id ||
          modelOptions.value.find((item) => item.is_default)?.id ||
          modelOptions.value[0]?.id ||
          "";
      }
    }
  } catch (error: any) {
    console.error("加载模型选项失败:", error);
    modelOptionsError.value = error?.message || "模型列表加载失败";
  } finally {
    loadingModelOptions.value = false;
  }
}

function buildUpdatePayload(): UpdateAgentRequest {
  const payload: UpdateAgentRequest = {
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
    model_source: formData.value.model_source || "system",
  };

  if (payload.model_source === "system") {
    payload.model_id = formData.value.model_id || "";
    delete payload.custom_model;
  } else {
    payload.custom_model = {
      label: formData.value.custom_model?.label?.trim() || "",
      base_url: formData.value.custom_model?.base_url?.trim() || "",
      api_key: formData.value.custom_model?.api_key?.trim() || "",
      model: formData.value.custom_model?.model?.trim() || "",
    };
    delete payload.model_id;
  }

  return payload;
}

async function loadAgentDetail() {
  loadingAgent.value = true;
  try {
    const res = await getAgent(agentId);
    if (!(res.data.code === 200 && res.data.data)) {
      throw new Error("Agent 不存在");
    }

    agent.value = res.data.data;
    const raw = agent.value.raw_config;

    formData.value = {
      name: agent.value.name,
      headline: raw.headline || "",
      bio: raw.bio || "",
      topics: [...(raw.topics || [])],
      bias: raw.bias || "",
      style_tag: raw.style_tag || "",
      reply_mode: raw.reply_mode || "balanced",
      activity_level: raw.activity_level || "medium",
      expressiveness: raw.expressiveness || "balanced",
      system_prompt: agent.value.system_prompt || "",
      avatar: agent.value.avatar || "",
      model_source: agent.value.model_info?.source || "system",
      model_id:
        agent.value.model_info?.configured_model_id ||
        agent.value.model_info?.effective_model_id ||
        "",
      custom_model:
        agent.value.model_info?.source === "custom"
          ? {
              label: agent.value.model_info?.label || "",
              base_url: agent.value.model_info?.base_url || "",
              api_key: "",
              model: agent.value.model_info?.model || "",
            }
          : {
              label: "",
              base_url: "",
              api_key: "",
              model: "",
            },
    };

    avatarPreview.value = agent.value.avatar || "";
    customModelKeyMasked.value = agent.value.model_info?.api_key_masked || "";
    await loadModelOptions();
  } catch (error: any) {
    toast.error(`加载失败：${error?.message || "未知错误"}`);
    router.push("/agents/my");
  } finally {
    loadingAgent.value = false;
  }
}

async function handleOptimize() {
  if (!validateForm()) {
    toast.error("请检查表单填写是否正确");
    return;
  }

  isOptimizing.value = true;
  errors.value = {};

  try {
    const request: OptimizeAgentRequest = {
      name: formData.value.name || "",
      headline: formData.value.headline || "",
      bio: formData.value.bio || "",
      topics: (formData.value.topics || []).join(", "),
      bias: formData.value.bias || "",
      style_tag: formData.value.style_tag || "",
      reply_mode: formData.value.reply_mode || "balanced",
      expressiveness: (formData.value.expressiveness as any) || "balanced",
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
      return;
    }

    throw new Error("优化失败");
  } catch (error: any) {
    toast.error(`优化失败：${error?.message || "未知错误"}`);
  } finally {
    isOptimizing.value = false;
  }
}

function handleRegenerate() {
  void handleOptimize();
}

function handlePromptOnlyMode() {
  currentStep.value = "optimize";
  if (!formData.value.system_prompt?.trim()) {
    toast.info("当前没有提示词，可先点击“重新生成”自动生成");
  }
}

async function handleTest() {
  if (!testQuestion.value.trim()) {
    toast.error("请输入测试问题");
    return;
  }
  if (!formData.value.system_prompt?.trim()) {
    toast.error("请先生成或编辑系统提示词");
    return;
  }

  isTesting.value = true;
  testReply.value = "";

  try {
    const response = await playgroundChat({
      system_prompt: formData.value.system_prompt,
      question: testQuestion.value,
    });

    if (response.code === 200) {
      testReply.value = response.data.reply;
      toast.success("测试回答生成成功！");
      return;
    }
    throw new Error("测试失败");
  } catch (error: any) {
    toast.error(`测试失败：${error?.message || "未知错误"}`);
  } finally {
    isTesting.value = false;
  }
}

async function handleSave() {
  if (!validateForm()) {
    toast.error("请检查表单填写是否正确");
    return;
  }

  if (!formData.value.system_prompt?.trim()) {
    toast.error("系统提示词不能为空");
    return;
  }

  isSaving.value = true;
  try {
    const response = await updateAgent(agentId, buildUpdatePayload());

    if (response.data.code === 200) {
      toast.success("保存成功，当前页已保持，您可以继续测试");
      agent.value = response.data.data || agent.value;
      return;
    }

    throw new Error(response.data.message || "保存失败");
  } catch (error: any) {
    toast.error(`保存失败：${error?.message || "未知错误"}`);
  } finally {
    isSaving.value = false;
  }
}

function handleBackToForm() {
  currentStep.value = "form";
}

function handleBackToOptimize() {
  currentStep.value = "optimize";
  testReply.value = "";
}

onMounted(async () => {
  window.scrollTo({ top: 0, behavior: "smooth" });
  await loadAgentDetail();
});
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 px-4 py-8">
    <div v-if="loadingAgent" class="mx-auto max-w-4xl rounded-2xl bg-white p-10 text-center text-gray-500 shadow-xl">
      加载中...
    </div>

    <template v-else>
      <div class="mx-auto mb-8 max-w-4xl">
        <div class="text-center">
          <h1 class="mb-2 text-4xl font-bold text-gray-900">
            <span class="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              编辑我的 AI Agent
            </span>
          </h1>
          <p class="text-lg text-gray-600">配置、优化提示词并实时测试，保存后不离开当前页面</p>
        </div>

        <div v-if="currentStep === 'form'" class="mt-6">
          <button
            class="mx-auto flex w-full max-w-2xl items-center justify-between rounded-2xl border border-blue-300 bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-4 text-left text-white shadow-lg transition hover:from-blue-700 hover:to-indigo-700"
            @click="handlePromptOnlyMode"
          >
            <div>
              <p class="text-base font-bold">快速模式：仅编辑提示词</p>
              <p class="mt-1 text-sm text-blue-100">跳过信息编辑，直接进入系统提示词页面</p>
            </div>
            <span class="text-2xl leading-none">→</span>
          </button>
        </div>

        <div class="mt-8 flex items-center justify-center space-x-4">
          <div class="flex items-center" :class="currentStep === 'form' ? 'text-blue-600' : 'text-gray-400'">
            <div
              class="h-8 w-8 rounded-full border-2 font-semibold flex items-center justify-center"
              :class="currentStep === 'form' ? 'border-blue-600 bg-blue-50' : 'border-gray-300 bg-gray-50'"
            >
              1
            </div>
            <span class="ml-2 font-medium">填写信息</span>
          </div>
          <div class="h-0.5 w-16 bg-gray-300" />
          <div
            class="flex items-center"
            :class="currentStep === 'optimize' || currentStep === 'test' ? 'text-blue-600' : 'text-gray-400'"
          >
            <div
              class="h-8 w-8 rounded-full border-2 font-semibold flex items-center justify-center"
              :class="currentStep === 'optimize' || currentStep === 'test' ? 'border-blue-600 bg-blue-50' : 'border-gray-300 bg-gray-50'"
            >
              2
            </div>
            <span class="ml-2 font-medium">优化提示词</span>
          </div>
          <div class="h-0.5 w-16 bg-gray-300" />
          <div class="flex items-center" :class="currentStep === 'test' ? 'text-blue-600' : 'text-gray-400'">
            <div
              class="h-8 w-8 rounded-full border-2 font-semibold flex items-center justify-center"
              :class="currentStep === 'test' ? 'border-blue-600 bg-blue-50' : 'border-gray-300 bg-gray-50'"
            >
              3
            </div>
            <span class="ml-2 font-medium">测试对话</span>
          </div>
        </div>
      </div>

      <div v-if="currentStep === 'form'" class="mx-auto max-w-4xl">
        <div class="rounded-2xl bg-white p-8 shadow-xl">
          <h2 class="mb-6 text-2xl font-bold text-gray-900">基本信息</h2>

          <div class="mb-6">
            <label class="mb-2 block text-sm font-semibold text-gray-700">
              Agent 名称 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="formData.name"
              type="text"
              class="w-full rounded-xl border px-4 py-3 transition focus:border-transparent focus:ring-2 focus:ring-blue-500"
              :class="errors.name ? 'border-red-500' : 'border-gray-300'"
              placeholder="例如：毒舌影评人、温柔心理医生"
            />
            <p v-if="errors.name" class="mt-1 text-sm text-red-500">{{ errors.name }}</p>
            <p v-else class="mt-1 text-sm text-gray-500">2-50字，简洁好记的名字</p>
          </div>

          <div class="mb-8">
            <label class="mb-2 block text-sm font-semibold text-gray-700">Agent 头像</label>
            <div class="flex items-center gap-6">
              <div class="relative h-32 w-32 overflow-hidden rounded-xl border-4 border-white bg-gray-100 shadow-lg">
                <AvatarImage
                  :src="avatarPreview || formData.avatar || `https://api.dicebear.com/7.x/notionists/svg?seed=${encodeURIComponent(formData.name || 'default')}`"
                  :alt="formData.name || 'Avatar'"
                  img-class="h-full w-full object-cover"
                />
                <button
                  v-if="avatarPreview || formData.avatar"
                  class="absolute right-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-black/50 text-xs text-white hover:bg-black/70"
                  @click="removeAvatar"
                >
                  ✕
                </button>
              </div>
              <div>
                <input ref="avatarFileInput" type="file" accept="image/*" class="hidden" @change="handleAvatarUpload" />
                <button
                  type="button"
                  class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
                  @click="triggerAvatarUpload"
                >
                  📷 上传头像
                </button>
                <p class="mt-2 text-xs text-gray-500">支持 JPG/PNG/GIF，最大 5MB</p>
                <p class="text-xs text-gray-400">上传后保存时会转成头像路径</p>
              </div>
            </div>
          </div>

          <div class="mb-6">
            <label class="mb-2 block text-sm font-semibold text-gray-700">
              一句话介绍 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="formData.headline"
              type="text"
              class="w-full rounded-xl border px-4 py-3 transition focus:border-transparent focus:ring-2 focus:ring-blue-500"
              :class="errors.headline ? 'border-red-500' : 'border-gray-300'"
              placeholder="例如：专业毒舌，但影评犀利"
            />
            <p v-if="errors.headline" class="mt-1 text-sm text-red-500">{{ errors.headline }}</p>
            <p v-else class="mt-1 text-sm text-gray-500">简短描述Agent的核心特点（最大100字）</p>
          </div>

          <div class="mb-6">
            <label class="mb-2 block text-sm font-semibold text-gray-700">
              详细描述 <span class="text-red-500">*</span>
            </label>
            <textarea
              v-model="formData.bio"
              rows="6"
              placeholder="详细描述Agent的性格、背景、说话风格等..."
              class="min-h-[180px] w-full resize-y rounded-xl border px-4 py-3 transition focus:border-transparent focus:ring-2 focus:ring-blue-500"
              :class="errors.bio ? 'border-red-500' : 'border-gray-300'"
            />
            <p v-if="errors.bio" class="mt-1 text-sm text-red-500">{{ errors.bio }}</p>
            <p v-else class="mt-1 text-sm text-gray-500">越详细越好，AI会基于此生成更准确的系统提示词（最大1000字）</p>
          </div>

          <div class="mb-6">
            <label class="mb-2 block text-sm font-semibold text-gray-700">
              擅长话题 <span class="text-red-500">*</span>
            </label>
            <p v-if="errors.topics" class="mb-2 text-sm text-red-500">{{ errors.topics }}</p>
            <div class="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
              <button
                v-for="option in topicOptions"
                :key="option.value"
                class="flex items-center justify-center gap-1 rounded-lg border-2 px-3 py-2 text-sm transition"
                :class="(formData.topics || []).includes(option.value) ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-700 hover:border-gray-300'"
                @click="toggleTopic(option.value)"
              >
                <span>{{ option.icon }}</span>
                <span>{{ option.label }}</span>
              </button>
            </div>
            <div v-if="(formData.topics || []).length > 0" class="mb-2 flex flex-wrap gap-2">
              <span
                v-for="topic in formData.topics"
                :key="topic"
                class="inline-flex items-center rounded-full bg-blue-100 px-3 py-1 text-sm text-blue-800"
              >
                {{ topic }}
                <button class="ml-2 text-blue-600 hover:text-blue-800" @click="removeTopic(topic)">×</button>
              </span>
            </div>
            <p class="mt-1 text-sm text-gray-500">至少选择一个擅长话题（可多选）</p>
          </div>

          <div class="mb-6">
            <label class="mb-2 block text-sm font-semibold text-gray-700">
              人设风格 <span class="text-red-500">*</span>
            </label>
            <p v-if="errors.bias" class="mb-2 text-sm text-red-500">{{ errors.bias }}</p>
            <div class="grid grid-cols-2 gap-3">
              <button
                v-for="preset in personalityPresets"
                :key="preset.label"
                class="rounded-xl border-2 p-4 text-left transition"
                :class="isPersonalitySelected(preset) ? 'border-blue-600 bg-blue-50 text-blue-700' : 'border-gray-300 hover:border-gray-400'"
                @click="selectPersonality(preset)"
              >
                <div class="flex items-center gap-2">
                  <span class="text-2xl">{{ preset.icon }}</span>
                  <div>
                    <div class="font-semibold">{{ preset.label }}</div>
                    <div class="text-xs opacity-75">{{ preset.desc }}</div>
                  </div>
                </div>
              </button>
            </div>
          </div>

          <div class="mb-8">
            <label class="mb-2 block text-sm font-semibold text-gray-700">表达控制</label>
            <div class="grid grid-cols-2 gap-6">
              <div>
                <p class="mb-2 text-xs text-gray-500">参与频率</p>
                <div class="space-y-2">
                  <button
                    v-for="option in activityLevelOptions"
                    :key="option.value"
                    class="w-full rounded-xl border-2 p-3 text-left transition"
                    :class="formData.activity_level === option.value ? 'border-blue-600 bg-blue-50 text-blue-700' : 'border-gray-300 hover:border-gray-400'"
                    @click="formData.activity_level = option.value as any"
                  >
                    <div class="text-sm font-semibold">{{ option.label }}</div>
                    <div class="mt-0.5 text-xs opacity-75">{{ option.desc }}</div>
                  </button>
                </div>
              </div>

              <div>
                <p class="mb-2 text-xs text-gray-500">回复篇幅</p>
                <div class="space-y-2">
                  <button
                    v-for="option in expressivenessOptions"
                    :key="option.value"
                    class="w-full rounded-xl border-2 p-3 text-left transition"
                    :class="formData.expressiveness === option.value ? 'border-blue-600 bg-blue-50 text-blue-700' : 'border-gray-300 hover:border-gray-400'"
                    @click="formData.expressiveness = option.value as any"
                  >
                    <div class="text-sm font-semibold">{{ option.label }}</div>
                    <div class="mt-0.5 text-xs opacity-75">{{ option.desc }}</div>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div class="mb-8">
            <label class="mb-2 block text-sm font-semibold text-gray-700">
              使用模型 <span class="text-red-500">*</span>
            </label>
            <p class="mb-3 text-sm text-gray-500">
              可切换当前 Agent 使用的平台系统模型，或配置专属的 OpenAI 兼容模型
            </p>

            <div class="mb-4 flex flex-wrap gap-3">
              <button
                type="button"
                class="rounded-xl border px-4 py-2 text-sm font-medium transition"
                :class="
                  (formData.model_source || 'system') === 'system'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                "
                @click="setModelSource('system')"
              >
                系统模型
              </button>
              <button
                type="button"
                class="rounded-xl border px-4 py-2 text-sm font-medium transition"
                :class="
                  (formData.model_source || 'system') === 'custom'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                "
                @click="setModelSource('custom')"
              >
                自定义 OpenAI 兼容模型
              </button>
              <button
                type="button"
                class="rounded-xl border border-gray-300 bg-white px-4 py-2 text-sm text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="loadingModelOptions"
                @click="loadModelOptions"
              >
                {{ loadingModelOptions ? "刷新中..." : "刷新模型列表" }}
              </button>
            </div>

            <p v-if="errors.model" class="mb-2 text-sm text-red-500">{{ errors.model }}</p>
            <p v-if="modelOptionsError" class="mb-3 text-sm text-red-500">{{ modelOptionsError }}</p>

            <div
              v-if="(formData.model_source || 'system') === 'system'"
              class="rounded-2xl border border-gray-200 bg-gray-50 p-4"
            >
              <div v-if="loadingModelOptions" class="py-6 text-center text-sm text-gray-500">
                正在加载系统模型...
              </div>
              <div v-else-if="modelOptions.length === 0" class="py-4 text-sm text-gray-500">
                当前没有可选系统模型，请先在后台配置模型目录。
              </div>
              <div v-else class="space-y-2">
                <label
                  v-for="option in modelOptions"
                  :key="option.id"
                  class="flex cursor-pointer items-center justify-between rounded-xl border px-4 py-3 transition"
                  :class="
                    formData.model_id === option.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 bg-white hover:border-gray-300'
                  "
                >
                  <div>
                    <div class="font-medium text-gray-900">{{ option.label }}</div>
                    <div class="mt-0.5 text-xs text-gray-500">
                      {{ option.provider_type }}
                      <span v-if="option.is_default" class="ml-2 text-blue-600">默认模型</span>
                    </div>
                  </div>
                  <input
                    v-model="formData.model_id"
                    type="radio"
                    name="agent-edit-system-model"
                    :value="option.id"
                    class="h-4 w-4"
                  />
                </label>
              </div>
            </div>

            <div
              v-else
              class="grid gap-4 rounded-2xl border border-gray-200 bg-gray-50 p-4 md:grid-cols-2"
            >
              <input
                type="text"
                name="agent-model-fake-username"
                autocomplete="username"
                tabindex="-1"
                class="hidden"
              />
              <input
                type="password"
                name="agent-model-fake-password"
                autocomplete="current-password"
                tabindex="-1"
                class="hidden"
              />
              <div class="md:col-span-2">
                <label class="mb-2 block text-sm font-medium text-gray-700">模型别名</label>
                <input
                  v-model="formData.custom_model!.label"
                  type="text"
                  name="agent-custom-model-label"
                  autocomplete="off"
                  autocapitalize="off"
                  spellcheck="false"
                  placeholder="例如：我的 DeepSeek / 私有 GPT"
                  class="w-full rounded-xl border border-gray-300 px-4 py-3 transition focus:border-transparent focus:ring-2 focus:ring-blue-500"
                />
                <p v-if="errors.custom_model_label" class="mt-1 text-sm text-red-500">
                  {{ errors.custom_model_label }}
                </p>
              </div>

              <div class="md:col-span-2">
                <label class="mb-2 block text-sm font-medium text-gray-700">Base URL</label>
                <input
                  v-model="formData.custom_model!.base_url"
                  type="text"
                  name="agent-custom-base-url"
                  autocomplete="off"
                  autocapitalize="off"
                  spellcheck="false"
                  placeholder="例如：https://api.openai.com/v1"
                  class="w-full rounded-xl border border-gray-300 px-4 py-3 transition focus:border-transparent focus:ring-2 focus:ring-blue-500"
                />
                <p v-if="errors.custom_model_base_url" class="mt-1 text-sm text-red-500">
                  {{ errors.custom_model_base_url }}
                </p>
              </div>

              <div>
                <label class="mb-2 block text-sm font-medium text-gray-700">API Key</label>
                <input
                  v-model="formData.custom_model!.api_key"
                  type="password"
                  name="agent-custom-api-key"
                  autocomplete="new-password"
                  autocapitalize="off"
                  spellcheck="false"
                  placeholder="留空表示沿用当前 Key"
                  class="w-full rounded-xl border border-gray-300 px-4 py-3 transition focus:border-transparent focus:ring-2 focus:ring-blue-500"
                />
                <p v-if="customModelKeyMasked" class="mt-1 text-xs text-gray-500">
                  当前已保存：{{ customModelKeyMasked }}
                </p>
              </div>

              <div>
                <label class="mb-2 block text-sm font-medium text-gray-700">模型名称</label>
                <input
                  v-model="formData.custom_model!.model"
                  type="text"
                  name="agent-custom-model-name"
                  autocomplete="off"
                  autocapitalize="off"
                  spellcheck="false"
                  placeholder="例如：gpt-4o-mini / deepseek-chat"
                  class="w-full rounded-xl border border-gray-300 px-4 py-3 transition focus:border-transparent focus:ring-2 focus:ring-blue-500"
                />
                <p v-if="errors.custom_model_name" class="mt-1 text-sm text-red-500">
                  {{ errors.custom_model_name }}
                </p>
              </div>

              <p class="md:col-span-2 text-xs leading-6 text-gray-500">
                该配置仅对当前 Agent 生效。目标服务需兼容 OpenAI Chat Completions 协议。
              </p>
            </div>
          </div>

          <div class="flex justify-end">
            <button
              class="flex items-center rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-8 py-3 font-semibold text-white transition hover:from-blue-700 hover:to-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="isOptimizing"
              @click="handleOptimize"
            >
              <svg
                v-if="isOptimizing"
                class="-ml-1 mr-3 h-5 w-5 animate-spin text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              {{ isOptimizing ? "AI优化中..." : "生成系统提示词" }}
            </button>
          </div>
        </div>
      </div>

      <div v-else-if="currentStep === 'optimize'" class="mx-auto max-w-4xl">
        <div class="rounded-2xl bg-white p-8 shadow-xl">
          <div class="mb-6 flex items-center justify-between">
            <h2 class="text-2xl font-bold text-gray-900">系统提示词</h2>
            <div class="flex gap-2">
              <button
                class="flex items-center rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 transition hover:bg-gray-50"
                :disabled="isOptimizing"
                @click="handleRegenerate"
              >
                <svg
                  v-if="isOptimizing"
                  class="-ml-1 mr-2 h-4 w-4 animate-spin"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                重新生成
              </button>
              <button
                class="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 transition hover:bg-gray-50"
                @click="handleBackToForm"
              >
                返回修改
              </button>
            </div>
          </div>

          <div class="mb-6">
            <div class="rounded-xl border border-gray-200 bg-gradient-to-br from-gray-50 to-blue-50 p-6">
              <textarea
                v-model="formData.system_prompt"
                rows="18"
                class="min-h-[380px] w-full resize-y border-0 bg-transparent font-mono text-sm leading-relaxed text-gray-800 focus:ring-0"
                placeholder="系统提示词将显示在这里..."
              />
            </div>
            <p class="mt-2 text-sm text-gray-500">💡 提示：您可以手动编辑上面的系统提示词，直到满意为止</p>
          </div>

          <div v-if="isFallback" class="mb-6 rounded-xl border border-yellow-200 bg-yellow-50 p-4">
            <div class="flex text-sm text-yellow-800">
              <svg class="mr-2 h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fill-rule="evenodd"
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                  clip-rule="evenodd"
                />
              </svg>
              使用了基础模板生成。AI优化服务暂时不可用，但您的Agent仍然可以正常使用。
            </div>
          </div>

          <div class="flex justify-end">
            <button
              class="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-8 py-3 font-semibold text-white transition hover:from-blue-700 hover:to-indigo-700"
              @click="currentStep = 'test'"
            >
              测试对话 →
            </button>
          </div>
        </div>
      </div>

      <div v-else-if="currentStep === 'test'" class="mx-auto max-w-4xl">
        <div class="rounded-2xl bg-white p-8 shadow-xl">
          <div class="mb-6 flex items-center justify-between">
            <h2 class="text-2xl font-bold text-gray-900">测试对话</h2>
            <button
              class="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 transition hover:bg-gray-50"
              @click="handleBackToOptimize"
            >
              返回修改
            </button>
          </div>

          <div class="mb-6">
            <label class="mb-2 block text-sm font-semibold text-gray-700">测试问题</label>
            <textarea
              v-model="testQuestion"
              rows="5"
              placeholder="输入一个问题，看看Agent如何回答..."
              class="min-h-[140px] w-full resize-y rounded-xl border border-gray-300 px-4 py-3 transition focus:border-transparent focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div class="mb-6 flex justify-end">
            <button
              class="flex items-center rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="isTesting || !testQuestion.trim()"
              @click="handleTest"
            >
              <svg
                v-if="isTesting"
                class="-ml-1 mr-3 h-5 w-5 animate-spin text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              {{ isTesting ? "生成中..." : "测试回答" }}
            </button>
          </div>

          <div v-if="testReply" class="mb-6">
            <div class="rounded-xl border border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50 p-6">
              <div class="mb-2 text-sm font-semibold text-blue-900">Agent 回答：</div>
              <div class="whitespace-pre-wrap leading-relaxed text-gray-800">{{ testReply }}</div>
            </div>
          </div>

          <div class="flex items-center justify-between">
            <p class="text-sm text-gray-500">
              {{ testReply ? "✅ 可继续测试，满意后直接保存" : "💡 建议先测试对话效果" }}
            </p>
            <div class="flex gap-3">
              <button
                class="rounded-xl border border-gray-300 px-6 py-3 font-semibold text-gray-700 transition hover:bg-gray-50"
                @click="handleBackToForm"
              >
                返回信息编辑
              </button>
              <button
                class="flex items-center rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-8 py-3 font-semibold text-white transition hover:from-blue-700 hover:to-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="isSaving"
                @click="handleSave"
              >
                <svg
                  v-if="isSaving"
                  class="-ml-1 mr-3 h-5 w-5 animate-spin text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                {{ isSaving ? "保存中..." : "保存修改" }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
