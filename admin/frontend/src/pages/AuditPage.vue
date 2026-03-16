<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "../api";
import { formatBeijingDateTime } from "../utils/datetime";

const rows = ref<any[]>([]);

function formatDateTime(value: string | null | undefined): string {
  return formatBeijingDateTime(value ?? null);
}

async function load() {
  const { data } = await api.auditLogs(200);
  rows.value = data;
}

onMounted(load);
</script>

<template>
  <div class="panel">
    <div class="toolbar" style="margin-bottom: 10px">
      <p class="section-title">审计日志</p>
      <button class="secondary" @click="load">刷新</button>
    </div>

    <div class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>admin_id</th>
            <th>action</th>
            <th>target</th>
            <th>ip</th>
            <th class="time-cell">创建时间（北京时间）</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td class="mono">{{ row.id }}</td>
            <td class="mono">{{ row.admin_id }}</td>
            <td>{{ row.action }}</td>
            <td>{{ row.target_type }}#{{ row.target_id }}</td>
            <td>{{ row.ip || "-" }}</td>
            <td class="time-cell">{{ formatDateTime(row.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
