<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "../api";

const router = useRouter();

const username = ref("superadmin");
const password = ref("ChangeMe123!");
const loading = ref(false);
const error = ref("");

async function submit() {
  loading.value = true;
  error.value = "";
  try {
    const { data } = await api.login(username.value, password.value);
    localStorage.setItem("admin_token", data.access_token);
    router.push("/dashboard");
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "登录失败，请检查用户名和密码";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h1>AgentTalk 管理后台</h1>
      <p>统一控制用户、内容、辩论与 Agent 运行状态</p>

      <div class="row" style="margin-top: 16px; flex-direction: column">
        <input v-model="username" placeholder="管理员用户名" />
        <input
          v-model="password"
          placeholder="密码"
          type="password"
          @keyup.enter="submit"
        />
      </div>

      <p v-if="error" class="error">{{ error }}</p>

      <div
        class="row"
        style="
          margin-top: 14px;
          justify-content: space-between;
          align-items: center;
        "
      >
        <span class="muted">登录后进入中控台</span>
        <button class="primary" :disabled="loading" @click="submit">
          {{ loading ? "登录中..." : "进入后台" }}
        </button>
      </div>
    </div>
  </div>
</template>
