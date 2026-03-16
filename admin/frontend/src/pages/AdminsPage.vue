<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { api } from "../api";

const rows = ref<any[]>([]);
const form = reactive({ username: "", password: "" });
const currentAdminId = ref<number | null>(null);
const error = ref("");

async function loadMe() {
  const { data } = await api.me();
  currentAdminId.value = data?.id || null;
}

async function load() {
  error.value = "";
  try {
    const { data } = await api.listAdmins();
    rows.value = data;
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "加载失败";
  }
}

async function createAdmin() {
  if (!form.username || !form.password) return;
  error.value = "";
  try {
    await api.createAdmin({ username: form.username, password: form.password });
    form.username = "";
    form.password = "";
    await load();
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "创建失败";
  }
}

async function toggleStatus(row: any) {
  error.value = "";
  const target = row.status === "active" ? "disabled" : "active";
  try {
    await api.updateAdmin(row.id, { status: target });
    await load();
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "状态切换失败";
  }
}

async function remove(row: any) {
  error.value = "";
  try {
    await api.deleteAdmin(row.id);
    await load();
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "删除失败";
  }
}

onMounted(async () => {
  await loadMe();
  await load();
});
</script>

<template>
  <div class="grid">
    <div class="panel col-4">
      <p class="section-title">创建管理员</p>
      <div class="stack">
        <input v-model="form.username" placeholder="用户名" />
        <input v-model="form.password" placeholder="初始密码" type="password" />
        <button class="primary" @click="createAdmin">新增管理员</button>
      </div>
    </div>

    <div class="panel col-8">
      <p class="section-title">管理员列表</p>
      <div
        v-if="error"
        class="panel-soft"
        style="margin-bottom: 10px; border-color: #8d2f3b; color: #f4a7b5"
      >
        {{ error }}
      </div>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>用户名</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td class="mono">{{ row.id }}</td>
              <td>{{ row.username }}</td>
              <td>
                <span class="badge">{{ row.status }}</span>
              </td>
              <td class="actions-cell">
                <div class="row">
                  <button
                    class="secondary"
                    :disabled="row.id === currentAdminId"
                    @click="toggleStatus(row)"
                  >
                    {{
                      row.id === currentAdminId ? "不可切换自己" : "切换状态"
                    }}
                  </button>
                  <button class="warn" @click="remove(row)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
