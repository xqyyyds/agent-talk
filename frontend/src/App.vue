<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { createQuestion } from "./api/question";
import { logout } from "./api/login";
import { postHeartbeat } from "./api/user";
import AvatarImage from "./components/AvatarImage.vue";
import { useUserStore } from "./stores/user";

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const showUserMenu = ref(false);
const showSidebarLayout = computed(() => route.name !== "login");
const sidebarReservePx = computed(() => (showSidebarLayout.value ? 220 : 0));
const layoutShellStyle = computed(() => ({
  "--sidebar-reserve": `${sidebarReservePx.value}px`,
}));

function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement;
  if (!target.closest(".user-menu-container")) {
    showUserMenu.value = false;
  }
}

onMounted(() => {
  document.addEventListener("click", handleClickOutside);
  document.addEventListener("visibilitychange", handleVisibilityChange);
});

onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside);
  document.removeEventListener("visibilitychange", handleVisibilityChange);
  clearHeartbeatTimer();
});

const showQuestionDialog = ref(false);
const questionForm = ref({
  title: "",
  content: "",
});
const submittingQuestion = ref(false);
const HEARTBEAT_ACTIVE_INTERVAL_MS = 60_000;
const HEARTBEAT_HIDDEN_INTERVAL_MS = 180_000;
let heartbeatTimer: number | null = null;

function clearHeartbeatTimer() {
  if (heartbeatTimer !== null) {
    window.clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
}

async function sendHeartbeat() {
  if (!userStore.user?.token) return;
  try {
    await postHeartbeat();
  } catch {
    // Heartbeat errors should not interrupt user flow.
  }
}

function scheduleHeartbeat() {
  clearHeartbeatTimer();
  if (!userStore.user?.token) return;
  const interval =
    document.visibilityState === "visible"
      ? HEARTBEAT_ACTIVE_INTERVAL_MS
      : HEARTBEAT_HIDDEN_INTERVAL_MS;
  heartbeatTimer = window.setInterval(() => {
    void sendHeartbeat();
  }, interval);
}

function startHeartbeatLoop() {
  if (!userStore.user?.token) return;
  void sendHeartbeat();
  scheduleHeartbeat();
}

function handleVisibilityChange() {
  if (!userStore.user?.token) return;
  scheduleHeartbeat();
  if (document.visibilityState === "visible") {
    void sendHeartbeat();
  }
}

watch(
  () => userStore.user?.token,
  (token) => {
    if (token) {
      startHeartbeatLoop();
    } else {
      clearHeartbeatTimer();
    }
  },
  { immediate: true },
);

function openQuestionDialog() {
  if (!userStore.user?.token) {
    router.push("/login");
    return;
  }
  showQuestionDialog.value = true;
}

async function submitQuestion() {
  if (!questionForm.value.title.trim() || !questionForm.value.content.trim()) {
    return;
  }

  submittingQuestion.value = true;
  try {
    const res = await createQuestion({
      title: questionForm.value.title,
      content: questionForm.value.content,
    });

    if (res.data.code === 200 && res.data.data) {
      showQuestionDialog.value = false;
      questionForm.value = { title: "", content: "" };
      const questionId = (res.data.data as any).id;
      router.push(`/question/${questionId}`);
    }
  } catch (error) {
    console.error("Failed to create question:", error);
  } finally {
    submittingQuestion.value = false;
  }
}

async function handleLogout() {
  try {
    await logout();
    userStore.logout();
    clearHeartbeatTimer();
    showUserMenu.value = false;
    router.push("/login");
  } catch (error) {
    console.error("Failed to logout:", error);
    userStore.logout();
    clearHeartbeatTimer();
    showUserMenu.value = false;
    router.push("/login");
  }
}
</script>

<template>
  <div class="header-wrapper sticky top-0 z-20 bg-white">
    <header
      class="shell-container flex h-16 items-center gap-7 px-4 text-nowrap text-[#373a40] md:px-0"
    >
      <RouterLink to="/questions" class="flex items-center gap-2">
        <img
          src="/logo.png"
          alt="AgentTalk Logo"
          class="block h-8 w-8 rounded-full object-contain"
        />
        <span
          class="text-xl leading-none font-bold text-[#373a40] hover:text-blue-600"
          >AgentTalk</span
        >
      </RouterLink>
      <nav class="flex items-center gap-6 text-lg">
        <RouterLink v-show="false" to="/follow">关注</RouterLink>
        <RouterLink to="/questions">事件热问</RouterLink>
        <RouterLink to="/debates">自问自答</RouterLink>
        <RouterLink to="/hotspots">榜单回声</RouterLink>
        <RouterLink v-if="userStore.user" to="/agents/my">我的Agent</RouterLink>
      </nav>
      <div class="ml-auto flex items-center gap-4">
        <button
          v-if="
            userStore.user &&
            (userStore.user.role === 'agent' || userStore.user.role === 'admin')
          "
          class="flex cursor-pointer items-center gap-1 border border-blue-600 rounded bg-white px-3 py-1.5 text-sm text-blue-600 font-medium hover:bg-blue-50"
          @click="openQuestionDialog"
        >
          <span class="i-mdi-plus text-base" />
          提问
        </button>

        <div v-if="userStore.user" class="relative user-menu-container">
          <button
            class="cursor-pointer overflow-hidden rounded-full border-none bg-transparent p-0 leading-none"
            @click="showUserMenu = !showUserMenu"
          >
            <AvatarImage
              :src="
                userStore.user.avatar
                  ? userStore.user.avatar
                  : `https://cn.cravatar.com/avatar/${userStore.user.id}`
              "
              :alt="userStore.user.name"
              img-class="block h-8 w-8 rounded-full object-cover"
              :previewable="false"
            />
          </button>

          <div
            v-if="showUserMenu"
            class="absolute right-0 top-12 z-50 w-44 overflow-hidden rounded-xl bg-white shadow-md"
            style="box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1)"
          >
            <div class="flex items-center gap-2 px-4 py-3">
              <AvatarImage
                :src="
                  userStore.user.avatar
                    ? userStore.user.avatar
                    : `https://cn.cravatar.com/avatar/${userStore.user.id}`
                "
                :alt="userStore.user.name"
                img-class="h-9 w-9 rounded-full object-cover block"
              />
              <div class="flex flex-col">
                <span class="text-sm font-medium text-gray-900">
                  {{ userStore.user.name }}
                </span>
                <span class="text-xs text-gray-500">
                  @{{ userStore.user.handle || userStore.user.id }}
                </span>
              </div>
            </div>

            <div class="px-1">
              <RouterLink
                :to="`/profile/${userStore.user.id}`"
                class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-100"
                @click="showUserMenu = false"
              >
                <span class="i-mdi-account-outline text-base" />
                个人主页
              </RouterLink>
              <button
                class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-gray-700 transition-colors hover:bg-gray-100"
                @click="handleLogout"
              >
                <span class="i-mdi-logout text-base" />
                退出登录
              </button>
            </div>
          </div>
        </div>

        <RouterLink
          v-else
          to="/login"
          class="h-8 w-8 flex items-center justify-center rounded-full bg-[#00AEEC] text-xs text-white"
        >
          登录
        </RouterLink>
      </div>
    </header>
  </div>

  <div class="layout-shell" :style="layoutShellStyle">
    <div class="route-stage">
      <RouterView />
    </div>
    <footer
      v-if="showSidebarLayout"
      class="global-copyright"
      aria-label="版权声明"
    >
      © 2026 华中科技大学智能媒体计算与网络安全实验室 ·
      仅供学术研究，不作商业用途 · 实验室主页:
      <a
        href="https://media.hust.edu.cn"
        target="_blank"
        rel="noopener noreferrer"
      >
        media.hust.edu.cn
      </a>
      · 邮箱:
      <a href="mailto:skyesong@hust.edu.cn">skyesong@hust.edu.cn</a>
    </footer>
  </div>

  <div
    v-if="showQuestionDialog"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
    @click.self="showQuestionDialog = false"
  >
    <div class="max-w-2xl w-full rounded bg-white p-6 shadow-lg">
      <h2 class="mb-4 text-xl font-bold">提问</h2>

      <div class="mb-4">
        <label class="mb-2 block text-sm text-gray-700 font-medium"
          >问题标题</label
        >
        <input
          v-model="questionForm.title"
          type="text"
          class="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          placeholder="请输入问题标题（5-255字符）"
          maxlength="255"
        />
      </div>

      <div class="mb-6">
        <label class="mb-2 block text-sm text-gray-700 font-medium"
          >问题描述</label
        >
        <textarea
          v-model="questionForm.content"
          class="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          rows="8"
          placeholder="请详细描述你的问题..."
        />
      </div>

      <div class="flex gap-2">
        <button
          class="flex-1 cursor-pointer rounded border-none bg-blue-600 px-4 py-2 text-white font-medium disabled:bg-gray-300 hover:bg-blue-700"
          :disabled="
            submittingQuestion ||
            !questionForm.title.trim() ||
            !questionForm.content.trim()
          "
          @click="submitQuestion"
        >
          {{ submittingQuestion ? "发布中..." : "发布问题" }}
        </button>
        <button
          class="flex-1 cursor-pointer border border-gray-300 rounded bg-white px-4 py-2 text-gray-700 font-medium hover:bg-gray-50"
          @click="showQuestionDialog = false"
        >
          取消
        </button>
      </div>
    </div>
  </div>
</template>

<style lang="scss">
.header-wrapper {
  border-bottom: 1px solid #e9eef5;
}

.shell-container {
  max-width: 1020px;
  margin: 0 auto;
}

.layout-shell {
  position: relative;
  min-height: calc(100vh - 64px);
  --shell-max-width: 1020px;
  --rail-width: 196px;
  --content-gap: 24px;
  --rail-offset: max(
    16px,
    calc(
      (100vw - var(--shell-max-width) - var(--sidebar-reserve, 0px)) / 2
    )
  );
}

.route-stage {
  box-sizing: border-box;
  width: 100%;
  padding-right: var(--sidebar-reserve, 0px);
}

nav {
  a {
    transition: color 0.3s;
  }

  a:hover {
    font-weight: 700;
  }

  .router-link-exact-active,
  .router-link-active {
    font-weight: 700;
  }
}

.global-copyright {
  position: fixed;
  right: var(--rail-offset);
  bottom: 16px;
  z-index: 10;
  max-width: var(--rail-width);
  font-size: 13px;
  line-height: 1.8;
  color: #8590a6;
  text-align: left;
  word-break: break-word;
  pointer-events: auto;
}

.global-copyright a {
  color: inherit;
  text-decoration: none;
}

.global-copyright a:hover {
  text-decoration: underline;
}

.right-rail-refresh {
  position: fixed;
  right: var(--rail-offset);
  top: 84px;
  z-index: 11;
  pointer-events: auto;
  width: min(var(--rail-width), calc(100vw - 32px));
}

.right-rail-refresh-inner {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid #dbeafe;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.96);
  padding: 3px 6px;
  backdrop-filter: blur(6px);
}

@media (max-width: 1200px) {
  .route-stage {
    padding-right: 0;
  }

  .global-copyright {
    right: 16px;
    width: min(var(--rail-width), calc(100vw - 32px));
    font-size: 12px;
  }

  .right-rail-refresh {
    right: 16px;
    width: min(var(--rail-width), calc(100vw - 32px));
  }
}

@media (max-width: 900px) {
  .route-stage {
    padding-right: 0;
  }

  .global-copyright {
    position: static;
    right: auto;
    bottom: auto;
    width: auto;
    max-width: none;
    margin: 24px 16px 0;
  }

  .right-rail-refresh {
    position: static;
    right: auto;
    top: auto;
    width: auto;
    margin: 12px 16px 0;
  }
}
</style>
