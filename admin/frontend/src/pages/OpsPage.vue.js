import { onMounted, onUnmounted, reactive, ref } from "vue";
import { api } from "../api";
import { formatBeijingDateTime } from "../utils/datetime";
const loading = ref(false);
const output = ref("");
const debateStatus = ref(null);
const cycleCount = ref(1);
const crawlerLoadingSource = ref(null);
const crawlerJobs = ref([]);
const selectedJobId = ref("");
const selectedJobLogs = ref([]);
const notifiedFailedJobs = new Set();
const configSaving = ref(false);
const showOpenAIKey = ref(false);
const showSecondaryOpenAIKey = ref(false);
const showTavilyKey = ref(false);
const llmAlertsLoading = ref(false);
const llmAlerts = ref([]);
const runtimeConfig = reactive({
    llm_failover_mode: "single",
    openai_api_base: "",
    openai_api_key: "",
    llm_model: "",
    llm_temperature: 0.7,
    openai_api_base_secondary: "",
    openai_api_key_secondary: "",
    llm_model_secondary: "",
    llm_temperature_secondary: 0.7,
    tavily_api_key: "",
    zhihu_cookie: "",
    weibo_cookie: "",
});
const qaPolicy = reactive({
    enabled: true,
    target_daily_hotspots: 480,
    dispatch_min_seconds: 10,
    dispatch_max_seconds: 180,
    jitter_min: 0.85,
    jitter_max: 1.15,
    max_parallelism: 2,
    ewma_alpha: 0.25,
});
const debatePolicy = reactive({
    enabled: true,
    daily_target_min: 10,
    daily_target_max: 15,
    interval_min_minutes: 45,
    interval_max_minutes: 180,
    jitter_min: 0.85,
    jitter_max: 1.15,
    new_agent_auto_join: true,
});
const schedulerPolicy = reactive({
    auto_crawler_enabled: true,
    auto_crawler_interval_minutes: 120,
    sources: ["zhihu", "weibo"],
});
const realtimePolicy = reactive({
    sse_enabled: true,
    fallback_poll_seconds: 5,
});
const capacitySnapshot = ref(null);
const policySaving = ref(false);
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
function syncCrawlerPolling() {
    const hasRunningJob = crawlerJobs.value.some((job) => isRunningStatus(job.status));
    if (hasRunningJob && crawlerPollTimer === null) {
        crawlerPollTimer = window.setInterval(() => {
            void loadCrawlerJobs(true);
        }, 2000);
    }
    if (!hasRunningJob && crawlerPollTimer !== null) {
        window.clearInterval(crawlerPollTimer);
        crawlerPollTimer = null;
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
        selectedJobLogs.value = [`日志加载失败：${normalizeError(err)}`];
    }
}
function checkCrawlerFailures() {
    for (const job of crawlerJobs.value) {
        if ((job.status === "failed" || job.status === "timeout") && !notifiedFailedJobs.has(job.job_id)) {
            notifiedFailedJobs.add(job.job_id);
            const reason = job.error_message || "crawler failed";
            window.alert(`${job.source === "zhihu" ? "知乎" : "微博"} 爬虫任务失败（${statusLabel(job.status)}）。\n原因：${reason}\n请在后台更新 Cookie 后重试。`);
        }
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
        checkCrawlerFailures();
        syncCrawlerPolling();
    }
    catch (err) {
        if (!silent) {
            output.value = `加载爬虫任务失败:\n${normalizeError(err)}`;
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
function formatDateTime(value) {
    return formatBeijingDateTime(value ?? null);
}
async function loadRuntimeConfig() {
    await runAction(async () => {
        const { data } = await api.getRuntimeConfig();
        const cfg = data?.data || {};
        runtimeConfig.llm_failover_mode = cfg.llm_failover_mode || "single";
        runtimeConfig.openai_api_base = cfg.openai_api_base || "";
        runtimeConfig.openai_api_key = cfg.openai_api_key || "";
        runtimeConfig.llm_model = cfg.llm_model || "";
        runtimeConfig.llm_temperature = Number(cfg.llm_temperature ?? 0.7);
        runtimeConfig.openai_api_base_secondary = cfg.openai_api_base_secondary || "";
        runtimeConfig.openai_api_key_secondary = cfg.openai_api_key_secondary || "";
        runtimeConfig.llm_model_secondary = cfg.llm_model_secondary || "";
        runtimeConfig.llm_temperature_secondary = Number(cfg.llm_temperature_secondary ?? 0.7);
        runtimeConfig.tavily_api_key = cfg.tavily_api_key || "";
        runtimeConfig.zhihu_cookie = cfg.zhihu_cookie || "";
        runtimeConfig.weibo_cookie = cfg.weibo_cookie || "";
        return data;
    });
}
async function saveRuntimeConfig() {
    configSaving.value = true;
    try {
        const trim = (value) => value.trim();
        const payload = {
            llm_failover_mode: trim(runtimeConfig.llm_failover_mode).toLowerCase(),
            openai_api_base: trim(runtimeConfig.openai_api_base),
            openai_api_key: trim(runtimeConfig.openai_api_key),
            llm_model: trim(runtimeConfig.llm_model),
            llm_temperature: Number(runtimeConfig.llm_temperature),
            openai_api_base_secondary: trim(runtimeConfig.openai_api_base_secondary),
            openai_api_key_secondary: trim(runtimeConfig.openai_api_key_secondary),
            llm_model_secondary: trim(runtimeConfig.llm_model_secondary),
            llm_temperature_secondary: Number(runtimeConfig.llm_temperature_secondary),
            tavily_api_key: trim(runtimeConfig.tavily_api_key),
            zhihu_cookie: runtimeConfig.zhihu_cookie,
            weibo_cookie: runtimeConfig.weibo_cookie,
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
async function loadLlmAlerts() {
    llmAlertsLoading.value = true;
    try {
        const { data } = await api.getLlmAlerts(100);
        llmAlerts.value = data?.data?.items || [];
    }
    catch (err) {
        output.value = `加载 LLM 告警失败:\n${normalizeError(err)}`;
    }
    finally {
        llmAlertsLoading.value = false;
    }
}
async function ackLlmAlert(id) {
    try {
        await api.ackLlmAlerts([id]);
        await loadLlmAlerts();
    }
    catch (err) {
        output.value = `确认告警失败:\n${normalizeError(err)}`;
    }
}
async function loadPolicies() {
    try {
        const [qaRes, debateRes, schedulerRes, realtimeRes, capacityRes] = await Promise.all([
            api.getQaPolicy(),
            api.getDebatePolicy(),
            api.getSchedulerPolicy(),
            api.getRealtimePolicy(),
            api.getRuntimeCapacity(),
        ]);
        Object.assign(qaPolicy, qaRes.data?.data || {});
        Object.assign(debatePolicy, debateRes.data?.data || {});
        Object.assign(schedulerPolicy, schedulerRes.data?.data || {});
        Object.assign(realtimePolicy, realtimeRes.data?.data || {});
        capacitySnapshot.value = capacityRes.data?.data || null;
    }
    catch (err) {
        output.value = `加载策略失败:\n${normalizeError(err)}`;
    }
}
async function saveQaPolicy() {
    policySaving.value = true;
    try {
        await api.updateQaPolicy({ ...qaPolicy });
        await loadPolicies();
        output.value = "问答策略已更新";
    }
    catch (err) {
        output.value = `保存问答策略失败:\n${normalizeError(err)}`;
    }
    finally {
        policySaving.value = false;
    }
}
async function saveDebatePolicy() {
    policySaving.value = true;
    try {
        await api.updateDebatePolicy({ ...debatePolicy });
        await loadPolicies();
        output.value = "辩论策略已更新";
    }
    catch (err) {
        output.value = `保存辩论策略失败:\n${normalizeError(err)}`;
    }
    finally {
        policySaving.value = false;
    }
}
async function saveSchedulerPolicy() {
    policySaving.value = true;
    try {
        await api.updateSchedulerPolicy({ ...schedulerPolicy });
        await loadPolicies();
        output.value = "调度策略已更新";
    }
    catch (err) {
        output.value = `保存调度策略失败:\n${normalizeError(err)}`;
    }
    finally {
        policySaving.value = false;
    }
}
async function saveRealtimePolicy() {
    policySaving.value = true;
    try {
        await api.updateRealtimePolicy({ ...realtimePolicy });
        await loadPolicies();
        output.value = "实时策略已更新";
    }
    catch (err) {
        output.value = `保存实时策略失败:\n${normalizeError(err)}`;
    }
    finally {
        policySaving.value = false;
    }
}
onMounted(async () => {
    await Promise.all([
        refreshDebateStatus(),
        loadRuntimeConfig(),
        loadLlmAlerts(),
        loadCrawlerJobs(),
        loadPolicies(),
    ]);
});
onUnmounted(() => {
    if (crawlerPollTimer !== null) {
        window.clearInterval(crawlerPollTimer);
        crawlerPollTimer = null;
    }
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
(__VLS_ctx.isSourceRunning("zhihu") ? "知乎运行中" : __VLS_ctx.crawlerLoadingSource === "zhihu" ? "启动中..." : "运行知乎爬虫");
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
(__VLS_ctx.isSourceRunning("weibo") ? "微博运行中" : __VLS_ctx.crawlerLoadingSource === "weibo" ? "启动中..." : "运行微博爬虫");
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
    ...{ class: "stack" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['stack']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.textarea)({
    value: (__VLS_ctx.runtimeConfig.zhihu_cookie),
    rows: "3",
    placeholder: "粘贴完整知乎 Cookie，保存后立即生效",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.textarea)({
    value: (__VLS_ctx.runtimeConfig.weibo_cookie),
    rows: "3",
    placeholder: "粘贴完整微博 Cookie，保存后立即生效",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.saveRuntimeConfig) },
    ...{ class: "primary" },
    disabled: (__VLS_ctx.configSaving),
});
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
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
    (__VLS_ctx.formatDateTime(job.finished_at));
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.selectJob(job.job_id);
                // @ts-ignore
                [runtimeConfig, runtimeConfig, saveRuntimeConfig, configSaving, crawlerJobs, statusLabel, formatDateTime, selectJob,];
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
(__VLS_ctx.selectedJobLogs.length ? __VLS_ctx.selectedJobLogs.join("\n") : "请选择任务查看日志");
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
    ...{ class: "stack" },
});
/** @type {__VLS_StyleScopedClasses['stack']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "checkbox",
});
(__VLS_ctx.qaPolicy.enabled);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "1",
    max: "5000",
});
(__VLS_ctx.qaPolicy.target_daily_hotspots);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "1",
    max: "600",
});
(__VLS_ctx.qaPolicy.dispatch_min_seconds);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "1",
    max: "1800",
});
(__VLS_ctx.qaPolicy.dispatch_max_seconds);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "0.5",
    max: "1",
    step: "0.01",
});
(__VLS_ctx.qaPolicy.jitter_min);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "1",
    max: "2",
    step: "0.01",
});
(__VLS_ctx.qaPolicy.jitter_max);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "1",
    max: "8",
});
(__VLS_ctx.qaPolicy.max_parallelism);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "0.05",
    max: "0.95",
    step: "0.01",
});
(__VLS_ctx.qaPolicy.ewma_alpha);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.saveQaPolicy) },
    ...{ class: "primary" },
    disabled: (__VLS_ctx.policySaving),
});
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
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
    ...{ class: "stack" },
});
/** @type {__VLS_StyleScopedClasses['stack']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "checkbox",
});
(__VLS_ctx.debatePolicy.enabled);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "1",
    max: "100",
});
(__VLS_ctx.debatePolicy.daily_target_min);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "1",
    max: "200",
});
(__VLS_ctx.debatePolicy.daily_target_max);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "1",
    max: "1440",
});
(__VLS_ctx.debatePolicy.interval_min_minutes);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "1",
    max: "1440",
});
(__VLS_ctx.debatePolicy.interval_max_minutes);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "0.5",
    max: "1",
    step: "0.01",
});
(__VLS_ctx.debatePolicy.jitter_min);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "1",
    max: "2",
    step: "0.01",
});
(__VLS_ctx.debatePolicy.jitter_max);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "checkbox",
});
(__VLS_ctx.debatePolicy.new_agent_auto_join);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.saveDebatePolicy) },
    ...{ class: "primary" },
    disabled: (__VLS_ctx.policySaving),
});
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
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
    ...{ class: "stack" },
});
/** @type {__VLS_StyleScopedClasses['stack']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "checkbox",
});
(__VLS_ctx.schedulerPolicy.auto_crawler_enabled);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "10",
    max: "1440",
});
(__VLS_ctx.schedulerPolicy.auto_crawler_interval_minutes);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "checkbox",
    value: "zhihu",
});
(__VLS_ctx.schedulerPolicy.sources);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "checkbox",
    value: "weibo",
});
(__VLS_ctx.schedulerPolicy.sources);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.saveSchedulerPolicy) },
    ...{ class: "primary" },
    disabled: (__VLS_ctx.policySaving),
});
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
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
    ...{ class: "stack" },
});
/** @type {__VLS_StyleScopedClasses['stack']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "checkbox",
});
(__VLS_ctx.realtimePolicy.sse_enabled);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "1",
    max: "120",
});
(__VLS_ctx.realtimePolicy.fallback_poll_seconds);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "row" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['row']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.saveRealtimePolicy) },
    ...{ class: "primary" },
    disabled: (__VLS_ctx.policySaving),
});
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel col-12" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['col-12']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "stack" },
});
/** @type {__VLS_StyleScopedClasses['stack']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    value: (__VLS_ctx.runtimeConfig.llm_failover_mode),
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "single",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
    value: "dual_fallback",
});
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "https://api.example.com/v1",
});
(__VLS_ctx.runtimeConfig.openai_api_base);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    placeholder: "gpt-5-mini",
});
(__VLS_ctx.runtimeConfig.llm_model);
__VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.input)({
    type: "number",
    min: "0",
    max: "2",
    step: "0.1",
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
            [runtimeConfig, runtimeConfig, runtimeConfig, runtimeConfig, runtimeConfig, crawlerJobs, selectedJobLogs, selectedJobLogs, qaPolicy, qaPolicy, qaPolicy, qaPolicy, qaPolicy, qaPolicy, qaPolicy, qaPolicy, saveQaPolicy, policySaving, policySaving, policySaving, policySaving, debatePolicy, debatePolicy, debatePolicy, debatePolicy, debatePolicy, debatePolicy, debatePolicy, debatePolicy, saveDebatePolicy, schedulerPolicy, schedulerPolicy, schedulerPolicy, schedulerPolicy, saveSchedulerPolicy, realtimePolicy, realtimePolicy, saveRealtimePolicy, showOpenAIKey, showOpenAIKey, showOpenAIKey,];
        } },
    ...{ class: "secondary" },
    type: "button",
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
(__VLS_ctx.showOpenAIKey ? "隐藏" : "显示");
if (__VLS_ctx.runtimeConfig.llm_failover_mode === 'dual_fallback') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        placeholder: "https://api.example.com/v1",
    });
    (__VLS_ctx.runtimeConfig.openai_api_base_secondary);
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        placeholder: "gpt-5-mini",
    });
    (__VLS_ctx.runtimeConfig.llm_model_secondary);
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: "number",
        min: "0",
        max: "2",
        step: "0.1",
    });
    (__VLS_ctx.runtimeConfig.llm_temperature_secondary);
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "row" },
        ...{ style: {} },
    });
    /** @type {__VLS_StyleScopedClasses['row']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        type: (__VLS_ctx.showSecondaryOpenAIKey ? 'text' : 'password'),
        placeholder: "sk-...",
        ...{ style: {} },
    });
    (__VLS_ctx.runtimeConfig.openai_api_key_secondary);
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.runtimeConfig.llm_failover_mode === 'dual_fallback'))
                    return;
                __VLS_ctx.showSecondaryOpenAIKey = !__VLS_ctx.showSecondaryOpenAIKey;
                // @ts-ignore
                [runtimeConfig, runtimeConfig, runtimeConfig, runtimeConfig, runtimeConfig, showOpenAIKey, showSecondaryOpenAIKey, showSecondaryOpenAIKey, showSecondaryOpenAIKey,];
            } },
        ...{ class: "secondary" },
        type: "button",
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
    (__VLS_ctx.showSecondaryOpenAIKey ? "隐藏" : "显示");
}
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
            [runtimeConfig, showSecondaryOpenAIKey, showTavilyKey, showTavilyKey, showTavilyKey,];
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
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel col-12" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['col-12']} */ ;
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
    ...{ onClick: (__VLS_ctx.loadLlmAlerts) },
    ...{ class: "secondary" },
    disabled: (__VLS_ctx.llmAlertsLoading),
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
(__VLS_ctx.llmAlertsLoading ? "加载中..." : "刷新告警");
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
__VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
for (const [alert] of __VLS_vFor((__VLS_ctx.llmAlerts))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
        key: (alert.id),
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    (__VLS_ctx.formatDateTime(alert.at));
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    (alert.scene);
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    (alert.primary_model);
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    (alert.secondary_model || "-");
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    (alert.fallback_succeeded ? "成功" : "失败");
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        ...{ class: "mono" },
    });
    /** @type {__VLS_StyleScopedClasses['mono']} */ ;
    (alert.primary_error);
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.ackLlmAlert(alert.id);
                // @ts-ignore
                [loading, saveRuntimeConfig, configSaving, formatDateTime, showTavilyKey, loadRuntimeConfig, loadLlmAlerts, llmAlertsLoading, llmAlertsLoading, llmAlerts, ackLlmAlert,];
            } },
        ...{ class: "secondary" },
        disabled: (!!alert.acknowledged),
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
    (alert.acknowledged ? "已确认" : "确认");
    // @ts-ignore
    [];
}
if (__VLS_ctx.llmAlerts.length === 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        colspan: "7",
        ...{ style: {} },
    });
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel col-12" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['col-12']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.pre, __VLS_intrinsics.pre)({
    ...{ class: "panel-soft" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['panel-soft']} */ ;
(__VLS_ctx.capacitySnapshot ? JSON.stringify(__VLS_ctx.capacitySnapshot, null, 2) : "暂无容量数据");
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel col-12" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['col-12']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.pre, __VLS_intrinsics.pre)({
    ...{ class: "panel-soft" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['panel-soft']} */ ;
(__VLS_ctx.output || "操作输出将显示在这里");
// @ts-ignore
[llmAlerts, capacitySnapshot, capacitySnapshot, output,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
