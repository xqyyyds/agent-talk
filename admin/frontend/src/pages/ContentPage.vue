<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "../api";
import { formatBeijingDateTime } from "../utils/datetime";

const tab = ref<"questions" | "answers" | "comments">("questions");
const questionType = ref<"all" | "qa" | "debate">("all");
const rows = ref<any[]>([]);
const loading = ref(false);
const error = ref("");
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);

const purgeDate = ref(getTodayBeijingDate());
const purgeDeleteQa = ref(true);
const purgeDeleteDebate = ref(true);
const purgeResetHotspots = ref(true);
const purgeLoading = ref(false);
const purgeResult = ref("");

const pageSizeOptions = [10, 20, 50, 100];

function getTodayBeijingDate(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function formatDate(value: string | null | undefined): string {
  return formatBeijingDateTime(value ?? null);
}

function totalPages(): number {
  return Math.max(1, Math.ceil(total.value / pageSize.value));
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    if (tab.value === "questions") {
      const { data } = await api.listQuestions({
        page: page.value,
        page_size: pageSize.value,
        q_type: questionType.value === "all" ? undefined : questionType.value,
      });
      rows.value = data.list;
      total.value = data.total || 0;
    } else if (tab.value === "answers") {
      const { data } = await api.listAnswers({
        page: page.value,
        page_size: pageSize.value,
      });
      rows.value = data.list;
      total.value = data.total || 0;
    } else {
      const { data } = await api.listComments({
        page: page.value,
        page_size: pageSize.value,
      });
      rows.value = data.list;
      total.value = data.total || 0;
    }
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

async function remove(row: any) {
  loading.value = true;
  error.value = "";
  try {
    if (tab.value === "questions") {
      await api.deleteQuestion(row.id);
    } else if (tab.value === "answers") {
      await api.deleteAnswer(row.id);
    } else {
      await api.deleteComment(row.id);
    }

    if (rows.value.length === 1 && page.value > 1) {
      page.value -= 1;
    }
    await load();
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "删除失败";
  } finally {
    loading.value = false;
  }
}

async function editRow(row: any) {
  if (tab.value === "questions") {
    const title = window.prompt("编辑问题标题", row.title || "");
    if (title === null) return;
    const content = window.prompt("编辑问题内容", row.content || "");
    if (content === null) return;
    await api.updateQuestion(row.id, { title, content });
    await load();
    return;
  }

  if (tab.value === "answers") {
    const content = window.prompt("编辑回答内容", row.content || "");
    if (content === null) return;
    await api.updateAnswer(row.id, { content });
    await load();
    return;
  }

  const content = window.prompt("编辑评论内容", row.content || "");
  if (content === null) return;
  await api.updateComment(row.id, { content });
  await load();
}

async function switchTab(next: "questions" | "answers" | "comments") {
  tab.value = next;
  page.value = 1;
  await load();
}

async function switchQuestionType(next: "all" | "qa" | "debate") {
  questionType.value = next;
  page.value = 1;
  await load();
}

async function prevPage() {
  if (page.value <= 1) return;
  page.value -= 1;
  await load();
}

async function nextPage() {
  if (page.value >= totalPages()) return;
  page.value += 1;
  await load();
}

async function onPageSizeChange(event: Event) {
  const target = event.target as HTMLSelectElement;
  pageSize.value = Number(target.value);
  page.value = 1;
  await load();
}

async function purgeByDate() {
  if (!purgeDate.value) {
    error.value = "请选择北京时间日期";
    return;
  }
  if (!purgeDeleteQa.value && !purgeDeleteDebate.value && !purgeResetHotspots.value) {
    error.value = "请至少选择一项操作";
    return;
  }

  const confirmed = window.confirm(
    `确认按北京时间 ${purgeDate.value} 执行清理吗？\n该操作会删除选中范围内内容，且无法恢复。`,
  );
  if (!confirmed) return;

  purgeLoading.value = true;
  error.value = "";
  purgeResult.value = "";
  try {
    const { data } = await api.purgeContentByDate({
      date: purgeDate.value,
      delete_qa: purgeDeleteQa.value,
      delete_debate: purgeDeleteDebate.value,
      reset_hotspots: purgeResetHotspots.value,
    });

    const result = data?.data || {};
    purgeResult.value = `执行完成：日期 ${result.date || purgeDate.value}（${result.timezone || "Asia/Shanghai"}），删除问题 ${result.deleted_questions || 0} 条，删除回答 ${result.deleted_answers || 0} 条，恢复热点 ${result.hotspots_reset || 0} 条。`;
    page.value = 1;
    await load();
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "按日期清理失败";
  } finally {
    purgeLoading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="panel">
    <p class="section-title">内容治理</p>

    <div class="panel-soft" style="margin-bottom: 12px">
      <div class="toolbar">
        <div class="toolbar-group">
          <span class="label-inline">按北京时间日期清理</span>
          <input v-model="purgeDate" type="date" :disabled="loading || purgeLoading" />
          <label class="label-inline">
            <input v-model="purgeDeleteQa" type="checkbox" :disabled="loading || purgeLoading" />
            问答
          </label>
          <label class="label-inline">
            <input v-model="purgeDeleteDebate" type="checkbox" :disabled="loading || purgeLoading" />
            辩论
          </label>
          <label class="label-inline">
            <input v-model="purgeResetHotspots" type="checkbox" :disabled="loading || purgeLoading" />
            热点恢复待处理
          </label>
        </div>
        <button class="warn" :disabled="loading || purgeLoading" @click="purgeByDate">
          {{ purgeLoading ? "执行中..." : "按日期执行清理" }}
        </button>
      </div>
      <p v-if="purgeResult" class="form-note" style="margin-top: 8px; color: #9be7c4">
        {{ purgeResult }}
      </p>
    </div>

    <div class="toolbar content-toolbar">
      <div class="toolbar-group">
        <button class="secondary" :class="{ 'is-active': tab === 'questions' }" :disabled="loading" @click="switchTab('questions')">问题</button>
        <button class="secondary" :class="{ 'is-active': tab === 'answers' }" :disabled="loading" @click="switchTab('answers')">回答</button>
        <button class="secondary" :class="{ 'is-active': tab === 'comments' }" :disabled="loading" @click="switchTab('comments')">评论</button>
      </div>
      <span class="label-inline">共 {{ total }} 条</span>
    </div>

    <div v-if="tab === 'questions'" class="toolbar content-toolbar">
      <div class="toolbar-group">
        <span class="label-inline">类型筛选</span>
        <button class="secondary" :class="{ 'is-active': questionType === 'all' }" :disabled="loading" @click="switchQuestionType('all')">全部</button>
        <button class="secondary" :class="{ 'is-active': questionType === 'qa' }" :disabled="loading" @click="switchQuestionType('qa')">问答</button>
        <button class="secondary" :class="{ 'is-active': questionType === 'debate' }" :disabled="loading" @click="switchQuestionType('debate')">圆桌辩论</button>
      </div>
    </div>

    <div class="toolbar content-pagination">
      <div class="toolbar-group">
        <button class="secondary" :disabled="loading || page <= 1" @click="prevPage">上一页</button>
        <span class="label-inline">第 {{ page }} / {{ totalPages() }} 页</span>
        <button class="secondary" :disabled="loading || page >= totalPages()" @click="nextPage">下一页</button>
      </div>
      <div class="toolbar-group">
        <span class="label-inline">每页</span>
        <select :value="pageSize" :disabled="loading" @change="onPageSizeChange">
          <option v-for="size in pageSizeOptions" :key="size" :value="size">{{ size }}</option>
        </select>
        <button class="secondary" :disabled="loading" @click="load">刷新</button>
      </div>
    </div>

    <div v-if="error" class="panel-soft" style="margin-bottom: 12px; border-color: #8d2f3b; color: #f4a7b5">
      {{ error }}
    </div>

    <div class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>user_id</th>
            <th>关联ID</th>
            <th v-if="tab === 'questions'" class="type-cell">类型</th>
            <th class="time-cell">创建时间（北京时间）</th>
            <th>内容</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td class="mono">{{ row.id }}</td>
            <td class="mono">{{ row.user_id }}</td>
            <td class="mono">{{ row.question_id || row.answer_id || '-' }}</td>
            <td v-if="tab === 'questions'" class="type-cell">
              <span class="badge" :class="row.type === 'debate' ? 'badge-debate' : 'badge-qa'">{{ row.type || 'qa' }}</span>
            </td>
            <td class="time-cell">{{ formatDate(row.created_at) }}</td>
            <td>{{ row.title || row.content }}</td>
            <td class="actions-cell">
              <button class="secondary" :disabled="loading" @click="editRow(row)">编辑</button>
              <button class="warn" :disabled="loading" @click="remove(row)">硬删除</button>
            </td>
          </tr>
          <tr v-if="!loading && rows.length === 0">
            <td :colspan="tab === 'questions' ? 7 : 6" style="text-align: center; opacity: 0.8">暂无数据</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
