<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

const isLoginPage = computed(() => route.path === "/login");

const navItems = [
  { path: "/dashboard", label: "总览" },
  { path: "/admins", label: "管理员" },
  { path: "/users", label: "用户" },
  { path: "/agents", label: "Agent" },
  { path: "/content", label: "内容治理" },
  { path: "/ops", label: "运维控制" },
  { path: "/audit", label: "审计日志" },
];

type NavItem = { path: string; label: string };

function logout() {
  localStorage.removeItem("admin_token");
  router.push("/login");
}
</script>

<template>
  <router-view v-if="isLoginPage" />

  <div v-else class="admin-shell">
    <aside class="left-rail">
      <div class="brand">
        <div class="brand-dot" />
        <div>
          <h1>AgentTalk</h1>
          <p>Admin Command</p>
        </div>
      </div>

      <nav class="menu-list">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="menu-item"
          :class="{ active: route.path === item.path }"
        >
          {{ item.label }}
        </RouterLink>
      </nav>

      <button class="danger-ghost" @click="logout">退出登录</button>
    </aside>

    <main class="main-stage">
      <header class="top-strip">
        <div>
          <h2>
            {{
              navItems.find((item: NavItem) => item.path === route.path)
                ?.label || "后台"
            }}
          </h2>
          <p>实时管理平台状态与内容质量</p>
        </div>
        <div class="status-pill">LIVE</div>
      </header>
      <section class="view-wrap">
        <router-view />
      </section>
    </main>
  </div>
</template>
