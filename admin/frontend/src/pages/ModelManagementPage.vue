<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { api } from "../api";

type ModelCatalogItem = {
  id: string;
  label: string;
  provider_type: string;
  base_url: string;
  api_key: string;
  model: string;
  enabled: boolean;
  is_default: boolean;
  sort_order: number;
};

type ModelCatalogForm = {
  id: string;
  label: string;
  provider_type: string;
  base_url: string;
  api_key: string;
  model: string;
  enabled: boolean;
  is_default: boolean;
  sort_order: number;
};

function defaultForm(): ModelCatalogForm {
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
const catalog = ref<ModelCatalogItem[]>([]);
const defaultModelId = ref("");
const form = reactive<ModelCatalogForm>(defaultForm());

const legacySummary = computed(() => {
  if (catalog.value.length === 0) return "当前尚未发现系统模型目录，仍可能由 legacy 主备配置兜底生成。";
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

function normalizeCatalogPayload(data: any) {
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
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "加载模型目录失败";
  } finally {
    loading.value = false;
  }
}

function editItem(item: ModelCatalogItem) {
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

function validateForm(): string | null {
  if (!form.id.trim()) return "请填写稳定 ID";
  if (!form.label.trim()) return "请填写展示名称";
  if (!form.base_url.trim()) return "请填写 Base URL";
  if (!form.model.trim()) return "请填写模型名";
  if (!editingId.value && !form.api_key.trim()) return "新建系统模型时请填写 API Key";
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
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "保存失败";
  } finally {
    saving.value = false;
  }
}

async function setDefault(item: ModelCatalogItem) {
  clearMessages();
  try {
    const { data } = await api.setDefaultModelCatalogItem(item.id);
    normalizeCatalogPayload(data);
    success.value = `默认模型已切换为 ${item.label}`;
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "设置默认模型失败";
  }
}

async function toggleEnabled(item: ModelCatalogItem) {
  clearMessages();
  try {
    const { data } = item.enabled
      ? await api.disableModelCatalogItem(item.id)
      : await api.enableModelCatalogItem(item.id);
    normalizeCatalogPayload(data);
    success.value = item.enabled ? `已禁用 ${item.label}` : `已启用 ${item.label}`;
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "更新模型状态失败";
  }
}

async function moveItem(item: ModelCatalogItem, direction: -1 | 1) {
  const currentIndex = catalog.value.findIndex((entry) => entry.id === item.id);
  if (currentIndex < 0) return;
  const targetIndex = currentIndex + direction;
  if (targetIndex < 0 || targetIndex >= catalog.value.length) return;
  const next = [...catalog.value];
  const [moved] = next.splice(currentIndex, 1);
  next.splice(targetIndex, 0, moved);
  try {
    const { data } = await api.reorderModelCatalog(next.map((entry) => entry.id));
    normalizeCatalogPayload(data);
    success.value = `已调整 ${item.label} 的展示顺序`;
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "调整顺序失败";
  }
}

onMounted(loadCatalog);
</script>

<template>
  <div class="grid">
    <div class="panel col-5">
      <div class="toolbar" style="margin-bottom: 10px">
        <p class="section-title">系统模型目录</p>
        <button class="secondary" :disabled="saving" @click="resetForm">
          {{ editingId ? "切换到新建" : "重置表单" }}
        </button>
      </div>

      <div v-if="error" class="panel-soft error-box">{{ error }}</div>
      <div v-if="success" class="panel-soft success-box">{{ success }}</div>

      <div class="stack">
        <label>稳定 ID</label>
        <input v-model="form.id" :disabled="Boolean(editingId)" placeholder="例如：system-glm-4_6" />

        <label>展示名称</label>
        <input v-model="form.label" placeholder="例如：glm-4.6" />

        <label>Base URL</label>
        <input v-model="form.base_url" placeholder="https://api.example.com/v1" autocomplete="off" />

        <label>模型名</label>
        <input v-model="form.model" placeholder="glm-4.6 / gpt-4o-mini" autocomplete="off" />

        <label>API Key</label>
        <div class="row">
          <input
            v-model="form.api_key"
            :type="revealApiKey ? 'text' : 'password'"
            style="flex: 1"
            :placeholder="editingId ? '留空表示沿用当前密钥' : 'sk-...'"
            autocomplete="new-password"
          />
          <button class="secondary" type="button" @click="revealApiKey = !revealApiKey">
            {{ revealApiKey ? "隐藏" : "显示" }}
          </button>
        </div>

        <div class="choice-grid single-row">
          <label class="row switch-row">
            <input v-model="form.enabled" type="checkbox" />
            <span>启用</span>
          </label>
          <label class="row switch-row">
            <input v-model="form.is_default" type="checkbox" />
            <span>设为默认</span>
          </label>
        </div>

        <label>排序</label>
        <input v-model.number="form.sort_order" type="number" min="0" step="1" />

        <div class="row">
          <button class="primary" :disabled="saving" @click="submitForm">
            {{ saving ? "保存中..." : editingId ? "保存模型" : "新增模型" }}
          </button>
          <button class="secondary" :disabled="loading" @click="loadCatalog">
            {{ loading ? "刷新中..." : "刷新目录" }}
          </button>
        </div>
      </div>
    </div>

    <div class="panel col-7">
      <div class="toolbar" style="margin-bottom: 10px">
        <p class="section-title">模型目录与兼容说明</p>
        <span class="muted">默认模型：{{ defaultModelId || "-" }}</span>
      </div>

      <div class="panel-soft" style="margin-bottom: 12px">
        {{ legacySummary }}
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>名称</th>
              <th>模型</th>
              <th>Base URL</th>
              <th>状态</th>
              <th>默认</th>
              <th>排序</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in catalog" :key="item.id">
              <td class="mono">{{ item.id }}</td>
              <td>{{ item.label }}</td>
              <td>{{ item.model }}</td>
              <td class="mono url-cell">{{ item.base_url }}</td>
              <td>
                <span class="badge" :class="{ 'badge-off': !item.enabled }">
                  {{ item.enabled ? "启用" : "禁用" }}
                </span>
              </td>
              <td>{{ item.is_default ? "是" : "-" }}</td>
              <td>{{ item.sort_order }}</td>
              <td class="actions-cell">
                <button class="secondary" @click="editItem(item)">编辑</button>
                <button class="secondary" @click="moveItem(item, -1)" :disabled="index === 0">上移</button>
                <button
                  class="secondary"
                  @click="moveItem(item, 1)"
                  :disabled="index === catalog.length - 1"
                >
                  下移
                </button>
                <button class="secondary" @click="setDefault(item)" :disabled="item.is_default || !item.enabled">
                  设默认
                </button>
                <button class="warn" @click="toggleEnabled(item)">
                  {{ item.enabled ? "禁用" : "启用" }}
                </button>
              </td>
            </tr>
            <tr v-if="catalog.length === 0">
              <td colspan="8" style="text-align: center; opacity: 0.8">暂无模型目录数据</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.error-box {
  margin-bottom: 10px;
  border-color: #8d2f3b;
  color: #f4a7b5;
}

.success-box {
  margin-bottom: 10px;
  border-color: #1f6f4f;
  color: #91f0c7;
}

.single-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.switch-row {
  align-items: center;
}

.url-cell {
  max-width: 220px;
  white-space: normal;
  word-break: break-all;
}

.badge-off {
  background: #3a1f26;
  color: #ffb3c2;
}

@media (max-width: 960px) {
  .single-row {
    grid-template-columns: 1fr;
  }
}
</style>
