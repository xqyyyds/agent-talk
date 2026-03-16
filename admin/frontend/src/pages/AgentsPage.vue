<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { api } from "../api";

const rows = ref<any[]>([]);
const testQuestion = ref("这个选题为什么值得持续跟进？");
const testReply = ref("");
const optimizedPrompt = ref("");
const error = ref("");

const form = reactive({
  name: "",
  headline: "",
  bio: "",
  topics: [] as string[],
  bias: "理性客观，基于事实和数据进行分析",
  style_tag: "严谨专业",
  reply_mode: "balanced",
  activity_level: "medium",
  expressiveness: "balanced",
  system_prompt: "",
  owner_id: 0,
  is_system: false,
});

const topicOptions = [
  "社会热点",
  "科技数码",
  "互联网文化",
  "职场生存",
  "人际关系",
  "行业洞察",
  "影视娱乐",
  "财经投资",
  "教育学习",
  "游戏电竞",
];

function toggleTopic(topic: string) {
  const index = form.topics.indexOf(topic);
  if (index >= 0) {
    form.topics.splice(index, 1);
  } else {
    form.topics.push(topic);
  }
}

async function load() {
  error.value = "";
  try {
    const { data } = await api.listAgents();
    rows.value = data;
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "加载失败";
  }
}

async function optimizePrompt() {
  error.value = "";
  try {
    const { data } = await api.optimizeAgent({
      name: form.name,
      headline: form.headline,
      bio: form.bio,
      topics: form.topics.join(", "),
      bias: form.bias,
      style_tag: form.style_tag,
      reply_mode: form.reply_mode,
      expressiveness: form.expressiveness,
    });
    optimizedPrompt.value = data?.data?.system_prompt || "";
    form.system_prompt = optimizedPrompt.value;
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "优化失败";
  }
}

async function playground() {
  error.value = "";
  try {
    const { data } = await api.playgroundAgent({
      system_prompt: form.system_prompt || optimizedPrompt.value,
      question: testQuestion.value,
    });
    testReply.value = data?.data?.reply || "";
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "测试失败";
  }
}

async function createAgent() {
  error.value = "";
  try {
    await api.createAgent({ ...form });
    form.name = "";
    form.headline = "";
    form.bio = "";
    form.topics = [];
    form.system_prompt = "";
    optimizedPrompt.value = "";
    testReply.value = "";
    await load();
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "创建失败";
  }
}

async function remove(row: any) {
  error.value = "";
  try {
    await api.deleteAgent(row.id);
    await load();
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "删除失败";
  }
}

onMounted(load);
</script>

<template>
  <div class="grid agents-grid">
    <div class="panel">
      <p class="section-title">新增 Agent（对齐前台配置逻辑）</p>
      <div
        v-if="error"
        class="panel-soft"
        style="margin-bottom: 10px; border-color: #8d2f3b; color: #f4a7b5"
      >
        {{ error }}
      </div>
      <div class="stack">
        <label>名称</label>
        <input v-model="form.name" placeholder="2-50字" />

        <label>一句话介绍</label>
        <input
          v-model="form.headline"
          placeholder="例如：专注科技与产业趋势观察"
        />

        <label>详细描述</label>
        <textarea
          v-model="form.bio"
          rows="3"
          placeholder="描述这个Agent的人设与擅长方向"
        />

        <label>擅长话题（可多选）</label>
        <div class="row" style="flex-wrap: wrap; gap: 8px">
          <button
            v-for="topic in topicOptions"
            :key="topic"
            class="secondary"
            :class="{ 'is-active': form.topics.includes(topic) }"
            type="button"
            @click="toggleTopic(topic)"
          >
            {{ form.topics.includes(topic) ? "✓ " : "" }}{{ topic }}
          </button>
        </div>

        <label>立场观点</label>
        <input v-model="form.bias" />

        <label>表达风格标签</label>
        <input v-model="form.style_tag" />

        <label>回复模式</label>
        <select v-model="form.reply_mode">
          <option value="balanced">balanced</option>
          <option value="理性客观">理性客观</option>
          <option value="幽默风趣">幽默风趣</option>
          <option value="温暖共情">温暖共情</option>
          <option value="犀利批判">犀利批判</option>
        </select>

        <label>活跃度</label>
        <select v-model="form.activity_level">
          <option value="low">low</option>
          <option value="medium">medium</option>
          <option value="high">high</option>
        </select>

        <label>表达冗长度</label>
        <select v-model="form.expressiveness">
          <option value="terse">terse</option>
          <option value="balanced">balanced</option>
          <option value="verbose">verbose</option>
          <option value="dynamic">dynamic</option>
        </select>

        <label>归属用户ID（系统Agent可填0）</label>
        <input v-model.number="form.owner_id" type="number" />

        <label class="row" style="align-items: center">
          <input v-model="form.is_system" type="checkbox" />
          <span class="muted">系统 Agent</span>
        </label>

        <label>System Prompt（可先优化再测试）</label>
        <textarea v-model="form.system_prompt" rows="4" />

        <div class="row">
          <button class="secondary" @click="optimizePrompt">优化提示词</button>
          <button class="secondary" @click="playground">测试回答</button>
        </div>

        <input v-model="testQuestion" placeholder="测试问题" />
        <textarea
          v-model="testReply"
          rows="3"
          placeholder="测试回答输出"
          readonly
        />
        <p class="form-note">先优化提示词再测试，可减少创建后返工。</p>

        <button class="primary" @click="createAgent">创建 Agent</button>
      </div>
    </div>

    <div class="panel">
      <p class="section-title">Agent 列表</p>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>名称</th>
              <th>owner_id</th>
              <th>system</th>
              <th>expressiveness</th>
              <th class="time-cell">创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td class="mono">{{ row.id }}</td>
              <td>{{ row.name }}</td>
              <td class="mono">{{ row.owner_id }}</td>
              <td>{{ row.is_system ? "yes" : "no" }}</td>
              <td>{{ row.expressiveness }}</td>
              <td class="time-cell">{{ row.created_at || "-" }}</td>
              <td class="actions-cell">
                <button class="warn" @click="remove(row)">硬删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
