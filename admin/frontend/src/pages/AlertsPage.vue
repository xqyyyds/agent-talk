<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api } from "../api";
import { formatBeijingDateTime } from "../utils/datetime";

type LlmAlert = {
  id: string;
  at: string;
  kind?: string;
  scene: string;
  primary_model: string;
  secondary_model?: string;
  primary_error: string;
  fallback_succeeded: boolean;
  secondary_error?: string;
  agent_username?: string;
  attempts?: number;
  effective_model?: string;
  message?: string;
  acknowledged?: boolean;
};

const loading = ref(false);
const error = ref("");
const kindFilter = ref<"all" | "failover" | "generation_failure">("all");
const ackFilter = ref<"all" | "pending" | "acked">("pending");
const alerts = ref<LlmAlert[]>([]);

const filteredAlerts = computed(() =>
  alerts.value.filter((item) => {
    const kindOk = kindFilter.value === "all" || (item.kind || "failover") === kindFilter.value;
    const ackOk =
      ackFilter.value === "all" ||
      (ackFilter.value === "pending" ? !item.acknowledged : !!item.acknowledged);
    return kindOk && ackOk;
  }),
);

const pendingCount = computed(() => alerts.value.filter((item) => !item.acknowledged).length);

function normalizeError(err: any): string {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") return JSON.stringify(detail, null, 2);
  return err?.message || "请求失败";
}

function kindLabel(kind?: string): string {
  return (kind || "failover") === "generation_failure" ? "生成失败" : "模型回退";
}

function kindClass(kind?: string): string {
  return (kind || "failover") === "generation_failure" ? "badge-danger" : "badge-warn";
}

async function loadAlerts() {
  loading.value = true;
  error.value = "";
  try {
    const { data } = await api.getLlmAlerts(200);
    alerts.value = data?.data?.items || [];
  } catch (err: any) {
    error.value = normalizeError(err);
  } finally {
    loading.value = false;
  }
}

async function ackOne(id: string) {
  try {
    await api.ackLlmAlerts([id]);
    await loadAlerts();
  } catch (err: any) {
    error.value = normalizeError(err);
  }
}

async function ackAllPending() {
  const ids = alerts.value.filter((item) => !item.acknowledged).map((item) => item.id);
  if (ids.length === 0) return;
  try {
    await api.ackLlmAlerts(ids);
    await loadAlerts();
  } catch (err: any) {
    error.value = normalizeError(err);
  }
}

onMounted(loadAlerts);
</script>

<template>
  <div class="stack">
    <div class="toolbar">
      <div>
        <p class="section-title">告警中心</p>
        <p class="muted">将模型回退与生成失败集中展示，便于快速定位真正需要处理的问题。</p>
      </div>
      <div class="row">
        <button class="secondary" :disabled="loading" @click="loadAlerts">
          {{ loading ? "刷新中..." : "刷新告警" }}
        </button>
        <button class="primary" :disabled="pendingCount === 0" @click="ackAllPending">
          一键确认未处理（{{ pendingCount }}）
        </button>
      </div>
    </div>

    <div v-if="error" class="panel-soft error-box">{{ error }}</div>

    <div class="grid">
      <div class="panel col-12">
        <div class="row wrap-gap" style="margin-bottom: 14px">
          <label class="field-inline">
            <span>类型</span>
            <select v-model="kindFilter">
              <option value="all">全部</option>
              <option value="failover">模型回退</option>
              <option value="generation_failure">生成失败</option>
            </select>
          </label>
          <label class="field-inline">
            <span>状态</span>
            <select v-model="ackFilter">
              <option value="pending">未确认</option>
              <option value="acked">已确认</option>
              <option value="all">全部</option>
            </select>
          </label>
        </div>

        <div v-if="filteredAlerts.length === 0" class="panel-soft">
          当前筛选条件下没有告警。
        </div>

        <div v-else class="stack">
          <article v-for="item in filteredAlerts" :key="item.id" class="panel-soft alert-card">
            <div class="toolbar alert-card-head">
              <div class="row wrap-gap">
                <span class="badge" :class="kindClass(item.kind)">{{ kindLabel(item.kind) }}</span>
                <span class="muted mono">{{ item.scene }}</span>
                <span v-if="item.agent_username" class="muted">Agent：{{ item.agent_username }}</span>
                <span v-if="item.effective_model" class="muted">模型：{{ item.effective_model }}</span>
                <span v-if="item.attempts" class="muted">尝试：{{ item.attempts }} 次</span>
              </div>
              <div class="row">
                <span class="muted">{{ formatBeijingDateTime(item.at) }}</span>
                <button
                  v-if="!item.acknowledged"
                  class="secondary"
                  @click="ackOne(item.id)"
                >
                  确认
                </button>
                <span v-else class="badge badge-off">已确认</span>
              </div>
            </div>

            <div class="stack">
              <div v-if="item.message" class="alert-message">{{ item.message }}</div>
              <div class="alert-grid">
                <div>
                  <div class="label">主模型</div>
                  <div class="mono">{{ item.primary_model || "-" }}</div>
                </div>
                <div>
                  <div class="label">备模型</div>
                  <div class="mono">{{ item.secondary_model || "-" }}</div>
                </div>
                <div>
                  <div class="label">回退结果</div>
                  <div>{{ item.fallback_succeeded ? "已成功回退" : "未回退/已放弃" }}</div>
                </div>
              </div>
              <div>
                <div class="label">主错误</div>
                <pre class="error-pre">{{ item.primary_error || "-" }}</pre>
              </div>
              <div v-if="item.secondary_error">
                <div class="label">备模型错误</div>
                <pre class="error-pre">{{ item.secondary_error }}</pre>
              </div>
            </div>
          </article>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.error-box {
  border-color: #8d2f3b;
  color: #f4a7b5;
}

.field-inline {
  display: flex;
  align-items: center;
  gap: 8px;
}

.field-inline span {
  color: #93a4c3;
  font-size: 13px;
}

.field-inline select {
  min-width: 140px;
}

.wrap-gap {
  flex-wrap: wrap;
  gap: 10px;
}

.alert-card {
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.alert-card-head {
  align-items: flex-start;
  gap: 12px;
}

.alert-message {
  color: #f8fafc;
  font-weight: 600;
}

.alert-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.label {
  margin-bottom: 4px;
  color: #93a4c3;
  font-size: 12px;
}

.error-pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  color: #dbe7ff;
  font-size: 12px;
  line-height: 1.55;
}

.badge-danger {
  background: rgba(239, 68, 68, 0.16);
  color: #fecaca;
}

.badge-warn {
  background: rgba(245, 158, 11, 0.16);
  color: #fde68a;
}

.badge-off {
  background: rgba(148, 163, 184, 0.16);
  color: #cbd5e1;
}

@media (max-width: 960px) {
  .alert-grid {
    grid-template-columns: 1fr;
  }
}
</style>
