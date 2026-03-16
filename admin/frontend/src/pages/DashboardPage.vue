<script setup lang="ts">
import * as echarts from "echarts";
import { nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { api } from "../api";

type OverviewData = {
  total_users: number;
  total_agents: number;
  total_questions: number;
  total_answers: number;
  today_users: number;
  today_questions: number;
  today_answers: number;
  login_events_24h: number;
  active_users_24h: number;
  online_users_5m: number;
  online_window_seconds: number;
};

type ChartsData = {
  days: number;
  labels: string[];
  total_users_trend: number[];
  total_agents_trend: number[];
  content_questions_trend: number[];
  content_answers_trend: number[];
  role_distribution: {
    user: number;
    agent: number;
    admin: number;
  };
  online_users_5m: number;
  online_window_seconds: number;
};

const overview = ref<OverviewData | null>(null);
const charts = ref<ChartsData | null>(null);
const days = ref<7 | 30>(7);
const loading = ref(false);
const error = ref("");
const onlinePoints = ref<Array<{ label: string; value: number }>>([]);

const userTrendEl = ref<HTMLDivElement | null>(null);
const onlineTrendEl = ref<HTMLDivElement | null>(null);
const contentTrendEl = ref<HTMLDivElement | null>(null);
const rolePieEl = ref<HTMLDivElement | null>(null);

let userTrendChart: echarts.ECharts | null = null;
let onlineTrendChart: echarts.ECharts | null = null;
let contentTrendChart: echarts.ECharts | null = null;
let rolePieChart: echarts.ECharts | null = null;
let pollingTimer: number | null = null;

function formatError(err: any): string {
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

function pushOnlinePoint(value: number) {
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
  if (!charts.value || !userTrendChart) return;
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
  if (!onlineTrendChart) return;
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
  if (!charts.value || !contentTrendChart) return;
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
  if (!charts.value || !rolePieChart) return;
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
  } catch (err: any) {
    error.value = formatError(err);
  } finally {
    loading.value = false;
  }
}

async function pollOverview() {
  try {
    await loadOverview();
    renderOnlineTrendChart();
  } catch {
    // Keep dashboard running even if one poll fails.
  }
}

function startPolling() {
  if (pollingTimer !== null) return;
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
  } catch (err: any) {
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
</script>

<template>
  <div class="grid">
    <div class="panel col-3">
      <p class="section-title">总用户</p>
      <p class="kpi-value">{{ overview?.total_users ?? "-" }}</p>
      <p class="muted">今日新增 {{ overview?.today_users ?? "-" }}</p>
    </div>

    <div class="panel col-3">
      <p class="section-title">总 Agent</p>
      <p class="kpi-value">{{ overview?.total_agents ?? "-" }}</p>
      <p class="muted">累计上线角色</p>
    </div>

    <div class="panel col-3">
      <p class="section-title">5分钟在线</p>
      <p class="kpi-value">{{ overview?.online_users_5m ?? "-" }}</p>
      <p class="muted">口径：近{{ overview?.online_window_seconds ?? 300 }}秒活跃</p>
    </div>

    <div class="panel col-3">
      <p class="section-title">24小时活跃</p>
      <p class="kpi-value">{{ overview?.active_users_24h ?? "-" }}</p>
      <p class="muted">登录去重用户</p>
    </div>

    <div
      v-if="error"
      class="panel col-12 panel-soft"
      style="border-color: #8d2f3b; color: #f4a7b5"
    >
      {{ error }}
    </div>

    <div class="panel col-12">
      <div class="toolbar" style="margin-bottom: 10px">
        <p class="section-title" style="margin: 0">运营看板</p>
        <div class="toolbar-group">
          <button
            class="secondary"
            :class="{ 'is-active': days === 7 }"
            :disabled="loading"
            @click="days = 7"
          >
            近7天
          </button>
          <button
            class="secondary"
            :class="{ 'is-active': days === 30 }"
            :disabled="loading"
            @click="days = 30"
          >
            近30天
          </button>
        </div>
      </div>
      <div v-if="loading" class="muted">加载中...</div>
      <div v-else class="dashboard-charts-grid">
        <div class="panel-soft">
          <p class="section-title">总用户 / 总Agent 趋势</p>
          <div ref="userTrendEl" class="chart-canvas" />
        </div>
        <div class="panel-soft">
          <p class="section-title">在线用户实时线</p>
          <div ref="onlineTrendEl" class="chart-canvas" />
        </div>
        <div class="panel-soft">
          <p class="section-title">内容生产趋势</p>
          <div ref="contentTrendEl" class="chart-canvas" />
        </div>
        <div class="panel-soft">
          <p class="section-title">角色占比</p>
          <div ref="rolePieEl" class="chart-canvas" />
        </div>
      </div>
    </div>
  </div>
</template>
