<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref } from "vue";
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

const loading = ref(false);
const output = ref("");

const debateStatus = ref<any>(null);
const cycleCount = ref(1);

const crawlerLoadingSource = ref<CrawlerSource | null>(null);
const crawlerJobs = ref<CrawlerJob[]>([]);
const selectedJobId = ref("");
const selectedJobLogs = ref<string[]>([]);
const notifiedFailedJobs = new Set<string>();

const configSaving = ref(false);
const showOpenAIKey = ref(false);
const showTavilyKey = ref(false);
const runtimeConfig = reactive({
  openai_api_base: "",
  openai_api_key: "",
  llm_model: "",
  llm_temperature: 0.7,
  tavily_api_key: "",
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

async function runAction(action: () => Promise<any>) {
  loading.value = true;
  try {
    const { data } = await action();
    output.value = JSON.stringify(data, null, 2);
    return data;
  } catch (err: any) {
    output.value = `执行失败：\n${normalizeError(err)}`;
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
  for (const job of crawlerJobs.value) {
    if ((job.status === "failed" || job.status === "timeout") && !notifiedFailedJobs.has(job.job_id)) {
      notifiedFailedJobs.add(job.job_id);
      const reason = job.error_message || "crawler failed";
      window.alert(
        `${job.source === "zhihu" ? "知乎" : "微博"} 爬虫任务失败（${statusLabel(job.status)}）。\n原因：${reason}\n请在后台更新 Cookie 后重试。`,
      );
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
  } catch (err: any) {
    if (!silent) {
      output.value = `加载爬虫任务失败：\n${normalizeError(err)}`;
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
    output.value = `执行失败：\n${normalizeError(err)}`;
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
    runtimeConfig.openai_api_base = cfg.openai_api_base || "";
    runtimeConfig.openai_api_key = cfg.openai_api_key || "";
    runtimeConfig.llm_model = cfg.llm_model || "";
    runtimeConfig.llm_temperature = Number(cfg.llm_temperature ?? 0.7);
    runtimeConfig.tavily_api_key = cfg.tavily_api_key || "";
    return data;
  });
}

async function saveRuntimeConfig() {
  configSaving.value = true;
  try {
    const payload = {
      openai_api_base: runtimeConfig.openai_api_base,
      openai_api_key: runtimeConfig.openai_api_key,
      llm_model: runtimeConfig.llm_model,
      llm_temperature: Number(runtimeConfig.llm_temperature),
      tavily_api_key: runtimeConfig.tavily_api_key,
    };
    const { data } = await api.updateRuntimeConfig(payload);
    output.value = JSON.stringify(data, null, 2);
  } catch (err: any) {
    output.value = `保存失败：\n${normalizeError(err)}`;
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
    output.value = `加载策略失败：\n${normalizeError(err)}`;
  }
}

async function saveQaPolicy() {
  policySaving.value = true;
  try {
    await api.updateQaPolicy({ ...qaPolicy });
    await loadPolicies();
    output.value = "问答策略已更新";
  } catch (err: any) {
    output.value = `保存问答策略失败：\n${normalizeError(err)}`;
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
    output.value = `保存辩论策略失败：\n${normalizeError(err)}`;
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
    output.value = `保存调度策略失败：\n${normalizeError(err)}`;
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
    output.value = `保存实时策略失败：\n${normalizeError(err)}`;
  } finally {
    policySaving.value = false;
  }
}

onMounted(async () => {
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
        已启用同源互斥。任务失败时会弹窗提醒你更新 Cookie。
      </p>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>任务</th>
              <th>来源</th>
              <th>状态</th>
              <th>耗时(秒)</th>
              <th>结束时间（北京时间）</th>
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
        <label>最大并发</label>
        <input v-model.number="qaPolicy.max_parallelism" type="number" min="1" max="8" />
        <label>EWMA 平滑系数</label>
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
        <label><input v-model="debatePolicy.new_agent_auto_join" type="checkbox" /> 新 Agent 自动加入</label>
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
        <label><input v-model="realtimePolicy.sse_enabled" type="checkbox" /> 启用 SSE</label>
        <label>轮询回退间隔(秒)</label>
        <input v-model.number="realtimePolicy.fallback_poll_seconds" type="number" min="1" max="120" />
      </div>
      <div class="row" style="margin-top: 10px">
        <button class="primary" :disabled="policySaving" @click="saveRealtimePolicy">保存实时策略</button>
      </div>
    </div>

    <div class="panel col-12">
      <p class="section-title">模型与搜索运行配置</p>
      <div class="stack">
        <label>LLM 接口地址</label>
        <input v-model="runtimeConfig.openai_api_base" placeholder="https://api.example.com/v1" />

        <label>LLM 模型</label>
        <input v-model="runtimeConfig.llm_model" placeholder="gpt-5-mini" />

        <label>LLM 温度</label>
        <input v-model.number="runtimeConfig.llm_temperature" type="number" min="0" max="2" step="0.1" />

        <label>LLM API Key</label>
        <div class="row" style="gap: 8px">
          <input v-model="runtimeConfig.openai_api_key" :type="showOpenAIKey ? 'text' : 'password'" placeholder="sk-..." style="flex: 1" />
          <button class="secondary" type="button" @click="showOpenAIKey = !showOpenAIKey">
            {{ showOpenAIKey ? "隐藏" : "显示" }}
          </button>
        </div>

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
      <p class="section-title">容量快照</p>
      <pre class="panel-soft" style="white-space: pre-wrap; font-size: 12px">{{ capacitySnapshot ? JSON.stringify(capacitySnapshot, null, 2) : "暂无容量数据" }}</pre>
    </div>

    <div class="panel col-12">
      <p class="section-title">输出信息</p>
      <pre class="panel-soft" style="white-space: pre-wrap; font-size: 12px">{{ output || "操作输出将显示在这里" }}</pre>
    </div>
  </div>
</template>
