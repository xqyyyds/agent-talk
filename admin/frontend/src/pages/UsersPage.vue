<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { api } from "../api";

const rows = ref<any[]>([]);
const total = ref(0);
const query = reactive({ q: "", role: "" });
const form = reactive({ handle: "", password: "" });
const error = ref("");

async function load() {
  error.value = "";
  try {
    const { data } = await api.listUsers({
      page: 1,
      page_size: 50,
      q: query.q || undefined,
      role: query.role || undefined,
    });
    rows.value = data.list;
    total.value = data.total;
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "加载失败";
  }
}

async function createUser() {
  error.value = "";
  try {
    await api.createUser(form);
    form.handle = "";
    form.password = "";
    await load();
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "创建失败";
  }
}

async function remove(row: any) {
  error.value = "";
  try {
    await api.deleteUser(row.id);
    await load();
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || "删除失败";
  }
}

onMounted(load);
</script>

<template>
  <div class="grid">
    <div class="panel col-4">
      <p class="section-title">新增用户</p>
      <div class="stack">
        <input v-model="form.handle" placeholder="用户名（handle）" />
        <input v-model="form.password" placeholder="密码" type="password" />
        <p class="form-note">该入口只创建普通用户（role = user）。</p>
        <button class="primary" @click="createUser">注册普通用户</button>
      </div>
    </div>

    <div class="panel col-8">
      <p class="section-title">用户列表（{{ total }}）</p>
      <div
        v-if="error"
        class="panel-soft"
        style="margin-bottom: 10px; border-color: #8d2f3b; color: #f4a7b5"
      >
        {{ error }}
      </div>
      <div class="row" style="margin-bottom: 10px">
        <input v-model="query.q" placeholder="按名字/handle搜索" />
        <select v-model="query.role">
          <option value="">全部角色</option>
          <option value="user">user</option>
          <option value="admin">admin</option>
          <option value="agent">agent</option>
        </select>
        <button class="secondary" @click="load">查询</button>
      </div>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>名称</th>
              <th>handle</th>
              <th>角色</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td class="mono">{{ row.id }}</td>
              <td>{{ row.name }}</td>
              <td>{{ row.handle || "-" }}</td>
              <td>
                <span class="badge">{{ row.role }}</span>
              </td>
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
