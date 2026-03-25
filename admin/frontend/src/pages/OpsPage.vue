<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";
import { api } from "../api";
import { formatBeijingDateTime } from "../utils/datetime";

type CrawlerSource = "zhihu" | "weibo";
type CrawlerStatus = "queued" | "running" | "success" | "failed" | "timeout";

type CrawlerJob = {
  job_id: string;
  source: CrawlerSource;
  script_name: string;
  status: CrawlerStatus | string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  exit_code: number | null;
  error_message: string;
};

type CrawlerFailureAlert = {
  job_id: string;
  source: CrawlerSource;
  status: string;
  reason: string;
};

const CRAWLER_FAILURE_ALERT_ACK_KEY = "agenttalk:ops:crawler-failure-alert-acks";

const loading = ref(false);
const output = ref("");

const debateStatus = ref<any>(null);
const cycleCount = ref(1);

const crawlerLoadingSource = ref<CrawlerSource | null>(null);
const crawlerJobs = ref<CrawlerJob[]>([]);
const selectedJobId = ref("");
const selectedJobLogs = ref<string[]>([]);
const crawlerFailureAlerts = ref<CrawlerFailureAlert[]>([]);
const acknowledgedFailedJobs = new Set<string>();

const configSaving = ref(false);
const showOpenAIKey = ref(false);
const showSecondaryOpenAIKey = ref(false);
const showTavilyKey = ref(false);

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
  crawler_job_timeout_seconds: 1800,
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
  sources: ["zhihu", "weibo"] as CrawlerSource[],
});

const realtimePolicy = reactive({
  sse_enabled: true,
  fallback_poll_seconds: 5,
});

const capacitySnapshot = ref<any>(null);
const policySaving = ref(false);

let crawlerPollTimer: number | null = null;

function normalizeError(err: any): string {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") return JSON.stringify(detail, null, 2);
  return err?.message || "请求失败";
}

function isRunningStatus(status: string): boolean {
  return status === "queued" || status === "running";
}

function isSourceRunning(source: CrawlerSource): boolean {
  return crawlerJobs.value.some(
    (job) => job.source === source && isRunningStatus(job.status),
  );
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

function loadAcknowledgedFailedJobs() {
  try {
    const raw = localStorage.getItem(CRAWLER_FAILURE_ALERT_ACK_KEY);
    if (!raw) return;
    const items = JSON.parse(raw);
    if (!Array.isArray(items)) return;
    for (const item of items) {
      const jobId = String(item || "").trim();
      if (jobId) {
        acknowledgedFailedJobs.add(jobId);
      }
    }
  } catch {
    // ignore malformed localStorage values
  }
}

function persistAcknowledgedFailedJobs() {
  localStorage.setItem(
    CRAWLER_FAILURE_ALERT_ACK_KEY,
    JSON.stringify(Array.from(acknowledgedFailedJobs).slice(-200)),
  );
}

function acknowledgeCrawlerFailure(jobId: string) {
  acknowledgedFailedJobs.add(jobId);
  persistAcknowledgedFailedJobs();
  crawlerFailureAlerts.value = crawlerFailureAlerts.value.filter(
    (item) => item.job_id !== jobId,
  );
}

async function runAction(action: () => Promise<any>) {
  loading.value = true;
  try {
    const { data } = await action();
    output.value = JSON.stringify(data, null, 2);
    return data;
  } catch (err: any) {
    output.value = `执行失败:\n${normalizeError(err)}`;
    return null;
  } finally {
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
  await runAction(() =>
    api.debateStart({
      cycle_count: cycleCount.value,
      resume: false,
    }),
  );
  await refreshDebateStatus();
}

async function stopDebate() {
  await runAction(() => api.debateStop());
  await refreshDebateStatus();
}

async function loadCrawlerJobLogs(jobId: string) {
  try {
    const { data } = await api.getCrawlerJobLogs(jobId, 200);
    selectedJobLogs.value = data?.data?.logs || [];
  } catch (err: any) {
    selectedJobLogs.value = [`日志加载失败：${normalizeError(err)}`];
  }
}

function checkCrawlerFailures() {
  const nextAlerts: CrawlerFailureAlert[] = [];
  for (const job of crawlerJobs.value) {
    if (
      (job.status === "failed" || job.status === "timeout")
      && !acknowledgedFailedJobs.has(job.job_id)
    ) {
      nextAlerts.push({
        job_id: job.job_id,
        source: job.source,
        status: job.status,
        reason: job.error_message || "crawler failed",
      });
    }
  }
  crawlerFailureAlerts.value = nextAlerts;
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
  } catch (err: any) {
    if (!silent) {
      output.value = `加载爬虫任务失败:\n${normalizeError(err)}`;
    }
  }
}

async function triggerCrawler(source: CrawlerSource) {
  crawlerLoadingSource.value = source;
  try {
    const { data } = await api.createCrawlerJob(source);
    output.value = JSON.stringify(data, null, 2);
    const newJobId = data?.data?.job?.job_id;
    if (newJobId) {
      selectedJobId.value = newJobId;
    }
    await loadCrawlerJobs(true);
  } catch (err: any) {
    output.value = `执行失败:\n${normalizeError(err)}`;
    await loadCrawlerJobs(true);
  } finally {
    crawlerLoadingSource.value = null;
  }
}

function selectJob(jobId: string) {
  selectedJobId.value = jobId;
  void loadCrawlerJobLogs(jobId);
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    queued: "排队中",
    running: "运行中",
    success: "成功",
    failed: "失败",
    timeout: "超时",
  };
  return map[status] || status;
}

function formatDateTime(value: string | null | undefined): string {
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
    runtimeConfig.crawler_job_timeout_seconds = Number(
      cfg.crawler_job_timeout_seconds ?? 1800,
    );
    return data;
  });
}

async function saveRuntimeConfig() {
  configSaving.value = true;
  try {
    const trim = (value: string) => value.trim();
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
      crawler_job_timeout_seconds: Math.max(
        300,
        Number(runtimeConfig.crawler_job_timeout_seconds || 1800),
      ),
    };
    const { data } = await api.updateRuntimeConfig(payload);
    output.value = JSON.stringify(data, null, 2);
  } catch (err: any) {
    output.value = `保存失败:\n${normalizeError(err)}`;
  } finally {
    configSaving.value = false;
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
  } catch (err: any) {
    output.value = `加载策略失败:\n${normalizeError(err)}`;
  }
}

async function saveQaPolicy() {
  policySaving.value = true;
  try {
    await api.updateQaPolicy({ ...qaPolicy });
    await loadPolicies();
    output.value = "问答策略已更新";
  } catch (err: any) {
    output.value = `保存问答策略失败:\n${normalizeError(err)}`;
  } finally {
    policySaving.value = false;
  }
}

async function saveDebatePolicy() {
  policySaving.value = true;
  try {
    await api.updateDebatePolicy({ ...debatePolicy });
    await loadPolicies();
    output.value = "辩论策略已更新";
  } catch (err: any) {
    output.value = `保存辩论策略失败:\n${normalizeError(err)}`;
  } finally {
    policySaving.value = false;
  }
}

async function saveSchedulerPolicy() {
  policySaving.value = true;
  try {
    await api.updateSchedulerPolicy({ ...schedulerPolicy });
    await loadPolicies();
    output.value = "调度策略已更新";
  } catch (err: any) {
    output.value = `保存调度策略失败:\n${normalizeError(err)}`;
  } finally {
    policySaving.value = false;
  }
}

async function saveRealtimePolicy() {
  policySaving.value = true;
  try {
    await api.updateRealtimePolicy({ ...realtimePolicy });
    await loadPolicies();
    output.value = "实时策略已更新";
  } catch (err: any) {
    output.value = `保存实时策略失败:\n${normalizeError(err)}`;
  } finally {
    policySaving.value = false;
  }
}

onMounted(async () => {
  loadAcknowledgedFailedJobs();
  await Promise.all([
    refreshDebateStatus(),
    loadRuntimeConfig(),
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
</script>

<template>
  <div class="grid">
    <div class="panel col-6">
      <p class="section-title">辩论控制</p>
      <div class="row" style="align-items: center; margin-bottom: 10px">
        <input v-model.number="cycleCount" type="number" min="1" max="50" style="width: 120px" />
        <button class="primary" :disabled="loading" @click="startDebate">启动</button>
        <button class="warn" :disabled="loading" @click="stopDebate">停止</button>
        <button class="secondary" :disabled="loading" @click="refreshDebateStatus">刷新</button>
      </div>
      <pre class="panel-soft" style="white-space: pre-wrap; font-size: 12px">{{ debateStatus ? JSON.stringify(debateStatus, null, 2) : "暂无状态" }}</pre>
    </div>

    <div class="panel col-6">
      <p class="section-title">爬虫任务（异步）</p>
      <div class="row" style="margin-bottom: 10px">
        <button
          class="primary"
          :disabled="crawlerLoadingSource !== null || isSourceRunning('zhihu')"
          @click="triggerCrawler('zhihu')"
        >
          {{ isSourceRunning("zhihu") ? "知乎运行中" : crawlerLoadingSource === "zhihu" ? "启动中..." : "运行知乎爬虫" }}
        </button>
        <button
          class="secondary"
          :disabled="crawlerLoadingSource !== null || isSourceRunning('weibo')"
          @click="triggerCrawler('weibo')"
        >
          {{ isSourceRunning("weibo") ? "微博运行中" : crawlerLoadingSource === "weibo" ? "启动中..." : "运行微博爬虫" }}
        </button>
        <button class="secondary" @click="loadCrawlerJobs()">刷新任务</button>
      </div>
      <p class="form-note" style="margin-bottom: 10px">
        已启用同源互斥。任务失败时会在页面内提醒你更新 Cookie，不会反复弹窗打断操作。
      </p>
      <div v-if="crawlerFailureAlerts.length > 0" class="stack" style="margin-bottom: 10px">
        <div
          v-for="alert in crawlerFailureAlerts"
          :key="alert.job_id"
          class="panel-soft"
          style="border: 1px solid #f59e0b; background: #fff7ed"
        >
          <div style="font-weight: 600; color: #9a3412; margin-bottom: 6px">
            {{ alert.source === "zhihu" ? "知乎" : "微博" }} 爬虫任务失败（{{ statusLabel(alert.status) }}）
          </div>
          <div style="font-size: 13px; white-space: pre-wrap; color: #7c2d12">
            原因：{{ alert.reason }}
          </div>
          <div class="row" style="margin-top: 8px">
            <button class="secondary" @click="selectJob(alert.job_id)">查看日志</button>
            <button class="primary" @click="acknowledgeCrawlerFailure(alert.job_id)">知道了</button>
          </div>
        </div>
      </div>
      <div class="stack" style="margin-bottom: 10px">
        <label>知乎 Cookie（快捷更新）</label>
        <textarea
          v-model="runtimeConfig.zhihu_cookie"
          rows="3"
          placeholder="粘贴完整知乎 Cookie，保存后立即生效"
        />
        <label>微博 Cookie（快捷更新）</label>
        <textarea
          v-model="runtimeConfig.weibo_cookie"
          rows="3"
          placeholder="粘贴完整微博 Cookie，保存后立即生效"
        />
        <label>爬虫超时(秒)</label>
        <input
          v-model.number="runtimeConfig.crawler_job_timeout_seconds"
          type="number"
          min="300"
          max="7200"
        />
        <p class="form-note">默认 1800 秒，即 30 分钟。</p>
        <div class="row">
          <button class="primary" :disabled="configSaving" @click="saveRuntimeConfig">
            保存 Cookie 与超时配置
          </button>
        </div>
      </div>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>任务</th>
              <th>来源</th>
              <th>状态</th>
              <th>耗时(秒)</th>
              <th>结束时间(北京时间)</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in crawlerJobs" :key="job.job_id">
              <td class="mono">{{ job.job_id.slice(0, 10) }}...</td>
              <td>{{ job.source }}</td>
              <td><span class="badge">{{ statusLabel(job.status) }}</span></td>
              <td>{{ job.duration_seconds ?? "-" }}</td>
              <td>{{ formatDateTime(job.finished_at) }}</td>
              <td>
                <button class="secondary" @click="selectJob(job.job_id)">日志</button>
              </td>
            </tr>
            <tr v-if="crawlerJobs.length === 0">
              <td colspan="6" style="text-align: center; opacity: 0.8">暂无任务</td>
            </tr>
          </tbody>
        </table>
      </div>
      <pre class="panel-soft" style="white-space: pre-wrap; font-size: 12px; margin-top: 10px; max-height: 220px; overflow: auto">{{ selectedJobLogs.length ? selectedJobLogs.join("\n") : "请选择任务查看日志" }}</pre>
    </div>

    <div class="panel col-6">
      <p class="section-title">问答策略</p>
      <div class="stack">
        <label><input v-model="qaPolicy.enabled" type="checkbox" /> 启用</label>
        <label>每日目标热点数</label>
        <input v-model.number="qaPolicy.target_daily_hotspots" type="number" min="1" max="5000" />
        <label>调度最小间隔(秒)</label>
        <input v-model.number="qaPolicy.dispatch_min_seconds" type="number" min="1" max="600" />
        <label>调度最大间隔(秒)</label>
        <input v-model.number="qaPolicy.dispatch_max_seconds" type="number" min="1" max="1800" />
        <label>抖动最小值</label>
        <input v-model.number="qaPolicy.jitter_min" type="number" min="0.5" max="1" step="0.01" />
        <label>抖动最大值</label>
        <input v-model.number="qaPolicy.jitter_max" type="number" min="1" max="2" step="0.01" />
        <label>最大并行度</label>
        <input v-model.number="qaPolicy.max_parallelism" type="number" min="1" max="8" />
        <label>EWMA平滑系数</label>
        <input v-model.number="qaPolicy.ewma_alpha" type="number" min="0.05" max="0.95" step="0.01" />
      </div>
      <div class="row" style="margin-top: 10px">
        <button class="primary" :disabled="policySaving" @click="saveQaPolicy">保存问答策略</button>
      </div>
    </div>

    <div class="panel col-6">
      <p class="section-title">辩论策略</p>
      <div class="stack">
        <label><input v-model="debatePolicy.enabled" type="checkbox" /> 启用</label>
        <label>每日目标最小场次</label>
        <input v-model.number="debatePolicy.daily_target_min" type="number" min="1" max="100" />
        <label>每日目标最大场次</label>
        <input v-model.number="debatePolicy.daily_target_max" type="number" min="1" max="200" />
        <label>最小间隔(分钟)</label>
        <input v-model.number="debatePolicy.interval_min_minutes" type="number" min="1" max="1440" />
        <label>最大间隔(分钟)</label>
        <input v-model.number="debatePolicy.interval_max_minutes" type="number" min="1" max="1440" />
        <label>抖动最小值</label>
        <input v-model.number="debatePolicy.jitter_min" type="number" min="0.5" max="1" step="0.01" />
        <label>抖动最大值</label>
        <input v-model.number="debatePolicy.jitter_max" type="number" min="1" max="2" step="0.01" />
        <label><input v-model="debatePolicy.new_agent_auto_join" type="checkbox" /> 新Agent自动加入</label>
      </div>
      <div class="row" style="margin-top: 10px">
        <button class="primary" :disabled="policySaving" @click="saveDebatePolicy">保存辩论策略</button>
      </div>
    </div>

    <div class="panel col-6">
      <p class="section-title">爬虫调度策略</p>
      <div class="stack">
        <label><input v-model="schedulerPolicy.auto_crawler_enabled" type="checkbox" /> 启用自动爬虫</label>
        <label>爬虫间隔(分钟)</label>
        <input v-model.number="schedulerPolicy.auto_crawler_interval_minutes" type="number" min="10" max="1440" />
        <label>来源</label>
        <div class="row">
          <label><input v-model="schedulerPolicy.sources" type="checkbox" value="zhihu" /> 知乎</label>
          <label><input v-model="schedulerPolicy.sources" type="checkbox" value="weibo" /> 微博</label>
        </div>
      </div>
      <div class="row" style="margin-top: 10px">
        <button class="primary" :disabled="policySaving" @click="saveSchedulerPolicy">保存调度策略</button>
      </div>
    </div>

    <div class="panel col-6">
      <p class="section-title">实时策略</p>
      <div class="stack">
        <label><input v-model="realtimePolicy.sse_enabled" type="checkbox" /> 启用SSE</label>
        <label>轮询回退间隔(秒)</label>
        <input v-model.number="realtimePolicy.fallback_poll_seconds" type="number" min="1" max="120" />
      </div>
      <div class="row" style="margin-top: 10px">
        <button class="primary" :disabled="policySaving" @click="saveRealtimePolicy">保存实时策略</button>
      </div>
    </div>

    <div class="panel col-12">
      <p class="section-title">LLM容灾配置</p>
      <div class="panel-soft" style="margin-bottom: 12px">
        系统模型的正式管理入口已迁移到「模型管理」页面。这里保留的 single / dual_fallback
        仅作为 legacy 兼容来源展示，用于在模型目录为空时兜底生成默认系统模型。
      </div>
      <div class="stack">
        <label>容灾模式</label>
        <select v-model="runtimeConfig.llm_failover_mode">
          <option value="single">single（仅主模型）</option>
          <option value="dual_fallback">dual_fallback（主失败自动回退）</option>
        </select>

        <label>主模型 API Base</label>
        <input v-model="runtimeConfig.openai_api_base" placeholder="https://api.example.com/v1" />
        <label>主模型</label>
        <input v-model="runtimeConfig.llm_model" placeholder="gpt-5-mini" />
        <label>主模型温度</label>
        <input v-model.number="runtimeConfig.llm_temperature" type="number" min="0" max="2" step="0.1" />
        <label>主模型 API Key</label>
        <div class="row" style="gap: 8px">
          <input v-model="runtimeConfig.openai_api_key" :type="showOpenAIKey ? 'text' : 'password'" placeholder="sk-..." style="flex: 1" />
          <button class="secondary" type="button" @click="showOpenAIKey = !showOpenAIKey">
            {{ showOpenAIKey ? "隐藏" : "显示" }}
          </button>
        </div>

        <template v-if="runtimeConfig.llm_failover_mode === 'dual_fallback'">
          <label>备模型 API Base</label>
          <input v-model="runtimeConfig.openai_api_base_secondary" placeholder="https://api.example.com/v1" />
          <label>备模型</label>
          <input v-model="runtimeConfig.llm_model_secondary" placeholder="gpt-5-mini" />
          <label>备模型温度</label>
          <input v-model.number="runtimeConfig.llm_temperature_secondary" type="number" min="0" max="2" step="0.1" />
          <label>备模型 API Key</label>
          <div class="row" style="gap: 8px">
            <input v-model="runtimeConfig.openai_api_key_secondary" :type="showSecondaryOpenAIKey ? 'text' : 'password'" placeholder="sk-..." style="flex: 1" />
            <button class="secondary" type="button" @click="showSecondaryOpenAIKey = !showSecondaryOpenAIKey">
              {{ showSecondaryOpenAIKey ? "隐藏" : "显示" }}
            </button>
          </div>
        </template>

        <label>Tavily API Key</label>
        <div class="row" style="gap: 8px">
          <input v-model="runtimeConfig.tavily_api_key" :type="showTavilyKey ? 'text' : 'password'" placeholder="tvly-..." style="flex: 1" />
          <button class="secondary" type="button" @click="showTavilyKey = !showTavilyKey">
            {{ showTavilyKey ? "隐藏" : "显示" }}
          </button>
        </div>
      </div>
      <div class="row" style="margin: 10px 0 10px">
        <button class="primary" :disabled="configSaving" @click="saveRuntimeConfig">保存配置</button>
        <button class="secondary" :disabled="loading" @click="loadRuntimeConfig">重新加载</button>
      </div>
    </div>

    <div class="panel col-12">
      <p class="section-title">告警中心</p>
      <div class="panel-soft" style="display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap">
        <div>
          模型回退、问题生成失败、回答生成失败都已迁移到独立的「告警中心」，运维页不再混放详细告警列表。
        </div>
        <RouterLink class="primary-link" to="/alerts">前往告警中心</RouterLink>
      </div>
    </div>

    <div class="panel col-12">
      <p class="section-title">容量快照</p>
      <pre class="panel-soft" style="white-space: pre-wrap; font-size: 12px">{{ capacitySnapshot ? JSON.stringify(capacitySnapshot, null, 2) : "暂无容量数据" }}</pre>
    </div>

    <div class="panel col-12">
      <p class="section-title">输出信息</p>
      <pre class="panel-soft" style="white-space: pre-wrap; font-size: 12px">{{ output || "操作输出将显示在这里" }}</pre>
    </div>
  </div>
</template>
