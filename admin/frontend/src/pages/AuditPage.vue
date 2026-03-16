<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "../api";

const rows = ref<any[]>([]);

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
            <th class="time-cell">created_at</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td class="mono">{{ row.id }}</td>
            <td class="mono">{{ row.admin_id }}</td>
            <td>{{ row.action }}</td>
            <td>{{ row.target_type }}#{{ row.target_id }}</td>
            <td>{{ row.ip || "-" }}</td>
            <td class="time-cell">{{ row.created_at }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
