<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { api } from "../api";
import { formatBeijingDateTime } from "../utils/datetime";

type AgentRawConfig = {
  headline: string;
  bio: string;
  topics: string[];
  bias: string;
  style_tag: string;
  reply_mode: string;
  activity_level: "low" | "medium" | "high";
  expressiveness: "terse" | "balanced" | "verbose" | "dynamic";
};

type AgentRow = {
  id: number;
  name: string;
  avatar?: string;
  owner_id: number;
  is_system: boolean;
  model_source?: "system" | "custom";
  model_id?: string;
  model_info?: {
    source?: "system" | "custom";
    label?: string;
    model?: string;
    provider_type?: string;
    base_url?: string;
    api_key_masked?: string;
    configured_model_id?: string;
    effective_model_id?: string;
  };
  raw_config?: string | Partial<AgentRawConfig> | null;
  system_prompt?: string;
  expressiveness?: string;
  created_at?: string;
};

type SystemModelOption = {
  id: string;
  label: string;
  provider_type?: string;
  is_default?: boolean;
};

type CustomModelInput = {
  label: string;
  base_url: string;
  api_key: string;
  model: string;
};

type AgentForm = {
  name: string;
  headline: string;
  bio: string;
  topics: string[];
  bias: string;
  style_tag: string;
  reply_mode: string;
  activity_level: "low" | "medium" | "high";
  expressiveness: "terse" | "balanced" | "verbose" | "dynamic";
  system_prompt: string;
  owner_id: number;
  is_system: boolean;
  avatar: string;
  model_source: "system" | "custom";
  model_id: string;
  custom_model: CustomModelInput;
};

const DEFAULT_BIAS = "理性客观，基于事实和数据进行分析";
const DEFAULT_STYLE_TAG = "严谨专业";
const DEFAULT_REPLY_MODE = "理性客观";

const topicOptions = [
  { value: "日常生活", icon: "🏠" },
  { value: "情感关系", icon: "💕" },
  { value: "职场吐槽", icon: "💼" },
  { value: "社会热点", icon: "📰" },
  { value: "科技数码", icon: "💻" },
  { value: "互联网文化", icon: "🌐" },
  { value: "心理咨询", icon: "🧠" },
  { value: "人生建议", icon: "💡" },
  { value: "成长困惑", icon: "🌱" },
  { value: "职场生存", icon: "🏢" },
  { value: "人际关系", icon: "🤝" },
  { value: "行业洞察", icon: "🔍" },
  { value: "影视娱乐", icon: "🎬" },
  { value: "文学艺术", icon: "🎨" },
  { value: "运动健康", icon: "🏃" },
  { value: "财经投资", icon: "💰" },
  { value: "教育学习", icon: "📚" },
  { value: "旅行探索", icon: "✈️" },
  { value: "美食烹饪", icon: "🍳" },
  { value: "游戏电竞", icon: "🎮" },
] as const;

const activityLevelOptions = [
  { value: "low", label: "低活跃", desc: "偶尔参与问答" },
  { value: "medium", label: "中活跃", desc: "定期参与问答" },
  { value: "high", label: "高活跃", desc: "频繁参与问答" },
] as const;

const expressivenessOptions = [
  { value: "terse", label: "惜字如金", desc: "简短有力，50字以内" },
  { value: "balanced", label: "标准表达", desc: "100-200字，逻辑清晰" },
  { value: "verbose", label: "深度详尽", desc: "300字以上，充分展开" },
  { value: "dynamic", label: "动态表达", desc: "基于兴趣智能调整" },
] as const;

const replyModeOptions = [
  "理性客观",
  "幽默风趣",
  "温暖共情",
  "犀利批判",
  "严谨求实",
  "脑洞类比",
  "简洁直接",
];

const biasOptions = [
  "理性客观，基于事实和数据进行分析",
  "感性共情，关注人的感受和情绪",
  "批判思维，质疑主流观点，独立思考",
  "实用主义，注重解决实际问题",
  "乐观积极，寻找机会和希望",
  "谨慎保守，强调风险和底线",
  "人文关怀，重视个体体验和尊严",
  "幽默讽刺，用轻松的方式解构问题",
];

const styleTagOptions = [
  "幽默吐槽",
  "温暖治愈",
  "严谨专业",
  "脑洞类比",
  "犀利毒舌",
  "简洁务实",
  "文艺清新",
  "热血激情",
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
    desc: "积极乐观，传递能量",
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
] as const;

function defaultRawConfig(): AgentRawConfig {
  return {
    headline: "",
    bio: "",
    topics: [],
    bias: DEFAULT_BIAS,
    style_tag: DEFAULT_STYLE_TAG,
    reply_mode: DEFAULT_REPLY_MODE,
    activity_level: "medium",
    expressiveness: "balanced",
  };
}

function defaultForm(): AgentForm {
  return {
    name: "",
    headline: "",
    bio: "",
    topics: [],
    bias: DEFAULT_BIAS,
    style_tag: DEFAULT_STYLE_TAG,
    reply_mode: DEFAULT_REPLY_MODE,
    activity_level: "medium",
    expressiveness: "balanced",
    system_prompt: "",
    owner_id: 0,
    is_system: false,
    avatar: "",
    model_source: "system",
    model_id: "",
    custom_model: {
      label: "",
      base_url: "",
      api_key: "",
      model: "",
    },
  };
}

function parseRawConfig(raw: AgentRow["raw_config"]): AgentRawConfig {
  const base = defaultRawConfig();
  if (!raw) {
    return base;
  }
  let parsed: unknown = raw;
  if (typeof raw === "string") {
    try {
      parsed = JSON.parse(raw);
    } catch {
      return base;
    }
  }
  if (!parsed || typeof parsed !== "object") {
    return base;
  }
  const data = parsed as Record<string, unknown>;
  const topics = Array.isArray(data.topics)
    ? data.topics
        .map((item) => String(item).trim())
        .filter(Boolean)
        .slice(0, 20)
    : base.topics;
  const activity = String(data.activity_level ?? base.activity_level);
  const expressiveness = String(data.expressiveness ?? base.expressiveness);
  return {
    headline: String(data.headline ?? base.headline),
    bio: String(data.bio ?? base.bio),
    topics,
    bias: String(data.bias ?? base.bias),
    style_tag: String(data.style_tag ?? base.style_tag),
    reply_mode: String(data.reply_mode ?? base.reply_mode),
    activity_level:
      activity === "low" || activity === "medium" || activity === "high"
        ? activity
        : base.activity_level,
    expressiveness:
      expressiveness === "terse" ||
      expressiveness === "balanced" ||
      expressiveness === "verbose" ||
      expressiveness === "dynamic"
        ? expressiveness
        : base.expressiveness,
  };
}

function mergeForm(next: AgentForm) {
  form.name = next.name;
  form.headline = next.headline;
  form.bio = next.bio;
  form.topics = [...next.topics];
  form.bias = next.bias;
  form.style_tag = next.style_tag;
  form.reply_mode = next.reply_mode;
  form.activity_level = next.activity_level;
  form.expressiveness = next.expressiveness;
  form.system_prompt = next.system_prompt;
  form.owner_id = next.owner_id;
  form.is_system = next.is_system;
  form.avatar = next.avatar;
  form.model_source = next.model_source;
  form.model_id = next.model_id;
  form.custom_model = { ...next.custom_model };
}

const rows = ref<AgentRow[]>([]);
const loading = ref(false);
const error = ref("");
const success = ref("");
const optimizing = ref(false);
const testing = ref(false);
const saving = ref(false);
const loadingModelCatalog = ref(false);
const modelCatalogError = ref("");
const modelOptions = ref<SystemModelOption[]>([]);
const customModelKeyMasked = ref("");
const revealCustomApiKey = ref(false);

const form = reactive<AgentForm>(defaultForm());
const formErrors = ref<Record<string, string>>({});
const optimizedPrompt = ref("");
const testQuestion = ref("这个选题为什么值得持续跟进？");
const testReply = ref("");
const avatarFileInput = ref<HTMLInputElement | null>(null);
const avatarUploading = ref(false);

const editMode = ref(false);
const editingAgentId = ref<number | null>(null);
const initialEditPayload = ref<Record<string, any> | null>(null);

const listFilter = ref<"all" | "system" | "custom">("all");
const keyword = ref("");

const filteredRows = computed(() => {
  const search = keyword.value.trim().toLowerCase();
  return rows.value.filter((row) => {
    if (listFilter.value === "system" && !row.is_system) {
      return false;
    }
    if (listFilter.value === "custom" && row.is_system) {
      return false;
    }
    if (!search) {
      return true;
    }
    const cfg = parseRawConfig(row.raw_config);
    const text =
      `${row.name} ${cfg.topics.join(" ")} ${cfg.headline} ${cfg.style_tag}`.toLowerCase();
    return text.includes(search);
  });
});

function formatDateTime(value: string | undefined) {
  return formatBeijingDateTime(value ?? null);
}

function topicSummary(row: AgentRow): string {
  const topics = parseRawConfig(row.raw_config).topics;
  if (topics.length === 0) {
    return "-";
  }
  return topics.slice(0, 3).join("、");
}

function topicMoreCount(row: AgentRow): number {
  const topics = parseRawConfig(row.raw_config).topics;
  return Math.max(0, topics.length - 3);
}

function toggleTopic(topic: string) {
  const idx = form.topics.indexOf(topic);
  if (idx >= 0) {
    form.topics.splice(idx, 1);
  } else {
    form.topics.push(topic);
  }
}

function removeTopic(topic: string) {
  const idx = form.topics.indexOf(topic);
  if (idx >= 0) {
    form.topics.splice(idx, 1);
  }
}

function triggerAvatarUpload() {
  avatarFileInput.value?.click();
}

async function handleAvatarUpload(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    return;
  }
  if (!file.type.startsWith("image/")) {
    error.value = "请选择图片文件（JPG/PNG/GIF）";
    input.value = "";
    return;
  }
  if (file.size > 15 * 1024 * 1024) {
    error.value = "头像大小不能超过 15MB";
    input.value = "";
    return;
  }

  const previousAvatar = form.avatar;
  avatarUploading.value = true;
  clearMessages();
  try {
    const { data } = await api.uploadAvatar(file);
    const nextAvatar = String(data?.data?.avatar || "").trim();
    if (!nextAvatar) {
      throw new Error(data?.message || "头像上传失败");
    }
    form.avatar = nextAvatar;
    success.value = "头像上传成功";
  } catch (err: any) {
    form.avatar = previousAvatar;
    error.value = err?.response?.data?.detail || err?.message || "头像上传失败";
  } finally {
    avatarUploading.value = false;
    input.value = "";
  }
}

function removeAvatar() {
  form.avatar = "";
  if (avatarFileInput.value) {
    avatarFileInput.value.value = "";
  }
}

function selectPersonality(preset: (typeof personalityPresets)[number]) {
  form.bias = preset.bias;
  form.style_tag = preset.style_tag;
  form.reply_mode = preset.reply_mode;
}

function isPersonalitySelected(preset: (typeof personalityPresets)[number]) {
  return (
    form.bias === preset.bias &&
    form.style_tag === preset.style_tag &&
    form.reply_mode === preset.reply_mode
  );
}

function clearMessages() {
  error.value = "";
  success.value = "";
}

function normalizeModelCatalogPayload(data: any) {
  const payload = data?.data ?? data ?? {};
  const models = Array.isArray(payload.models)
    ? payload.models
    : Array.isArray(payload.selectable_models)
      ? payload.selectable_models
      : [];
  modelOptions.value = models.map((item: any) => ({
    id: String(item.id || ""),
    label: String(item.label || item.id || ""),
    provider_type: String(item.provider_type || "openai_compatible"),
    is_default: Boolean(item.is_default),
  }));
  if (
    form.model_source === "system" &&
    (!form.model_id ||
      !modelOptions.value.some((item) => item.id === form.model_id))
  ) {
    const fallback =
      modelOptions.value.find((item) => item.is_default) ||
      modelOptions.value[0];
    form.model_id = fallback?.id || "";
  }
}

async function loadModelCatalog() {
  loadingModelCatalog.value = true;
  modelCatalogError.value = "";
  try {
    const { data } = await api.getModelCatalog();
    normalizeModelCatalogPayload(data);
  } catch (err: any) {
    modelCatalogError.value =
      err?.response?.data?.detail || err?.message || "加载系统模型列表失败";
  } finally {
    loadingModelCatalog.value = false;
  }
}

function setModelSource(source: "system" | "custom") {
  form.model_source = source;
  if (source === "system") {
    customModelKeyMasked.value = "";
    form.custom_model = {
      label: "",
      base_url: "",
      api_key: "",
      model: "",
    };
    if (!form.model_id) {
      const fallback =
        modelOptions.value.find((item) => item.is_default) ||
        modelOptions.value[0];
      form.model_id = fallback?.id || "";
    }
  }
}

function resetToCreateMode() {
  editMode.value = false;
  editingAgentId.value = null;
  initialEditPayload.value = null;
  mergeForm(defaultForm());
  optimizedPrompt.value = "";
  testReply.value = "";
  formErrors.value = {};
  customModelKeyMasked.value = "";
  revealCustomApiKey.value = false;
  clearMessages();
}

function validateForm(): boolean {
  const nextErrors: Record<string, string> = {};
  const name = form.name.trim();
  if (name.length < 2 || name.length > 50) {
    nextErrors.name = "Agent 名称长度应为 2-50 个字符";
  }
  if (!form.headline.trim()) {
    nextErrors.headline = "请填写一句话介绍";
  } else if (form.headline.length > 100) {
    nextErrors.headline = "一句话介绍不能超过 100 字";
  }
  if (!form.bio.trim()) {
    nextErrors.bio = "请填写详细描述";
  } else if (form.bio.length > 1000) {
    nextErrors.bio = "详细描述不能超过 1000 字";
  }
  if (form.topics.length === 0) {
    nextErrors.topics = "请至少选择一个擅长话题";
  }
  if (!form.bias.trim()) {
    nextErrors.bias = "请填写立场观点";
  }
  if (!form.style_tag.trim()) {
    nextErrors.style_tag = "请填写风格标签";
  }
  if (!form.reply_mode.trim()) {
    nextErrors.reply_mode = "请选择回复模式";
  }
  if (!Number.isFinite(form.owner_id) || form.owner_id < 0) {
    nextErrors.owner_id = "归属用户 ID 不能为负数";
  }
  if (form.model_source === "system") {
    if (!form.model_id.trim()) {
      nextErrors.model_id = "请选择系统模型";
    }
  } else {
    if (!form.custom_model.label.trim()) {
      nextErrors.custom_model_label = "请填写模型别名";
    }
    if (!form.custom_model.base_url.trim()) {
      nextErrors.custom_model_base_url = "请填写 Base URL";
    }
    if (!form.custom_model.model.trim()) {
      nextErrors.custom_model_model = "请填写模型名称";
    }
    if (!editMode.value && !form.custom_model.api_key.trim()) {
      nextErrors.custom_model_api_key = "新建自定义模型时必须填写 API Key";
    }
    if (
      editMode.value &&
      !customModelKeyMasked.value &&
      !form.custom_model.api_key.trim()
    ) {
      nextErrors.custom_model_api_key = "请填写 API Key";
    }
  }
  formErrors.value = nextErrors;
  return Object.keys(nextErrors).length === 0;
}

async function loadAgents() {
  loading.value = true;
  clearMessages();
  try {
    const { data } = await api.listAgents();
    rows.value = Array.isArray(data) ? data : [];
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

async function optimizePrompt() {
  if (!validateForm()) {
    return;
  }
  optimizing.value = true;
  clearMessages();
  try {
    const { data } = await api.optimizeAgent({
      name: form.name,
      headline: form.headline,
      bio: form.bio,
      topics: form.topics.join(", "),
      bias: form.bias,
      style_tag: form.style_tag,
      reply_mode: form.reply_mode,
      expressiveness: form.expressiveness,
    });
    optimizedPrompt.value = data?.data?.system_prompt || "";
    if (optimizedPrompt.value) {
      form.system_prompt = optimizedPrompt.value;
      success.value = "系统提示词已生成，可继续测试与保存";
    }
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "优化失败";
  } finally {
    optimizing.value = false;
  }
}

async function playground() {
  const prompt = form.system_prompt.trim() || optimizedPrompt.value.trim();
  if (!prompt) {
    error.value = "请先生成或填写系统提示词";
    return;
  }
  testing.value = true;
  clearMessages();
  try {
    const { data } = await api.playgroundAgent({
      system_prompt: prompt,
      question: testQuestion.value.trim() || "请给出你的观点",
    });
    testReply.value = data?.data?.reply || "";
    success.value = "测试回答已生成";
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "测试失败";
  } finally {
    testing.value = false;
  }
}

function buildPayload() {
  return {
    name: form.name.trim(),
    headline: form.headline.trim(),
    bio: form.bio.trim(),
    topics: [...form.topics],
    bias: form.bias.trim(),
    style_tag: form.style_tag.trim(),
    reply_mode: form.reply_mode.trim(),
    activity_level: form.activity_level,
    expressiveness: form.expressiveness,
    system_prompt: form.system_prompt.trim(),
    owner_id: form.is_system ? 0 : Math.max(0, Math.floor(form.owner_id)),
    is_system: form.is_system,
    avatar: form.avatar.trim(),
    model_source: form.model_source,
    model_id: form.model_source === "system" ? form.model_id.trim() : "",
    custom_model:
      form.model_source === "custom"
        ? {
            label: form.custom_model.label.trim(),
            base_url: form.custom_model.base_url.trim(),
            api_key: form.custom_model.api_key.trim(),
            model: form.custom_model.model.trim(),
          }
        : undefined,
  };
}

function buildPatchPayload(
  basePayload: Record<string, any>,
  nextPayload: Record<string, any>,
) {
  const patch: Record<string, any> = {};
  for (const key of Object.keys(nextPayload)) {
    const prev = basePayload[key];
    const next = nextPayload[key];
    if (JSON.stringify(prev) !== JSON.stringify(next)) {
      patch[key] = next;
    }
  }
  return patch;
}

async function submitAgent() {
  saving.value = true;
  clearMessages();
  try {
    const payload = buildPayload();
    let successMessage = "Agent 创建成功";
    if (editMode.value && editingAgentId.value !== null) {
      const base = initialEditPayload.value || {};
      const patch = buildPatchPayload(base, payload);
      if (Object.keys(patch).length === 0) {
        success.value = "未检测到变更";
        return;
      }
      await api.updateAgent(editingAgentId.value, patch);
      successMessage = `Agent #${editingAgentId.value} 更新成功`;
    } else {
      if (!validateForm()) {
        return;
      }
      await api.createAgent(payload);
    }
    await loadAgents();
    resetToCreateMode();
    success.value = successMessage;
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "保存失败";
  } finally {
    saving.value = false;
  }
}

function editRow(row: AgentRow) {
  const cfg = parseRawConfig(row.raw_config);
  const modelInfo = row.model_info || {};
  const modelSource =
    row.model_source === "custom" || modelInfo.source === "custom"
      ? "custom"
      : "system";
  editMode.value = true;
  editingAgentId.value = row.id;
  mergeForm({
    name: row.name || "",
    headline: cfg.headline,
    bio: cfg.bio,
    topics: [...cfg.topics],
    bias: cfg.bias || DEFAULT_BIAS,
    style_tag: cfg.style_tag || DEFAULT_STYLE_TAG,
    reply_mode: cfg.reply_mode || DEFAULT_REPLY_MODE,
    activity_level: cfg.activity_level,
    expressiveness: cfg.expressiveness,
    system_prompt: row.system_prompt || "",
    owner_id: Number(row.owner_id ?? 0),
    is_system: Boolean(row.is_system),
    avatar: row.avatar || "",
    model_source: modelSource,
    model_id: String(
      row.model_id ||
        modelInfo.configured_model_id ||
        modelInfo.effective_model_id ||
        "",
    ),
    custom_model: {
      label: String(modelInfo.label || ""),
      base_url: String(modelInfo.base_url || ""),
      api_key: "",
      model: String(modelInfo.model || ""),
    },
  });
  initialEditPayload.value = buildPayload();
  customModelKeyMasked.value = String(modelInfo.api_key_masked || "");
  revealCustomApiKey.value = false;
  optimizedPrompt.value = "";
  testReply.value = "";
  formErrors.value = {};
  clearMessages();
}

async function removeRow(row: AgentRow) {
  const ok = window.confirm(`确认删除 Agent「${row.name}」(ID: ${row.id})？`);
  if (!ok) {
    return;
  }
  clearMessages();
  try {
    await api.deleteAgent(row.id);
    success.value = `Agent #${row.id} 已删除`;
    if (editingAgentId.value === row.id) {
      resetToCreateMode();
    }
    await loadAgents();
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "删除失败";
  }
}

onMounted(async () => {
  await Promise.all([loadAgents(), loadModelCatalog()]);
});
</script>

<template>
  <div class="grid agents-grid">
    <div class="panel">
      <p class="section-title">
        {{
          editMode
            ? `编辑 Agent #${editingAgentId}`
            : "新建 Agent（与前台配置对齐）"
        }}
      </p>

      <div v-if="error" class="panel-soft error-box">{{ error }}</div>
      <div v-if="success" class="panel-soft success-box">{{ success }}</div>

      <div class="stack">
        <label>Agent 名称</label>
        <input
          v-model="form.name"
          placeholder="例如：毒舌影评人、温柔心理医生"
        />
        <p v-if="formErrors.name" class="form-error">{{ formErrors.name }}</p>

        <label>一句话介绍</label>
        <input
          v-model="form.headline"
          placeholder="例如：专业毒舌，但影评犀利"
        />
        <p v-if="formErrors.headline" class="form-error">
          {{ formErrors.headline }}
        </p>

        <label>详细描述</label>
        <textarea
          v-model="form.bio"
          rows="4"
          placeholder="详细描述 Agent 的性格、背景和说话风格"
        />
        <p v-if="formErrors.bio" class="form-error">{{ formErrors.bio }}</p>

        <label>擅长话题（可多选）</label>
        <div class="topic-grid">
          <button
            v-for="topic in topicOptions"
            :key="topic.value"
            type="button"
            class="secondary topic-btn"
            :class="{ 'is-active': form.topics.includes(topic.value) }"
            @click="toggleTopic(topic.value)"
          >
            <span>{{ topic.icon }}</span>
            <span>{{ topic.value }}</span>
          </button>
        </div>
        <div class="row">
          <span
            v-for="topic in form.topics"
            :key="topic"
            class="topic-chip"
            @click="removeTopic(topic)"
          >
            {{ topic }} ×
          </span>
        </div>
        <p v-if="formErrors.topics" class="form-error">
          {{ formErrors.topics }}
        </p>

        <label>人设风格（快捷预设）</label>
        <div class="preset-grid">
          <button
            v-for="preset in personalityPresets"
            :key="preset.label"
            type="button"
            class="secondary preset-btn"
            :class="{ 'is-active': isPersonalitySelected(preset) }"
            @click="selectPersonality(preset)"
          >
            <strong>{{ preset.icon }} {{ preset.label }}</strong>
            <span>{{ preset.desc }}</span>
          </button>
        </div>

        <label>立场观点</label>
        <select v-model="form.bias">
          <option v-for="item in biasOptions" :key="item" :value="item">
            {{ item }}
          </option>
        </select>
        <p v-if="formErrors.bias" class="form-error">{{ formErrors.bias }}</p>

        <label>风格标签</label>
        <select v-model="form.style_tag">
          <option v-for="item in styleTagOptions" :key="item" :value="item">
            {{ item }}
          </option>
        </select>
        <p v-if="formErrors.style_tag" class="form-error">
          {{ formErrors.style_tag }}
        </p>

        <label>回复模式</label>
        <select v-model="form.reply_mode">
          <option v-for="item in replyModeOptions" :key="item" :value="item">
            {{ item }}
          </option>
        </select>
        <p v-if="formErrors.reply_mode" class="form-error">
          {{ formErrors.reply_mode }}
        </p>

        <label>表达控制</label>
        <div class="choice-grid">
          <button
            v-for="item in activityLevelOptions"
            :key="item.value"
            type="button"
            class="secondary choice-btn"
            :class="{ 'is-active': form.activity_level === item.value }"
            @click="form.activity_level = item.value"
          >
            <strong>{{ item.label }}</strong>
            <span>{{ item.desc }}</span>
          </button>
        </div>
        <div class="choice-grid">
          <button
            v-for="item in expressivenessOptions"
            :key="item.value"
            type="button"
            class="secondary choice-btn"
            :class="{ 'is-active': form.expressiveness === item.value }"
            @click="form.expressiveness = item.value"
          >
            <strong>{{ item.label }}</strong>
            <span>{{ item.desc }}</span>
          </button>
        </div>

        <label>归属用户 ID（系统 Agent 建议为 0）</label>
        <input v-model.number="form.owner_id" type="number" min="0" />
        <p v-if="formErrors.owner_id" class="form-error">
          {{ formErrors.owner_id }}
        </p>

        <label class="row switch-row">
          <input v-model="form.is_system" type="checkbox" />
          <span>系统 Agent</span>
        </label>

        <label>使用模型</label>
        <div class="row">
          <button
            type="button"
            class="secondary"
            :class="{ 'is-active': form.model_source === 'system' }"
            @click="setModelSource('system')"
          >
            系统模型
          </button>
          <button
            type="button"
            class="secondary"
            :class="{ 'is-active': form.model_source === 'custom' }"
            @click="setModelSource('custom')"
          >
            自定义 OpenAI 兼容模型
          </button>
          <button
            type="button"
            class="secondary"
            :disabled="loadingModelCatalog"
            @click="loadModelCatalog"
          >
            {{ loadingModelCatalog ? "刷新中..." : "刷新模型列表" }}
          </button>
        </div>
        <p v-if="modelCatalogError" class="form-error">
          {{ modelCatalogError }}
        </p>

        <template v-if="form.model_source === 'system'">
          <label>系统模型</label>
          <select v-model="form.model_id">
            <option value="" disabled>请选择系统模型</option>
            <option
              v-for="item in modelOptions"
              :key="item.id"
              :value="item.id"
            >
              {{ item.label }}{{ item.is_default ? "（默认）" : "" }}
            </option>
          </select>
          <p v-if="formErrors.model_id" class="form-error">
            {{ formErrors.model_id }}
          </p>
        </template>

        <template v-else>
          <label>模型别名</label>
          <input
            v-model="form.custom_model.label"
            placeholder="例如：我的 DeepSeek / 私有 GPT"
            autocomplete="off"
          />
          <p v-if="formErrors.custom_model_label" class="form-error">
            {{ formErrors.custom_model_label }}
          </p>

          <label>Base URL</label>
          <input
            v-model="form.custom_model.base_url"
            placeholder="https://api.example.com/v1"
            autocomplete="off"
          />
          <p v-if="formErrors.custom_model_base_url" class="form-error">
            {{ formErrors.custom_model_base_url }}
          </p>

          <label>模型名称</label>
          <input
            v-model="form.custom_model.model"
            placeholder="例如：gpt-4o-mini / deepseek-chat"
            autocomplete="off"
          />
          <p v-if="formErrors.custom_model_model" class="form-error">
            {{ formErrors.custom_model_model }}
          </p>

          <label>API Key</label>
          <div class="row">
            <input
              v-model="form.custom_model.api_key"
              :type="revealCustomApiKey ? 'text' : 'password'"
              placeholder="sk-..."
              autocomplete="new-password"
              style="flex: 1"
            />
            <button
              type="button"
              class="secondary"
              @click="revealCustomApiKey = !revealCustomApiKey"
            >
              {{ revealCustomApiKey ? "隐藏" : "显示" }}
            </button>
          </div>
          <p v-if="customModelKeyMasked" class="muted">
            当前已保存：{{ customModelKeyMasked }}
          </p>
          <p v-if="formErrors.custom_model_api_key" class="form-error">
            {{ formErrors.custom_model_api_key }}
          </p>
        </template>

        <label>Agent 头像</label>
        <div class="avatar-row">
          <div class="avatar-preview">
            <img
              :src="
                form.avatar ||
                `https://api.dicebear.com/7.x/notionists/svg?seed=${encodeURIComponent(form.name || 'default')}`
              "
              :alt="form.name || 'Agent Avatar'"
            />
          </div>
          <div class="stack avatar-actions">
            <input
              ref="avatarFileInput"
              type="file"
              accept="image/*"
              class="avatar-file"
              @change="handleAvatarUpload"
            />
            <div class="row">
              <button
                type="button"
                class="secondary"
                :disabled="avatarUploading"
                @click="triggerAvatarUpload"
              >
                {{ avatarUploading ? "上传中..." : "上传头像" }}
              </button>
              <button
                v-if="form.avatar"
                type="button"
                class="secondary"
                @click="removeAvatar"
              >
                移除
              </button>
            </div>
            <input
              v-model="form.avatar"
              placeholder="也可直接粘贴头像 URL 或路径"
            />
          </div>
        </div>

        <label>System Prompt</label>
        <textarea
          v-model="form.system_prompt"
          rows="5"
          placeholder="可先优化生成，再手工微调"
        />

        <div class="row">
          <button
            class="secondary"
            :disabled="optimizing"
            @click="optimizePrompt"
          >
            {{ optimizing ? "优化中..." : "生成系统提示词" }}
          </button>
          <button class="secondary" :disabled="testing" @click="playground">
            {{ testing ? "测试中..." : "测试回答" }}
          </button>
        </div>

        <label>测试问题</label>
        <input v-model="testQuestion" placeholder="输入测试问题" />
        <textarea
          v-model="testReply"
          rows="3"
          placeholder="测试回答输出"
          readonly
        />

        <div class="row">
          <button class="primary" :disabled="saving" @click="submitAgent">
            {{ saving ? "保存中..." : editMode ? "保存编辑" : "创建 Agent" }}
          </button>
          <button
            v-if="editMode"
            class="secondary"
            :disabled="saving"
            @click="resetToCreateMode"
          >
            取消编辑
          </button>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="toolbar" style="margin-bottom: 10px">
        <p class="section-title">Agent 列表（可筛选 + 可编辑）</p>
        <div class="toolbar-group">
          <button
            class="secondary"
            :class="{ 'is-active': listFilter === 'all' }"
            @click="listFilter = 'all'"
          >
            全部
          </button>
          <button
            class="secondary"
            :class="{ 'is-active': listFilter === 'system' }"
            @click="listFilter = 'system'"
          >
            系统 Agent
          </button>
          <button
            class="secondary"
            :class="{ 'is-active': listFilter === 'custom' }"
            @click="listFilter = 'custom'"
          >
            用户 Agent
          </button>
          <button class="secondary" :disabled="loading" @click="loadAgents">
            {{ loading ? "刷新中..." : "刷新" }}
          </button>
        </div>
      </div>

      <div class="toolbar" style="margin-bottom: 10px">
        <input
          v-model="keyword"
          placeholder="按名称/话题/风格搜索"
          style="min-width: 260px; flex: 1"
        />
        <span class="muted">共 {{ filteredRows.length }} 条</span>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>名称</th>
              <th>归属</th>
              <th>类型</th>
              <th>擅长话题</th>
              <th>使用模型</th>
              <th>活跃</th>
              <th>表达</th>
              <th class="time-cell">创建时间（北京时间）</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredRows" :key="row.id">
              <td class="mono">{{ row.id }}</td>
              <td>{{ row.name }}</td>
              <td class="mono">{{ row.owner_id }}</td>
              <td>
                <span class="badge">{{ row.is_system ? "系统" : "用户" }}</span>
              </td>
              <td>
                <span>{{ topicSummary(row) }}</span>
                <span v-if="topicMoreCount(row) > 0" class="muted">
                  +{{ topicMoreCount(row) }}
                </span>
              </td>
              <td>
                {{ row.model_info?.label || row.model_id || "默认系统模型" }}
              </td>
              <td>{{ parseRawConfig(row.raw_config).activity_level }}</td>
              <td>{{ parseRawConfig(row.raw_config).expressiveness }}</td>
              <td class="time-cell">{{ formatDateTime(row.created_at) }}</td>
              <td class="actions-cell">
                <button class="secondary" @click="editRow(row)">编辑</button>
                <button class="warn" @click="removeRow(row)">删除</button>
              </td>
            </tr>
            <tr v-if="filteredRows.length === 0">
              <td colspan="10" style="text-align: center; opacity: 0.8">
                暂无数据
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.error-box {
  margin-bottom: 10px;
  border-color: #8d2f3b;
  color: #f4a7b5;
}

.success-box {
  margin-bottom: 10px;
  border-color: #1f6f4f;
  color: #91f0c7;
}

.form-error {
  margin: -6px 0 0;
  color: #ffb8b8;
  font-size: 12px;
}

.topic-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.topic-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 10px;
}

.topic-chip {
  border: 1px solid #36527f;
  border-radius: 999px;
  padding: 4px 10px;
  color: #cfe4ff;
  font-size: 12px;
  cursor: pointer;
}

.avatar-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.avatar-preview {
  width: 84px;
  height: 84px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #304666;
  background: #0a1323;
  flex: 0 0 auto;
}

.avatar-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-actions {
  flex: 1;
}

.avatar-file {
  display: none;
}

.preset-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.preset-btn,
.choice-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.preset-btn strong,
.choice-btn strong {
  font-size: 14px;
}

.preset-btn span,
.choice-btn span {
  color: #9fb3d6;
  font-size: 12px;
}

.choice-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.switch-row {
  align-items: center;
}

@media (max-width: 1200px) {
  .topic-grid,
  .preset-grid,
  .choice-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .topic-grid,
  .preset-grid,
  .choice-grid {
    grid-template-columns: 1fr;
  }

  .avatar-row {
    flex-direction: column;
  }
}
</style>
