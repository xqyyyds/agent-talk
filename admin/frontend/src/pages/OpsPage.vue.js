import { onMounted, onUnmounted, ref } from "vue";
import { api } from "../api";
const debateStatus = ref(null);
const output = ref("");
const cycleCount = ref(1);
const loading = ref(false);
const crawlerLoadingSource = ref(null);
const crawlerJobs = ref([]);
const selectedJobId = ref("");
const selectedJobLogs = ref([]);
const configSaving = ref(false);
const showOpenAIKey = ref(false);
const showTavilyKey = ref(false);
const runtimeConfig = ref({
    openai_api_base: "",
    openai_api_key: "",
    llm_model: "",
    llm_temperature: 0.7,
    tavily_api_key: "",
});
let crawlerPollTimer = null;
function normalizeError(err) {
    const detail = err?.response?.data?.detail;
    if (typeof detail === "string")
        return detail;
    if (detail && typeof detail === "object")
        return JSON.stringify(detail, null, 2);
    return err?.message || "请求失败";
}
function isRunningStatus(status) {
    return status === "queued" || status === "running";
}
function isSourceRunning(source) {
    return crawlerJobs.value.some((job) => job.source === source && isRunningStatus(job.status));
}
function startCrawlerPolling() {
    if (crawlerPollTimer !== null)
        return;
    crawlerPollTimer = window.setInterval(() => {
        void loadCrawlerJobs(true);
    }, 2000);
}
function stopCrawlerPolling() {
    if (crawlerPollTimer !== null) {
        window.clearInterval(crawlerPollTimer);
        crawlerPollTimer = null;
    }
}
function syncCrawlerPolling() {
    const hasRunningJob = crawlerJobs.value.some((job) => isRunningStatus(job.status));
    if (hasRunningJob) {
        startCrawlerPolling();
    }
    else {
        stopCrawlerPolling();
    }
}
async function runAction(action) {
    loading.value = true;
    try {
        const { data } = await action();
        output.value = JSON.stringify(data, null, 2);
        return data;
    }
    catch (err) {
        output.value = `执行失败:\n${normalizeError(err)}`;
        return null;
    }
    finally {
        loading.value = false;
    }
}
async function refreshDebateStatus() {
    await runAction(async () => {
        const { data } = await api.debateStatus();
        debateStatus.value = data;
        return data;
    });
}
async function startDebate() {
    await runAction(() => api.debateStart({
        cycle_count: cycleCount.value,
        resume: false,
    }));
    await refreshDebateStatus();
}
async function stopDebate() {
    await runAction(() => api.debateStop());
    await refreshDebateStatus();
}
async function loadCrawlerJobLogs(jobId) {
    try {
        const { data } = await api.getCrawlerJobLogs(jobId, 200);
        selectedJobLogs.value = data?.data?.logs || [];
    }
    catch (err) {
        selectedJobLogs.value = [`日志加载失败: ${normalizeError(err)}`];
    }
}
async function loadCrawlerJobs(silent = false) {
    try {
        const { data } = await api.listCrawlerJobs({ limit: 20 });
        crawlerJobs.value = data?.data?.jobs || [];
        if (!selectedJobId.value && crawlerJobs.value.length > 0) {
            selectedJobId.value = crawlerJobs.value[0].job_id;
        }
        if (selectedJobId.value) {
            await loadCrawlerJobLogs(selectedJobId.value);
        }
        syncCrawlerPolling();
    }
    catch (err) {
        if (!silent) {
            output.value = `拉取任务失败:\n${normalizeError(err)}`;
        }
    }
}
async function triggerCrawler(source) {
    crawlerLoadingSource.value = source;
    try {
        const { data } = await api.createCrawlerJob(source);
        output.value = JSON.stringify(data, null, 2);
        const newJobId = data?.data?.job?.job_id;
        if (newJobId) {
            selectedJobId.value = newJobId;
        }
        await loadCrawlerJobs(true);
    }
    catch (err) {
        output.value = `执行失败:\n${normalizeError(err)}`;
        await loadCrawlerJobs(true);
    }
    finally {
        crawlerLoadingSource.value = null;
    }
}
function selectJob(jobId) {
    selectedJobId.value = jobId;
    void loadCrawlerJobLogs(jobId);
}
function statusLabel(status) {
    const map = {
        queued: "排队中",
        running: "运行中",
        success: "成功",
        failed: "失败",
        timeout: "超时",
    };
    return map[status] || status;
}
async function loadRuntimeConfig() {
    await runAction(async () => {
        const { data } = await api.getRuntimeConfig();
        const cfg = data?.data || {};
        runtimeConfig.value = {
            openai_api_base: cfg.openai_api_base || "",
            openai_api_key: cfg.openai_api_key || "",
            llm_model: cfg.llm_model || "",
            llm_temperature: Number(cfg.llm_temperature ?? 0.7),
            tavily_api_key: cfg.tavily_api_key || "",
        };
        return data;
    });
}
async function saveRuntimeConfig() {
    configSaving.value = true;
    try {
        const payload = {
            openai_api_base: runtimeConfig.value.openai_api_base,
            openai_api_key: runtimeConfig.value.openai_api_key,
            llm_model: runtimeConfig.value.llm_model,
            llm_temperature: Number(runtimeConfig.value.llm_temperature),
            tavily_api_key: runtimeConfig.value.tavily_api_key,
        };
        const { data } = await api.updateRuntimeConfig(payload);
        output.value = JSON.stringify(data, null, 2);
    }
    catch (err) {
        output.value = `保存失败:\n${normalizeError(err)}`;
    }
    finally {
        configSaving.value = false;
    }
}
onMounted(async () => {
    await Promise.all([refreshDebateStatus(), loadRuntimeConfig(), loadCrawlerJobs()]);
});
onUnmounted(() => {
    stopCrawlerPolling();
});
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "grid" },
});
/** @type {__VLS_StyleScopedClasses['grid']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel col-6" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['col-6']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "1",
    max: "50",
    ...{ style: {} },
});
(__VLS_ctx.cycleCount);
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.startDebate) },
    ...{ class: "primary" },
    disabled: (__VLS_ctx.loading),
});
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.stopDebate) },
    ...{ class: "warn" },
    disabled: (__VLS_ctx.loading),
});
/** @type {__VLS_StyleScopedClasses['warn']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.refreshDebateStatus) },
    ...{ class: "secondary" },
    disabled: (__VLS_ctx.loading),
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.pre, __VLS_intrinsics.pre)({
    ...{ class: "panel-soft" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['panel-soft']} */ ;
(__VLS_ctx.debateStatus ? JSON.stringify(__VLS_ctx.debateStatus, null, 2) : "暂无状态");
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel col-6" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['col-6']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.triggerCrawler('zhihu');
            // @ts-ignore
            [cycleCount, startDebate, loading, loading, loading, stopDebate, refreshDebateStatus, debateStatus, debateStatus, triggerCrawler,];
        } },
    ...{ class: "primary" },
    disabled: (__VLS_ctx.crawlerLoadingSource !== null || __VLS_ctx.isSourceRunning('zhihu')),
});
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
(__VLS_ctx.isSourceRunning("zhihu")
    ? "知乎任务运行中"
    : __VLS_ctx.crawlerLoadingSource === "zhihu"
        ? "触发中..."
        : "触发知乎爬虫");
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.triggerCrawler('weibo');
            // @ts-ignore
            [triggerCrawler, crawlerLoadingSource, crawlerLoadingSource, isSourceRunning, isSourceRunning,];
        } },
    ...{ class: "secondary" },
    disabled: (__VLS_ctx.crawlerLoadingSource !== null || __VLS_ctx.isSourceRunning('weibo')),
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
(__VLS_ctx.isSourceRunning("weibo")
    ? "微博任务运行中"
    : __VLS_ctx.crawlerLoadingSource === "weibo"
        ? "触发中..."
        : "触发微博爬虫");
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.loadCrawlerJobs();
            // @ts-ignore
            [crawlerLoadingSource, crawlerLoadingSource, isSourceRunning, isSourceRunning, loadCrawlerJobs,];
        } },
    ...{ class: "secondary" },
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "form-note" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['form-note']} */ ;
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
__VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
for (const [job] of __VLS_vFor((__VLS_ctx.crawlerJobs))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
        key: (job.job_id),
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        ...{ class: "mono" },
    });
    /** @type {__VLS_StyleScopedClasses['mono']} */ ;
    (job.job_id.slice(0, 10));
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    (job.source);
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "badge" },
    });
    /** @type {__VLS_StyleScopedClasses['badge']} */ ;
    (__VLS_ctx.statusLabel(job.status));
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    (job.duration_seconds ?? "-");
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    (job.finished_at || "-");
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.selectJob(job.job_id);
                // @ts-ignore
                [crawlerJobs, statusLabel, selectJob,];
            } },
        ...{ class: "secondary" },
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
    // @ts-ignore
    [];
}
if (__VLS_ctx.crawlerJobs.length === 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        colspan: "6",
        ...{ style: {} },
    });
}
__VLS_asFunctionalElement1(__VLS_intrinsics.pre, __VLS_intrinsics.pre)({
    ...{ class: "panel-soft" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['panel-soft']} */ ;
(__VLS_ctx.selectedJobLogs.length ? __VLS_ctx.selectedJobLogs.join("\n") : "选择任务后可查看日志");
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel col-12" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['col-12']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-title" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stack" },
});
/** @type {__VLS_StyleScopedClasses['stack']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "https://api.example.com/v1",
});
(__VLS_ctx.runtimeConfig.openai_api_base);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "gpt-4o-mini",
});
(__VLS_ctx.runtimeConfig.llm_model);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "0",
    max: "2",
    step: "0.1",
    placeholder: "0.7",
});
(__VLS_ctx.runtimeConfig.llm_temperature);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: (__VLS_ctx.showOpenAIKey ? 'text' : 'password'),
    placeholder: "sk-...",
    ...{ style: {} },
});
(__VLS_ctx.runtimeConfig.openai_api_key);
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.showOpenAIKey = !__VLS_ctx.showOpenAIKey;
            // @ts-ignore
            [crawlerJobs, selectedJobLogs, selectedJobLogs, runtimeConfig, runtimeConfig, runtimeConfig, runtimeConfig, showOpenAIKey, showOpenAIKey, showOpenAIKey,];
        } },
    ...{ class: "secondary" },
    type: "button",
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
(__VLS_ctx.showOpenAIKey ? "隐藏" : "显示");
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: (__VLS_ctx.showTavilyKey ? 'text' : 'password'),
    placeholder: "tvly-...",
    ...{ style: {} },
});
(__VLS_ctx.runtimeConfig.tavily_api_key);
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.showTavilyKey = !__VLS_ctx.showTavilyKey;
            // @ts-ignore
            [runtimeConfig, showOpenAIKey, showTavilyKey, showTavilyKey, showTavilyKey,];
        } },
    ...{ class: "secondary" },
    type: "button",
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
(__VLS_ctx.showTavilyKey ? "隐藏" : "显示");
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.saveRuntimeConfig) },
    ...{ class: "primary" },
    disabled: (__VLS_ctx.configSaving),
});
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.loadRuntimeConfig) },
    ...{ class: "secondary" },
    disabled: (__VLS_ctx.loading),
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.pre, __VLS_intrinsics.pre)({
    ...{ class: "panel-soft" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['panel-soft']} */ ;
(__VLS_ctx.output || "执行结果会显示在这里");
// @ts-ignore
[loading, showTavilyKey, saveRuntimeConfig, configSaving, loadRuntimeConfig, output,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
