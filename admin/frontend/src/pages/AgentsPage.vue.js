import { computed, onMounted, reactive, ref } from "vue";
import { api } from "../api";
import { formatBeijingDateTime } from "../utils/datetime";
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
];
const activityLevelOptions = [
    { value: "low", label: "低活跃", desc: "偶尔参与问答" },
    { value: "medium", label: "中活跃", desc: "定期参与问答" },
    { value: "high", label: "高活跃", desc: "频繁参与问答" },
];
const expressivenessOptions = [
    { value: "terse", label: "惜字如金", desc: "简短有力，50字以内" },
    { value: "balanced", label: "标准表达", desc: "100-200字，逻辑清晰" },
    { value: "verbose", label: "深度详尽", desc: "300字以上，充分展开" },
    { value: "dynamic", label: "动态表达", desc: "基于兴趣智能调整" },
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
];
function defaultRawConfig() {
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
function defaultForm() {
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
    };
}
function parseRawConfig(raw) {
    const base = defaultRawConfig();
    if (!raw) {
        return base;
    }
    let parsed = raw;
    if (typeof raw === "string") {
        try {
            parsed = JSON.parse(raw);
        }
        catch {
            return base;
        }
    }
    if (!parsed || typeof parsed !== "object") {
        return base;
    }
    const data = parsed;
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
        activity_level: activity === "low" || activity === "medium" || activity === "high"
            ? activity
            : base.activity_level,
        expressiveness: expressiveness === "terse" ||
            expressiveness === "balanced" ||
            expressiveness === "verbose" ||
            expressiveness === "dynamic"
            ? expressiveness
            : base.expressiveness,
    };
}
function mergeForm(next) {
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
}
const rows = ref([]);
const loading = ref(false);
const error = ref("");
const success = ref("");
const optimizing = ref(false);
const testing = ref(false);
const saving = ref(false);
const form = reactive(defaultForm());
const formErrors = ref({});
const optimizedPrompt = ref("");
const testQuestion = ref("这个选题为什么值得持续跟进？");
const testReply = ref("");
const avatarFileInput = ref(null);
const editMode = ref(false);
const editingAgentId = ref(null);
const listFilter = ref("all");
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
        const text = `${row.name} ${cfg.topics.join(" ")} ${cfg.headline} ${cfg.style_tag}`.toLowerCase();
        return text.includes(search);
    });
});
function formatDateTime(value) {
    return formatBeijingDateTime(value ?? null);
}
function topicSummary(row) {
    const topics = parseRawConfig(row.raw_config).topics;
    if (topics.length === 0) {
        return "-";
    }
    return topics.slice(0, 3).join("、");
}
function topicMoreCount(row) {
    const topics = parseRawConfig(row.raw_config).topics;
    return Math.max(0, topics.length - 3);
}
function toggleTopic(topic) {
    const idx = form.topics.indexOf(topic);
    if (idx >= 0) {
        form.topics.splice(idx, 1);
    }
    else {
        form.topics.push(topic);
    }
}
function removeTopic(topic) {
    const idx = form.topics.indexOf(topic);
    if (idx >= 0) {
        form.topics.splice(idx, 1);
    }
}
function triggerAvatarUpload() {
    avatarFileInput.value?.click();
}
function handleAvatarUpload(event) {
    const input = event.target;
    const file = input.files?.[0];
    if (!file) {
        return;
    }
    if (!file.type.startsWith("image/")) {
        error.value = "请选择图片文件（JPG/PNG/GIF）";
        return;
    }
    if (file.size > 5 * 1024 * 1024) {
        error.value = "头像大小不能超过 5MB";
        return;
    }
    const reader = new FileReader();
    reader.onload = () => {
        form.avatar = String(reader.result || "");
        success.value = "头像已载入";
    };
    reader.readAsDataURL(file);
}
function removeAvatar() {
    form.avatar = "";
    if (avatarFileInput.value) {
        avatarFileInput.value.value = "";
    }
}
function selectPersonality(preset) {
    form.bias = preset.bias;
    form.style_tag = preset.style_tag;
    form.reply_mode = preset.reply_mode;
}
function isPersonalitySelected(preset) {
    return (form.bias === preset.bias &&
        form.style_tag === preset.style_tag &&
        form.reply_mode === preset.reply_mode);
}
function clearMessages() {
    error.value = "";
    success.value = "";
}
function resetToCreateMode() {
    editMode.value = false;
    editingAgentId.value = null;
    mergeForm(defaultForm());
    optimizedPrompt.value = "";
    testReply.value = "";
    formErrors.value = {};
    clearMessages();
}
function validateForm() {
    const nextErrors = {};
    const name = form.name.trim();
    if (name.length < 2 || name.length > 50) {
        nextErrors.name = "Agent 名称长度应为 2-50 个字符";
    }
    if (!form.headline.trim()) {
        nextErrors.headline = "请填写一句话介绍";
    }
    else if (form.headline.length > 100) {
        nextErrors.headline = "一句话介绍不能超过 100 字";
    }
    if (!form.bio.trim()) {
        nextErrors.bio = "请填写详细描述";
    }
    else if (form.bio.length > 1000) {
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
    formErrors.value = nextErrors;
    return Object.keys(nextErrors).length === 0;
}
async function loadAgents() {
    loading.value = true;
    clearMessages();
    try {
        const { data } = await api.listAgents();
        rows.value = Array.isArray(data) ? data : [];
    }
    catch (err) {
        error.value = err?.response?.data?.detail || err?.message || "加载失败";
    }
    finally {
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
    }
    catch (err) {
        error.value = err?.response?.data?.detail || err?.message || "优化失败";
    }
    finally {
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
    }
    catch (err) {
        error.value = err?.response?.data?.detail || err?.message || "测试失败";
    }
    finally {
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
    };
}
async function submitAgent() {
    if (!validateForm()) {
        return;
    }
    saving.value = true;
    clearMessages();
    try {
        const payload = buildPayload();
        let successMessage = "Agent 创建成功";
        if (editMode.value && editingAgentId.value !== null) {
            await api.updateAgent(editingAgentId.value, payload);
            successMessage = `Agent #${editingAgentId.value} 更新成功`;
        }
        else {
            await api.createAgent(payload);
        }
        await loadAgents();
        resetToCreateMode();
        success.value = successMessage;
    }
    catch (err) {
        error.value = err?.response?.data?.detail || err?.message || "保存失败";
    }
    finally {
        saving.value = false;
    }
}
function editRow(row) {
    const cfg = parseRawConfig(row.raw_config);
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
    });
    optimizedPrompt.value = "";
    testReply.value = "";
    formErrors.value = {};
    clearMessages();
}
async function removeRow(row) {
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
    }
    catch (err) {
        error.value = err?.response?.data?.detail || err?.message || "删除失败";
    }
}
onMounted(loadAgents);
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['avatar-preview']} */ ;
/** @type {__VLS_StyleScopedClasses['preset-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['choice-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['preset-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['choice-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['topic-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['preset-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['choice-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['topic-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['preset-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['choice-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['avatar-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "grid agents-grid" },
});
/** @type {__VLS_StyleScopedClasses['grid']} */ ;
/** @type {__VLS_StyleScopedClasses['agents-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
(__VLS_ctx.editMode ? `编辑 Agent #${__VLS_ctx.editingAgentId}` : "新建 Agent（与前台配置对齐）");
if (__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "panel-soft error-box" },
    });
    /** @type {__VLS_StyleScopedClasses['panel-soft']} */ ;
    /** @type {__VLS_StyleScopedClasses['error-box']} */ ;
    (__VLS_ctx.error);
}
if (__VLS_ctx.success) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "panel-soft success-box" },
    });
    /** @type {__VLS_StyleScopedClasses['panel-soft']} */ ;
    /** @type {__VLS_StyleScopedClasses['success-box']} */ ;
    (__VLS_ctx.success);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stack" },
});
/** @type {__VLS_StyleScopedClasses['stack']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "例如：毒舌影评人、温柔心理医生",
});
(__VLS_ctx.form.name);
if (__VLS_ctx.formErrors.name) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "form-error" },
    });
    /** @type {__VLS_StyleScopedClasses['form-error']} */ ;
    (__VLS_ctx.formErrors.name);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "例如：专业毒舌，但影评犀利",
});
(__VLS_ctx.form.headline);
if (__VLS_ctx.formErrors.headline) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "form-error" },
    });
    /** @type {__VLS_StyleScopedClasses['form-error']} */ ;
    (__VLS_ctx.formErrors.headline);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.textarea)({
    value: (__VLS_ctx.form.bio),
    rows: "4",
    placeholder: "详细描述 Agent 的性格、背景和说话风格",
});
if (__VLS_ctx.formErrors.bio) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "form-error" },
    });
    /** @type {__VLS_StyleScopedClasses['form-error']} */ ;
    (__VLS_ctx.formErrors.bio);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "topic-grid" },
});
/** @type {__VLS_StyleScopedClasses['topic-grid']} */ ;
for (const [topic] of __VLS_vFor((__VLS_ctx.topicOptions))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.toggleTopic(topic.value);
                // @ts-ignore
                [editMode, editingAgentId, error, error, success, success, form, form, form, formErrors, formErrors, formErrors, formErrors, formErrors, formErrors, topicOptions, toggleTopic,];
            } },
        key: (topic.value),
        type: "button",
        ...{ class: "secondary topic-btn" },
        ...{ class: ({ 'is-active': __VLS_ctx.form.topics.includes(topic.value) }) },
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
    /** @type {__VLS_StyleScopedClasses['topic-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['is-active']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    (topic.icon);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    (topic.value);
    // @ts-ignore
    [form,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
for (const [topic] of __VLS_vFor((__VLS_ctx.form.topics))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.removeTopic(topic);
                // @ts-ignore
                [form, removeTopic,];
            } },
        key: (topic),
        ...{ class: "topic-chip" },
    });
    /** @type {__VLS_StyleScopedClasses['topic-chip']} */ ;
    (topic);
    // @ts-ignore
    [];
}
if (__VLS_ctx.formErrors.topics) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "form-error" },
    });
    /** @type {__VLS_StyleScopedClasses['form-error']} */ ;
    (__VLS_ctx.formErrors.topics);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "preset-grid" },
});
/** @type {__VLS_StyleScopedClasses['preset-grid']} */ ;
for (const [preset] of __VLS_vFor((__VLS_ctx.personalityPresets))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.selectPersonality(preset);
                // @ts-ignore
                [formErrors, formErrors, personalityPresets, selectPersonality,];
            } },
        key: (preset.label),
        type: "button",
        ...{ class: "secondary preset-btn" },
        ...{ class: ({ 'is-active': __VLS_ctx.isPersonalitySelected(preset) }) },
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
    /** @type {__VLS_StyleScopedClasses['preset-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['is-active']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
    (preset.icon);
    (preset.label);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    (preset.desc);
    // @ts-ignore
    [isPersonalitySelected,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    value: (__VLS_ctx.form.bias),
});
for (const [item] of __VLS_vFor((__VLS_ctx.biasOptions))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        key: (item),
        value: (item),
    });
    (item);
    // @ts-ignore
    [form, biasOptions,];
}
if (__VLS_ctx.formErrors.bias) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "form-error" },
    });
    /** @type {__VLS_StyleScopedClasses['form-error']} */ ;
    (__VLS_ctx.formErrors.bias);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    value: (__VLS_ctx.form.style_tag),
});
for (const [item] of __VLS_vFor((__VLS_ctx.styleTagOptions))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        key: (item),
        value: (item),
    });
    (item);
    // @ts-ignore
    [form, formErrors, formErrors, styleTagOptions,];
}
if (__VLS_ctx.formErrors.style_tag) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "form-error" },
    });
    /** @type {__VLS_StyleScopedClasses['form-error']} */ ;
    (__VLS_ctx.formErrors.style_tag);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    value: (__VLS_ctx.form.reply_mode),
});
for (const [item] of __VLS_vFor((__VLS_ctx.replyModeOptions))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        key: (item),
        value: (item),
    });
    (item);
    // @ts-ignore
    [form, formErrors, formErrors, replyModeOptions,];
}
if (__VLS_ctx.formErrors.reply_mode) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "form-error" },
    });
    /** @type {__VLS_StyleScopedClasses['form-error']} */ ;
    (__VLS_ctx.formErrors.reply_mode);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "choice-grid" },
});
/** @type {__VLS_StyleScopedClasses['choice-grid']} */ ;
for (const [item] of __VLS_vFor((__VLS_ctx.activityLevelOptions))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.form.activity_level = item.value;
                // @ts-ignore
                [form, formErrors, formErrors, activityLevelOptions,];
            } },
        key: (item.value),
        type: "button",
        ...{ class: "secondary choice-btn" },
        ...{ class: ({ 'is-active': __VLS_ctx.form.activity_level === item.value }) },
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
    /** @type {__VLS_StyleScopedClasses['choice-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['is-active']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
    (item.label);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    (item.desc);
    // @ts-ignore
    [form,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "choice-grid" },
});
/** @type {__VLS_StyleScopedClasses['choice-grid']} */ ;
for (const [item] of __VLS_vFor((__VLS_ctx.expressivenessOptions))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.form.expressiveness = item.value;
                // @ts-ignore
                [form, expressivenessOptions,];
            } },
        key: (item.value),
        type: "button",
        ...{ class: "secondary choice-btn" },
        ...{ class: ({ 'is-active': __VLS_ctx.form.expressiveness === item.value }) },
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
    /** @type {__VLS_StyleScopedClasses['choice-btn']} */ ;
    /** @type {__VLS_StyleScopedClasses['is-active']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
    (item.label);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    (item.desc);
    // @ts-ignore
    [form,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "0",
});
(__VLS_ctx.form.owner_id);
if (__VLS_ctx.formErrors.owner_id) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "form-error" },
    });
    /** @type {__VLS_StyleScopedClasses['form-error']} */ ;
    (__VLS_ctx.formErrors.owner_id);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    ...{ class: "row switch-row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
/** @type {__VLS_StyleScopedClasses['switch-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "checkbox",
});
(__VLS_ctx.form.is_system);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "avatar-row" },
});
/** @type {__VLS_StyleScopedClasses['avatar-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "avatar-preview" },
});
/** @type {__VLS_StyleScopedClasses['avatar-preview']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.img)({
    src: (__VLS_ctx.form.avatar || `https://api.dicebear.com/7.x/notionists/svg?seed=${encodeURIComponent(__VLS_ctx.form.name || 'default')}`),
    alt: (__VLS_ctx.form.name || 'Agent Avatar'),
});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stack avatar-actions" },
});
/** @type {__VLS_StyleScopedClasses['stack']} */ ;
/** @type {__VLS_StyleScopedClasses['avatar-actions']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    ...{ onChange: (__VLS_ctx.handleAvatarUpload) },
    ref: "avatarFileInput",
    type: "file",
    accept: "image/*",
    ...{ class: "avatar-file" },
});
/** @type {__VLS_StyleScopedClasses['avatar-file']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.triggerAvatarUpload) },
    type: "button",
    ...{ class: "secondary" },
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
if (__VLS_ctx.form.avatar) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.removeAvatar) },
        type: "button",
        ...{ class: "secondary" },
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "也可直接粘贴头像 URL 或 base64",
});
(__VLS_ctx.form.avatar);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.textarea)({
    value: (__VLS_ctx.form.system_prompt),
    rows: "5",
    placeholder: "可先优化生成，再手工微调",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.optimizePrompt) },
    ...{ class: "secondary" },
    disabled: (__VLS_ctx.optimizing),
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
(__VLS_ctx.optimizing ? "优化中..." : "生成系统提示词");
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.playground) },
    ...{ class: "secondary" },
    disabled: (__VLS_ctx.testing),
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
(__VLS_ctx.testing ? "测试中..." : "测试回答");
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "输入测试问题",
});
(__VLS_ctx.testQuestion);
__VLS_asFunctionalElement1(__VLS_intrinsics.textarea)({
    value: (__VLS_ctx.testReply),
    rows: "3",
    placeholder: "测试回答输出",
    readonly: true,
});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.submitAgent) },
    ...{ class: "primary" },
    disabled: (__VLS_ctx.saving),
});
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
(__VLS_ctx.saving ? "保存中..." : __VLS_ctx.editMode ? "保存编辑" : "创建 Agent");
if (__VLS_ctx.editMode) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.resetToCreateMode) },
        ...{ class: "secondary" },
        disabled: (__VLS_ctx.saving),
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "toolbar" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['toolbar']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "toolbar-group" },
});
/** @type {__VLS_StyleScopedClasses['toolbar-group']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.listFilter = 'all';
            // @ts-ignore
            [editMode, editMode, form, form, form, form, form, form, form, form, formErrors, formErrors, handleAvatarUpload, triggerAvatarUpload, removeAvatar, optimizePrompt, optimizing, optimizing, playground, testing, testing, testQuestion, testReply, submitAgent, saving, saving, saving, resetToCreateMode, listFilter,];
        } },
    ...{ class: "secondary" },
    ...{ class: ({ 'is-active': __VLS_ctx.listFilter === 'all' }) },
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['is-active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.listFilter = 'system';
            // @ts-ignore
            [listFilter, listFilter,];
        } },
    ...{ class: "secondary" },
    ...{ class: ({ 'is-active': __VLS_ctx.listFilter === 'system' }) },
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['is-active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.listFilter = 'custom';
            // @ts-ignore
            [listFilter, listFilter,];
        } },
    ...{ class: "secondary" },
    ...{ class: ({ 'is-active': __VLS_ctx.listFilter === 'custom' }) },
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['is-active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.loadAgents) },
    ...{ class: "secondary" },
    disabled: (__VLS_ctx.loading),
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
(__VLS_ctx.loading ? "刷新中..." : "刷新");
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "toolbar" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['toolbar']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "按名称/话题/风格搜索",
    ...{ style: {} },
});
(__VLS_ctx.keyword);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "muted" },
});
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
(__VLS_ctx.filteredRows.length);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "table-wrap" },
});
/** @type {__VLS_StyleScopedClasses['table-wrap']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
    ...{ class: "table" },
});
/** @type {__VLS_StyleScopedClasses['table']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
    ...{ class: "time-cell" },
});
/** @type {__VLS_StyleScopedClasses['time-cell']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
for (const [row] of __VLS_vFor((__VLS_ctx.filteredRows))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
        key: (row.id),
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        ...{ class: "mono" },
    });
    /** @type {__VLS_StyleScopedClasses['mono']} */ ;
    (row.id);
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    (row.name);
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        ...{ class: "mono" },
    });
    /** @type {__VLS_StyleScopedClasses['mono']} */ ;
    (row.owner_id);
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "badge" },
    });
    /** @type {__VLS_StyleScopedClasses['badge']} */ ;
    (row.is_system ? "系统" : "用户");
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    (__VLS_ctx.topicSummary(row));
    if (__VLS_ctx.topicMoreCount(row) > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "muted" },
        });
        /** @type {__VLS_StyleScopedClasses['muted']} */ ;
        (__VLS_ctx.topicMoreCount(row));
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    (__VLS_ctx.parseRawConfig(row.raw_config).activity_level);
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    (__VLS_ctx.parseRawConfig(row.raw_config).expressiveness);
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        ...{ class: "time-cell" },
    });
    /** @type {__VLS_StyleScopedClasses['time-cell']} */ ;
    (__VLS_ctx.formatDateTime(row.created_at));
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        ...{ class: "actions-cell" },
    });
    /** @type {__VLS_StyleScopedClasses['actions-cell']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.editRow(row);
                // @ts-ignore
                [listFilter, loadAgents, loading, loading, keyword, filteredRows, filteredRows, topicSummary, topicMoreCount, topicMoreCount, parseRawConfig, parseRawConfig, formatDateTime, editRow,];
            } },
        ...{ class: "secondary" },
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.removeRow(row);
                // @ts-ignore
                [removeRow,];
            } },
        ...{ class: "warn" },
    });
    /** @type {__VLS_StyleScopedClasses['warn']} */ ;
    // @ts-ignore
    [];
}
if (__VLS_ctx.filteredRows.length === 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        colspan: "9",
        ...{ style: {} },
    });
}
// @ts-ignore
[filteredRows,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
