<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { api } from "../api";

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

const debateStatus = ref<any>(null);
const output = ref("");
const cycleCount = ref(1);
const loading = ref(false);
const crawlerLoadingSource = ref<CrawlerSource | null>(null);
const crawlerJobs = ref<CrawlerJob[]>([]);
const selectedJobId = ref<string>("");
const selectedJobLogs = ref<string[]>([]);
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

function startCrawlerPolling() {
  if (crawlerPollTimer !== null) return;
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
  const hasRunningJob = crawlerJobs.value.some((job) =>
    isRunningStatus(job.status),
  );
  if (hasRunningJob) {
    startCrawlerPolling();
  } else {
    stopCrawlerPolling();
  }
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
  } catch (err: any) {
    if (!silent) {
      output.value = `拉取任务失败:\n${normalizeError(err)}`;
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
  } catch (err: any) {
    output.value = `保存失败:\n${normalizeError(err)}`;
  } finally {
    configSaving.value = false;
  }
}

onMounted(async () => {
  await Promise.all([refreshDebateStatus(), loadRuntimeConfig(), loadCrawlerJobs()]);
});

onUnmounted(() => {
  stopCrawlerPolling();
});
</script>

<template>
  <div class="grid">
    <div class="panel col-6">
      <p class="section-title">辩论控制</p>
      <div class="row" style="align-items: center; margin-bottom: 10px">
        <input
          v-model.number="cycleCount"
          type="number"
          min="1"
          max="50"
          style="width: 120px"
        />
        <button class="primary" :disabled="loading" @click="startDebate">
          启动辩论
        </button>
        <button class="warn" :disabled="loading" @click="stopDebate">
          停止辩论
        </button>
        <button class="secondary" :disabled="loading" @click="refreshDebateStatus">
          刷新状态
        </button>
      </div>
      <pre class="panel-soft" style="white-space: pre-wrap; font-size: 12px">{{
        debateStatus ? JSON.stringify(debateStatus, null, 2) : "暂无状态"
      }}</pre>
    </div>

    <div class="panel col-6">
      <p class="section-title">爬虫任务面板（异步）</p>
      <div class="row" style="margin-bottom: 10px">
        <button
          class="primary"
          :disabled="crawlerLoadingSource !== null || isSourceRunning('zhihu')"
          @click="triggerCrawler('zhihu')"
        >
          {{
            isSourceRunning("zhihu")
              ? "知乎任务运行中"
              : crawlerLoadingSource === "zhihu"
                ? "触发中..."
                : "触发知乎爬虫"
          }}
        </button>
        <button
          class="secondary"
          :disabled="crawlerLoadingSource !== null || isSourceRunning('weibo')"
          @click="triggerCrawler('weibo')"
        >
          {{
            isSourceRunning("weibo")
              ? "微博任务运行中"
              : crawlerLoadingSource === "weibo"
                ? "触发中..."
                : "触发微博爬虫"
          }}
        </button>
        <button class="secondary" @click="loadCrawlerJobs()">刷新任务</button>
      </div>
      <p class="form-note" style="margin-bottom: 10px">
        说明：同源任务互斥，运行中可实时查看状态与日志，不再等待长请求。
      </p>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>任务ID</th>
              <th>来源</th>
              <th>状态</th>
              <th>耗时(s)</th>
              <th>结束时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in crawlerJobs" :key="job.job_id">
              <td class="mono">{{ job.job_id.slice(0, 10) }}...</td>
              <td>{{ job.source }}</td>
              <td>
                <span class="badge">{{ statusLabel(job.status) }}</span>
              </td>
              <td>{{ job.duration_seconds ?? "-" }}</td>
              <td>{{ job.finished_at || "-" }}</td>
              <td>
                <button class="secondary" @click="selectJob(job.job_id)">
                  查看日志
                </button>
              </td>
            </tr>
            <tr v-if="crawlerJobs.length === 0">
              <td colspan="6" style="text-align: center; opacity: 0.8">暂无任务</td>
            </tr>
          </tbody>
        </table>
      </div>
      <pre
        class="panel-soft"
        style="white-space: pre-wrap; font-size: 12px; margin-top: 10px; max-height: 220px; overflow: auto"
      >{{ selectedJobLogs.length ? selectedJobLogs.join("\n") : "选择任务后可查看日志" }}</pre>
    </div>

    <div class="panel col-12">
      <p class="section-title" style="margin-top: 0">模型与检索配置</p>
      <div class="stack">
        <label>LLM Base URL</label>
        <input
          v-model="runtimeConfig.openai_api_base"
          placeholder="https://api.example.com/v1"
        />

        <label>LLM Model</label>
        <input v-model="runtimeConfig.llm_model" placeholder="gpt-4o-mini" />

        <label>LLM Temperature</label>
        <input
          v-model.number="runtimeConfig.llm_temperature"
          type="number"
          min="0"
          max="2"
          step="0.1"
          placeholder="0.7"
        />

        <label>LLM API Key</label>
        <div class="row" style="gap: 8px">
          <input
            v-model="runtimeConfig.openai_api_key"
            :type="showOpenAIKey ? 'text' : 'password'"
            placeholder="sk-..."
            style="flex: 1"
          />
          <button
            class="secondary"
            type="button"
            @click="showOpenAIKey = !showOpenAIKey"
          >
            {{ showOpenAIKey ? "隐藏" : "显示" }}
          </button>
        </div>

        <label>Tavily API Key</label>
        <div class="row" style="gap: 8px">
          <input
            v-model="runtimeConfig.tavily_api_key"
            :type="showTavilyKey ? 'text' : 'password'"
            placeholder="tvly-..."
            style="flex: 1"
          />
          <button
            class="secondary"
            type="button"
            @click="showTavilyKey = !showTavilyKey"
          >
            {{ showTavilyKey ? "隐藏" : "显示" }}
          </button>
        </div>
      </div>
      <div class="row" style="margin: 10px 0 10px">
        <button class="primary" :disabled="configSaving" @click="saveRuntimeConfig">
          保存配置
        </button>
        <button class="secondary" :disabled="loading" @click="loadRuntimeConfig">
          刷新配置
        </button>
      </div>
      <pre class="panel-soft" style="white-space: pre-wrap; font-size: 12px">{{
        output || "执行结果会显示在这里"
      }}</pre>
    </div>
  </div>
</template>
