import { computed, onMounted, ref } from "vue";
import { api } from "../api";
import { formatBeijingDateTime } from "../utils/datetime";
const loading = ref(false);
const error = ref("");
const kindFilter = ref("all");
const ackFilter = ref("pending");
const alerts = ref([]);
const filteredAlerts = computed(() => alerts.value.filter((item) => {
    const kindOk = kindFilter.value === "all" || (item.kind || "failover") === kindFilter.value;
    const ackOk = ackFilter.value === "all" ||
        (ackFilter.value === "pending" ? !item.acknowledged : !!item.acknowledged);
    return kindOk && ackOk;
}));
const pendingCount = computed(() => alerts.value.filter((item) => !item.acknowledged).length);
function normalizeError(err) {
    const detail = err?.response?.data?.detail;
    if (typeof detail === "string")
        return detail;
    if (detail && typeof detail === "object")
        return JSON.stringify(detail, null, 2);
    return err?.message || "请求失败";
}
function kindLabel(kind) {
    return (kind || "failover") === "generation_failure" ? "生成失败" : "模型回退";
}
function kindClass(kind) {
    return (kind || "failover") === "generation_failure" ? "badge-danger" : "badge-warn";
}
async function loadAlerts() {
    loading.value = true;
    error.value = "";
    try {
        const { data } = await api.getLlmAlerts(200);
        alerts.value = data?.data?.items || [];
    }
    catch (err) {
        error.value = normalizeError(err);
    }
    finally {
        loading.value = false;
    }
}
async function ackOne(id) {
    try {
        await api.ackLlmAlerts([id]);
        await loadAlerts();
    }
    catch (err) {
        error.value = normalizeError(err);
    }
}
async function ackAllPending() {
    const ids = alerts.value.filter((item) => !item.acknowledged).map((item) => item.id);
    if (ids.length === 0)
        return;
    try {
        await api.ackLlmAlerts(ids);
        await loadAlerts();
    }
    catch (err) {
        error.value = normalizeError(err);
    }
}
onMounted(loadAlerts);
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['field-inline']} */ ;
/** @type {__VLS_StyleScopedClasses['field-inline']} */ ;
/** @type {__VLS_StyleScopedClasses['alert-grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stack" },
});
/** @type {__VLS_StyleScopedClasses['stack']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "toolbar" },
});
/** @type {__VLS_StyleScopedClasses['toolbar']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "muted" },
});
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.loadAlerts) },
    ...{ class: "secondary" },
    disabled: (__VLS_ctx.loading),
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
(__VLS_ctx.loading ? "刷新中..." : "刷新告警");
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.ackAllPending) },
    ...{ class: "primary" },
    disabled: (__VLS_ctx.pendingCount === 0),
});
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
(__VLS_ctx.pendingCount);
if (__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "panel-soft error-box" },
    });
    /** @type {__VLS_StyleScopedClasses['panel-soft']} */ ;
    /** @type {__VLS_StyleScopedClasses['error-box']} */ ;
    (__VLS_ctx.error);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "grid" },
});
/** @type {__VLS_StyleScopedClasses['grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel col-12" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['col-12']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row wrap-gap" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
/** @type {__VLS_StyleScopedClasses['wrap-gap']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    ...{ class: "field-inline" },
});
/** @type {__VLS_StyleScopedClasses['field-inline']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    value: (__VLS_ctx.kindFilter),
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "all",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "failover",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "generation_failure",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
    ...{ class: "field-inline" },
});
/** @type {__VLS_StyleScopedClasses['field-inline']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    value: (__VLS_ctx.ackFilter),
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "pending",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "acked",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "all",
});
if (__VLS_ctx.filteredAlerts.length === 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "panel-soft" },
    });
    /** @type {__VLS_StyleScopedClasses['panel-soft']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "stack" },
    });
    /** @type {__VLS_StyleScopedClasses['stack']} */ ;
    for (const [item] of __VLS_vFor((__VLS_ctx.filteredAlerts))) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.article, __VLS_intrinsics.article)({
            key: (item.id),
            ...{ class: "panel-soft alert-card" },
        });
        /** @type {__VLS_StyleScopedClasses['panel-soft']} */ ;
        /** @type {__VLS_StyleScopedClasses['alert-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "toolbar alert-card-head" },
        });
        /** @type {__VLS_StyleScopedClasses['toolbar']} */ ;
        /** @type {__VLS_StyleScopedClasses['alert-card-head']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "row wrap-gap" },
        });
        /** @type {__VLS_StyleScopedClasses['row']} */ ;
        /** @type {__VLS_StyleScopedClasses['wrap-gap']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "badge" },
            ...{ class: (__VLS_ctx.kindClass(item.kind)) },
        });
        /** @type {__VLS_StyleScopedClasses['badge']} */ ;
        (__VLS_ctx.kindLabel(item.kind));
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "muted mono" },
        });
        /** @type {__VLS_StyleScopedClasses['muted']} */ ;
        /** @type {__VLS_StyleScopedClasses['mono']} */ ;
        (item.scene);
        if (item.agent_username) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "muted" },
            });
            /** @type {__VLS_StyleScopedClasses['muted']} */ ;
            (item.agent_username);
        }
        if (item.effective_model) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "muted" },
            });
            /** @type {__VLS_StyleScopedClasses['muted']} */ ;
            (item.effective_model);
        }
        if (item.attempts) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "muted" },
            });
            /** @type {__VLS_StyleScopedClasses['muted']} */ ;
            (item.attempts);
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "row" },
        });
        /** @type {__VLS_StyleScopedClasses['row']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "muted" },
        });
        /** @type {__VLS_StyleScopedClasses['muted']} */ ;
        (__VLS_ctx.formatBeijingDateTime(item.at));
        if (!item.acknowledged) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                ...{ onClick: (...[$event]) => {
                        if (!!(__VLS_ctx.filteredAlerts.length === 0))
                            return;
                        if (!(!item.acknowledged))
                            return;
                        __VLS_ctx.ackOne(item.id);
                        // @ts-ignore
                        [loadAlerts, loading, loading, ackAllPending, pendingCount, pendingCount, error, error, kindFilter, ackFilter, filteredAlerts, filteredAlerts, kindClass, kindLabel, formatBeijingDateTime, ackOne,];
                    } },
                ...{ class: "secondary" },
            });
            /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "badge badge-off" },
            });
            /** @type {__VLS_StyleScopedClasses['badge']} */ ;
            /** @type {__VLS_StyleScopedClasses['badge-off']} */ ;
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "stack" },
        });
        /** @type {__VLS_StyleScopedClasses['stack']} */ ;
        if (item.message) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "alert-message" },
            });
            /** @type {__VLS_StyleScopedClasses['alert-message']} */ ;
            (item.message);
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "alert-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['alert-grid']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "mono" },
        });
        /** @type {__VLS_StyleScopedClasses['mono']} */ ;
        (item.primary_model || "-");
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "mono" },
        });
        /** @type {__VLS_StyleScopedClasses['mono']} */ ;
        (item.secondary_model || "-");
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
        (item.fallback_succeeded ? "已成功回退" : "未回退/已放弃");
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "label" },
        });
        /** @type {__VLS_StyleScopedClasses['label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.pre, __VLS_intrinsics.pre)({
            ...{ class: "error-pre" },
        });
        /** @type {__VLS_StyleScopedClasses['error-pre']} */ ;
        (item.primary_error || "-");
        if (item.secondary_error) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "label" },
            });
            /** @type {__VLS_StyleScopedClasses['label']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.pre, __VLS_intrinsics.pre)({
                ...{ class: "error-pre" },
            });
            /** @type {__VLS_StyleScopedClasses['error-pre']} */ ;
            (item.secondary_error);
        }
        // @ts-ignore
        [];
    }
}
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
