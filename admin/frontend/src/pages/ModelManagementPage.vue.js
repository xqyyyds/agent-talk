import { computed, onMounted, reactive, ref } from "vue";
import { api } from "../api";
function defaultForm() {
    return {
        id: "",
        label: "",
        provider_type: "openai_compatible",
        base_url: "",
        api_key: "",
        model: "",
        enabled: true,
        is_default: false,
        sort_order: 0,
    };
}
const loading = ref(false);
const saving = ref(false);
const error = ref("");
const success = ref("");
const revealApiKey = ref(false);
const editingId = ref("");
const catalog = ref([]);
const defaultModelId = ref("");
const form = reactive(defaultForm());
const legacySummary = computed(() => {
    if (catalog.value.length === 0)
        return "当前尚未发现系统模型目录，仍可能由 legacy 主备配置兜底生成。";
    return "当前系统优先使用模型目录；Ops 页中的 single / dual_fallback 配置仅作为兼容来源展示。";
});
function clearMessages() {
    error.value = "";
    success.value = "";
}
function resetForm() {
    Object.assign(form, defaultForm());
    editingId.value = "";
    revealApiKey.value = false;
}
function normalizeCatalogPayload(data) {
    const payload = data?.data ?? data ?? {};
    catalog.value = Array.isArray(payload.models) ? payload.models : [];
    defaultModelId.value = String(payload.default_model_id || "");
}
async function loadCatalog() {
    loading.value = true;
    clearMessages();
    try {
        const { data } = await api.getModelCatalog();
        normalizeCatalogPayload(data);
    }
    catch (err) {
        error.value = err?.response?.data?.detail || err?.message || "加载模型目录失败";
    }
    finally {
        loading.value = false;
    }
}
function editItem(item) {
    editingId.value = item.id;
    Object.assign(form, {
        id: item.id,
        label: item.label,
        provider_type: item.provider_type || "openai_compatible",
        base_url: item.base_url,
        api_key: item.api_key,
        model: item.model,
        enabled: item.enabled,
        is_default: item.is_default,
        sort_order: Number(item.sort_order || 0),
    });
    clearMessages();
}
function validateForm() {
    if (!form.id.trim())
        return "请填写稳定 ID";
    if (!form.label.trim())
        return "请填写展示名称";
    if (!form.base_url.trim())
        return "请填写 Base URL";
    if (!form.model.trim())
        return "请填写模型名";
    if (!editingId.value && !form.api_key.trim())
        return "新建系统模型时请填写 API Key";
    return null;
}
async function submitForm() {
    const invalid = validateForm();
    if (invalid) {
        error.value = invalid;
        return;
    }
    saving.value = true;
    clearMessages();
    try {
        const payload = {
            id: form.id.trim(),
            label: form.label.trim(),
            provider_type: form.provider_type.trim() || "openai_compatible",
            base_url: form.base_url.trim(),
            api_key: form.api_key.trim(),
            model: form.model.trim(),
            enabled: form.enabled,
            is_default: form.is_default,
            sort_order: Number(form.sort_order || 0),
        };
        const { data } = editingId.value
            ? await api.updateModelCatalogItem(editingId.value, payload)
            : await api.createModelCatalogItem(payload);
        normalizeCatalogPayload(data);
        success.value = editingId.value ? `模型 ${editingId.value} 更新成功` : "模型创建成功";
        resetForm();
    }
    catch (err) {
        error.value = err?.response?.data?.detail || err?.message || "保存失败";
    }
    finally {
        saving.value = false;
    }
}
async function setDefault(item) {
    clearMessages();
    try {
        const { data } = await api.setDefaultModelCatalogItem(item.id);
        normalizeCatalogPayload(data);
        success.value = `默认模型已切换为 ${item.label}`;
    }
    catch (err) {
        error.value = err?.response?.data?.detail || err?.message || "设置默认模型失败";
    }
}
async function toggleEnabled(item) {
    clearMessages();
    try {
        const { data } = item.enabled
            ? await api.disableModelCatalogItem(item.id)
            : await api.enableModelCatalogItem(item.id);
        normalizeCatalogPayload(data);
        success.value = item.enabled ? `已禁用 ${item.label}` : `已启用 ${item.label}`;
    }
    catch (err) {
        error.value = err?.response?.data?.detail || err?.message || "更新模型状态失败";
    }
}
async function moveItem(item, direction) {
    const currentIndex = catalog.value.findIndex((entry) => entry.id === item.id);
    if (currentIndex < 0)
        return;
    const targetIndex = currentIndex + direction;
    if (targetIndex < 0 || targetIndex >= catalog.value.length)
        return;
    const next = [...catalog.value];
    const [moved] = next.splice(currentIndex, 1);
    next.splice(targetIndex, 0, moved);
    try {
        const { data } = await api.reorderModelCatalog(next.map((entry) => entry.id));
        normalizeCatalogPayload(data);
        success.value = `已调整 ${item.label} 的展示顺序`;
    }
    catch (err) {
        error.value = err?.response?.data?.detail || err?.message || "调整顺序失败";
    }
}
onMounted(loadCatalog);
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['single-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "grid" },
});
/** @type {__VLS_StyleScopedClasses['grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel col-5" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['col-5']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "toolbar" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['toolbar']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.resetForm) },
    ...{ class: "secondary" },
    disabled: (__VLS_ctx.saving),
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
(__VLS_ctx.editingId ? "切换到新建" : "重置表单");
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
    disabled: (Boolean(__VLS_ctx.editingId)),
    placeholder: "例如：system-glm-4_6",
});
(__VLS_ctx.form.id);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "例如：glm-4.6",
});
(__VLS_ctx.form.label);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "https://api.example.com/v1",
    autocomplete: "off",
});
(__VLS_ctx.form.base_url);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "glm-4.6 / gpt-4o-mini",
    autocomplete: "off",
});
(__VLS_ctx.form.model);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: (__VLS_ctx.revealApiKey ? 'text' : 'password'),
    ...{ style: {} },
    placeholder: (__VLS_ctx.editingId ? '留空表示沿用当前密钥' : 'sk-...'),
    autocomplete: "new-password",
});
(__VLS_ctx.form.api_key);
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.revealApiKey = !__VLS_ctx.revealApiKey;
            // @ts-ignore
            [resetForm, saving, editingId, editingId, editingId, error, error, success, success, form, form, form, form, form, revealApiKey, revealApiKey, revealApiKey,];
        } },
    ...{ class: "secondary" },
    type: "button",
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
(__VLS_ctx.revealApiKey ? "隐藏" : "显示");
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "choice-grid single-row" },
});
/** @type {__VLS_StyleScopedClasses['choice-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['single-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    ...{ class: "row switch-row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
/** @type {__VLS_StyleScopedClasses['switch-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "checkbox",
});
(__VLS_ctx.form.enabled);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    ...{ class: "row switch-row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
/** @type {__VLS_StyleScopedClasses['switch-row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "checkbox",
});
(__VLS_ctx.form.is_default);
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "0",
    step: "1",
});
(__VLS_ctx.form.sort_order);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.submitForm) },
    ...{ class: "primary" },
    disabled: (__VLS_ctx.saving),
});
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
(__VLS_ctx.saving ? "保存中..." : __VLS_ctx.editingId ? "保存模型" : "新增模型");
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.loadCatalog) },
    ...{ class: "secondary" },
    disabled: (__VLS_ctx.loading),
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
(__VLS_ctx.loading ? "刷新中..." : "刷新目录");
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel col-7" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['col-7']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "toolbar" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['toolbar']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "muted" },
});
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
(__VLS_ctx.defaultModelId || "-");
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel-soft" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['panel-soft']} */ ;
(__VLS_ctx.legacySummary);
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
__VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
for (const [item, index] of __VLS_vFor((__VLS_ctx.catalog))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
        key: (item.id),
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        ...{ class: "mono" },
    });
    /** @type {__VLS_StyleScopedClasses['mono']} */ ;
    (item.id);
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    (item.label);
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    (item.model);
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        ...{ class: "mono url-cell" },
    });
    /** @type {__VLS_StyleScopedClasses['mono']} */ ;
    /** @type {__VLS_StyleScopedClasses['url-cell']} */ ;
    (item.base_url);
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "badge" },
        ...{ class: ({ 'badge-off': !item.enabled }) },
    });
    /** @type {__VLS_StyleScopedClasses['badge']} */ ;
    /** @type {__VLS_StyleScopedClasses['badge-off']} */ ;
    (item.enabled ? "启用" : "禁用");
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    (item.is_default ? "是" : "-");
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    (item.sort_order);
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        ...{ class: "actions-cell" },
    });
    /** @type {__VLS_StyleScopedClasses['actions-cell']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.editItem(item);
                // @ts-ignore
                [saving, saving, editingId, form, form, form, revealApiKey, submitForm, loadCatalog, loading, loading, defaultModelId, legacySummary, catalog, editItem,];
            } },
        ...{ class: "secondary" },
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.moveItem(item, -1);
                // @ts-ignore
                [moveItem,];
            } },
        ...{ class: "secondary" },
        disabled: (index === 0),
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.moveItem(item, 1);
                // @ts-ignore
                [moveItem,];
            } },
        ...{ class: "secondary" },
        disabled: (index === __VLS_ctx.catalog.length - 1),
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.setDefault(item);
                // @ts-ignore
                [catalog, setDefault,];
            } },
        ...{ class: "secondary" },
        disabled: (item.is_default || !item.enabled),
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.toggleEnabled(item);
                // @ts-ignore
                [toggleEnabled,];
            } },
        ...{ class: "warn" },
    });
    /** @type {__VLS_StyleScopedClasses['warn']} */ ;
    (item.enabled ? "禁用" : "启用");
    // @ts-ignore
    [];
}
if (__VLS_ctx.catalog.length === 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        colspan: "8",
        ...{ style: {} },
    });
}
// @ts-ignore
[catalog,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
