import * as echarts from "echarts";
import { nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { api } from "../api";
const overview = ref(null);
const charts = ref(null);
const days = ref(7);
const loading = ref(false);
const error = ref("");
const onlinePoints = ref([]);
const userTrendEl = ref(null);
const onlineTrendEl = ref(null);
const contentTrendEl = ref(null);
const rolePieEl = ref(null);
let userTrendChart = null;
let onlineTrendChart = null;
let contentTrendChart = null;
let rolePieChart = null;
let pollingTimer = null;
function formatError(err) {
    const detail = err?.response?.data?.detail;
    if (typeof detail === "string") {
        return detail;
    }
    if (detail && typeof detail === "object") {
        return JSON.stringify(detail, null, 2);
    }
    return err?.message || "加载失败";
}
function trimOnlinePoints(max = 24) {
    if (onlinePoints.value.length > max) {
        onlinePoints.value = onlinePoints.value.slice(-max);
    }
}
function pushOnlinePoint(value) {
    const now = new Date();
    const label = now.toLocaleTimeString("zh-CN", { hour12: false });
    onlinePoints.value.push({ label, value });
    trimOnlinePoints();
}
function ensureCharts() {
    if (userTrendEl.value && !userTrendChart) {
        userTrendChart = echarts.init(userTrendEl.value);
    }
    if (onlineTrendEl.value && !onlineTrendChart) {
        onlineTrendChart = echarts.init(onlineTrendEl.value);
    }
    if (contentTrendEl.value && !contentTrendChart) {
        contentTrendChart = echarts.init(contentTrendEl.value);
    }
    if (rolePieEl.value && !rolePieChart) {
        rolePieChart = echarts.init(rolePieEl.value);
    }
}
function renderUserTrendChart() {
    if (!charts.value || !userTrendChart)
        return;
    userTrendChart.setOption({
        tooltip: { trigger: "axis" },
        legend: { data: ["总用户", "总Agent"], textStyle: { color: "#cde6ff" } },
        grid: { left: 36, right: 20, top: 40, bottom: 30 },
        xAxis: {
            type: "category",
            data: charts.value.labels,
            axisLabel: { color: "#8fa1c6" },
            axisLine: { lineStyle: { color: "#314364" } },
        },
        yAxis: {
            type: "value",
            axisLabel: { color: "#8fa1c6" },
            splitLine: { lineStyle: { color: "#263652" } },
        },
        series: [
            {
                name: "总用户",
                type: "line",
                smooth: true,
                data: charts.value.total_users_trend,
                lineStyle: { width: 3, color: "#48d3ff" },
                areaStyle: { color: "rgba(72,211,255,0.16)" },
            },
            {
                name: "总Agent",
                type: "line",
                smooth: true,
                data: charts.value.total_agents_trend,
                lineStyle: { width: 3, color: "#80ffbf" },
                areaStyle: { color: "rgba(128,255,191,0.12)" },
            },
        ],
    });
}
function renderOnlineTrendChart() {
    if (!onlineTrendChart)
        return;
    onlineTrendChart.setOption({
        tooltip: { trigger: "axis" },
        grid: { left: 36, right: 20, top: 24, bottom: 30 },
        xAxis: {
            type: "category",
            data: onlinePoints.value.map((p) => p.label),
            axisLabel: { color: "#8fa1c6" },
            axisLine: { lineStyle: { color: "#314364" } },
        },
        yAxis: {
            type: "value",
            minInterval: 1,
            axisLabel: { color: "#8fa1c6" },
            splitLine: { lineStyle: { color: "#263652" } },
        },
        series: [
            {
                name: "在线用户",
                type: "line",
                smooth: true,
                data: onlinePoints.value.map((p) => p.value),
                lineStyle: { width: 3, color: "#66a8ff" },
                areaStyle: { color: "rgba(102,168,255,0.15)" },
            },
        ],
    });
}
function renderContentTrendChart() {
    if (!charts.value || !contentTrendChart)
        return;
    contentTrendChart.setOption({
        tooltip: { trigger: "axis" },
        legend: { data: ["问题", "回答"], textStyle: { color: "#cde6ff" } },
        grid: { left: 36, right: 20, top: 40, bottom: 30 },
        xAxis: {
            type: "category",
            data: charts.value.labels,
            axisLabel: { color: "#8fa1c6" },
            axisLine: { lineStyle: { color: "#314364" } },
        },
        yAxis: {
            type: "value",
            minInterval: 1,
            axisLabel: { color: "#8fa1c6" },
            splitLine: { lineStyle: { color: "#263652" } },
        },
        series: [
            {
                name: "问题",
                type: "bar",
                data: charts.value.content_questions_trend,
                itemStyle: { color: "#48d3ff" },
            },
            {
                name: "回答",
                type: "bar",
                data: charts.value.content_answers_trend,
                itemStyle: { color: "#80ffbf" },
            },
        ],
    });
}
function renderRolePieChart() {
    if (!charts.value || !rolePieChart)
        return;
    rolePieChart.setOption({
        tooltip: { trigger: "item" },
        legend: { bottom: 0, textStyle: { color: "#cde6ff" } },
        series: [
            {
                name: "角色占比",
                type: "pie",
                radius: ["36%", "66%"],
                center: ["50%", "42%"],
                data: [
                    { value: charts.value.role_distribution.user, name: "User" },
                    { value: charts.value.role_distribution.agent, name: "Agent" },
                    { value: charts.value.role_distribution.admin, name: "Admin" },
                ],
                label: { color: "#d8e9ff" },
            },
        ],
    });
}
function renderAllCharts() {
    renderUserTrendChart();
    renderOnlineTrendChart();
    renderContentTrendChart();
    renderRolePieChart();
}
function resizeCharts() {
    userTrendChart?.resize();
    onlineTrendChart?.resize();
    contentTrendChart?.resize();
    rolePieChart?.resize();
}
async function loadOverview() {
    const { data } = await api.overview();
    overview.value = data;
    pushOnlinePoint(Number(data.online_users_5m ?? 0));
}
async function loadCharts() {
    const { data } = await api.dashboardCharts(days.value);
    charts.value = data;
}
async function loadDashboardData() {
    loading.value = true;
    error.value = "";
    try {
        await Promise.all([loadOverview(), loadCharts()]);
        await nextTick();
        ensureCharts();
        renderAllCharts();
    }
    catch (err) {
        error.value = formatError(err);
    }
    finally {
        loading.value = false;
    }
}
async function pollOverview() {
    try {
        await loadOverview();
        renderOnlineTrendChart();
    }
    catch {
        // Keep dashboard running even if one poll fails.
    }
}
function startPolling() {
    if (pollingTimer !== null)
        return;
    pollingTimer = window.setInterval(() => {
        void pollOverview();
    }, 5000);
}
function stopPolling() {
    if (pollingTimer !== null) {
        window.clearInterval(pollingTimer);
        pollingTimer = null;
    }
}
watch(days, async () => {
    try {
        await loadCharts();
        renderUserTrendChart();
        renderContentTrendChart();
        renderRolePieChart();
    }
    catch (err) {
        error.value = formatError(err);
    }
});
onMounted(async () => {
    await loadDashboardData();
    startPolling();
    window.addEventListener("resize", resizeCharts);
});
onUnmounted(() => {
    stopPolling();
    window.removeEventListener("resize", resizeCharts);
    userTrendChart?.dispose();
    onlineTrendChart?.dispose();
    contentTrendChart?.dispose();
    rolePieChart?.dispose();
    userTrendChart = null;
    onlineTrendChart = null;
    contentTrendChart = null;
    rolePieChart = null;
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
    ...{ class: "panel col-3" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['col-3']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "kpi-value" },
});
/** @type {__VLS_StyleScopedClasses['kpi-value']} */ ;
(__VLS_ctx.overview?.total_users ?? "-");
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "muted" },
});
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
(__VLS_ctx.overview?.today_users ?? "-");
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel col-3" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['col-3']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "kpi-value" },
});
/** @type {__VLS_StyleScopedClasses['kpi-value']} */ ;
(__VLS_ctx.overview?.total_agents ?? "-");
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "muted" },
});
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel col-3" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['col-3']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "kpi-value" },
});
/** @type {__VLS_StyleScopedClasses['kpi-value']} */ ;
(__VLS_ctx.overview?.online_users_5m ?? "-");
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "muted" },
});
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
(__VLS_ctx.overview?.online_window_seconds ?? 300);
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel col-3" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['col-3']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "kpi-value" },
});
/** @type {__VLS_StyleScopedClasses['kpi-value']} */ ;
(__VLS_ctx.overview?.active_users_24h ?? "-");
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "muted" },
});
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
if (__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "panel col-12 panel-soft" },
        ...{ style: {} },
    });
    /** @type {__VLS_StyleScopedClasses['panel']} */ ;
    /** @type {__VLS_StyleScopedClasses['col-12']} */ ;
    /** @type {__VLS_StyleScopedClasses['panel-soft']} */ ;
    (__VLS_ctx.error);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel col-12" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['col-12']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "toolbar" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['toolbar']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-title" },
    ...{ style: {} },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "toolbar-group" },
});
/** @type {__VLS_StyleScopedClasses['toolbar-group']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.days = 7;
            // @ts-ignore
            [overview, overview, overview, overview, overview, overview, error, error, days,];
        } },
    ...{ class: "secondary" },
    ...{ class: ({ 'is-active': __VLS_ctx.days === 7 }) },
    disabled: (__VLS_ctx.loading),
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['is-active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.days = 30;
            // @ts-ignore
            [days, days, loading,];
        } },
    ...{ class: "secondary" },
    ...{ class: ({ 'is-active': __VLS_ctx.days === 30 }) },
    disabled: (__VLS_ctx.loading),
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['is-active']} */ ;
if (__VLS_ctx.loading) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "muted" },
    });
    /** @type {__VLS_StyleScopedClasses['muted']} */ ;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "dashboard-charts-grid" },
    });
    /** @type {__VLS_StyleScopedClasses['dashboard-charts-grid']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "panel-soft" },
    });
    /** @type {__VLS_StyleScopedClasses['panel-soft']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "section-title" },
    });
    /** @type {__VLS_StyleScopedClasses['section-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ref: "userTrendEl",
        ...{ class: "chart-canvas" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-canvas']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "panel-soft" },
    });
    /** @type {__VLS_StyleScopedClasses['panel-soft']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "section-title" },
    });
    /** @type {__VLS_StyleScopedClasses['section-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ref: "onlineTrendEl",
        ...{ class: "chart-canvas" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-canvas']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "panel-soft" },
    });
    /** @type {__VLS_StyleScopedClasses['panel-soft']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "section-title" },
    });
    /** @type {__VLS_StyleScopedClasses['section-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ref: "contentTrendEl",
        ...{ class: "chart-canvas" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-canvas']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "panel-soft" },
    });
    /** @type {__VLS_StyleScopedClasses['panel-soft']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "section-title" },
    });
    /** @type {__VLS_StyleScopedClasses['section-title']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ref: "rolePieEl",
        ...{ class: "chart-canvas" },
    });
    /** @type {__VLS_StyleScopedClasses['chart-canvas']} */ ;
}
// @ts-ignore
[days, loading, loading,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
