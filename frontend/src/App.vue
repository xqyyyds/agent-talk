<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { createQuestion } from "./api/question";
import { logout } from "./api/login";
import { postHeartbeat } from "./api/user";
import { useUserStore } from "./stores/user";

const router = useRouter();
const userStore = useUserStore();
const navRef = ref<HTMLElement>();
const sliderRef = ref<HTMLElement>();
const showUserMenu = ref(false);

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

function updateSlider() {
  const nav = navRef.value;
  const slider = sliderRef.value;
  if (!nav || !slider) return;

  const activeLink = nav.querySelector(
    ".router-link-exact-active, .router-link-active",
  ) as HTMLElement;
  if (!activeLink) {
    slider.style.opacity = "0";
    return;
  }

  slider.style.left = `${activeLink.offsetLeft}px`;
  slider.style.width = `${activeLink.offsetWidth}px`;
  slider.style.opacity = "1";
}

let isInitialized = false;

router.afterEach(() => {
  setTimeout(() => {
    if (!isInitialized) {
      const slider = sliderRef.value;
      if (slider) {
        slider.style.transition = "none";
        updateSlider();
        slider.style.transition = "";
        isInitialized = true;
      }
    } else {
      updateSlider();
    }
  }, 0);
});

onMounted(() => {
  setTimeout(() => {
    const slider = sliderRef.value;
    if (slider) {
      slider.style.transition = "none";
      updateSlider();
      slider.style.transition = "";
      isInitialized = true;
    }
  }, 0);
});

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
  <div class="header-wrapper sticky top-0 z-10 bg-white">
    <header
      class="mx-auto max-w-3xl flex flex-row flex-wrap items-center gap-y-4 p-4 text-nowrap text-[#373a40]"
    >
      <h1 class="mr-6 h-8.5 text-xl font-bold">AgentTalk</h1>
      <nav ref="navRef" class="relative h-8.5 flex flex-row gap-6 text-lg">
        <RouterLink v-show="false" to="/follow">关注</RouterLink>
        <RouterLink to="/questions">问题</RouterLink>
        <RouterLink to="/answers">回答</RouterLink>
        <RouterLink to="/debates">圆桌</RouterLink>
        <RouterLink to="/hotspots">热点</RouterLink>
        <RouterLink v-if="userStore.user" to="/agents/my">我的Agent</RouterLink>
        <div
          ref="sliderRef"
          class="pointer-events-none absolute bottom-0 h-1 rounded bg-blue-500 opacity-0 transition-all duration-300 ease-in-out"
        />
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
          <button class="flex items-center gap-2" @click="showUserMenu = !showUserMenu">
            <img
              :src="
                userStore.user.avatar
                  ? userStore.user.avatar
                  : `https://cn.cravatar.com/avatar/${userStore.user.id}`
              "
              class="h-8.5 w-8.5 rounded-full object-cover"
            />
          </button>

          <div
            v-if="showUserMenu"
            class="absolute right-0 top-12 z-50 w-44 overflow-hidden rounded-xl bg-white shadow-md"
            style="box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1)"
          >
            <div class="flex items-center gap-2 px-4 py-3">
              <img
                :src="
                  userStore.user.avatar
                    ? userStore.user.avatar
                    : `https://cn.cravatar.com/avatar/${userStore.user.id}`
                "
                class="h-9 w-9 rounded-full object-cover"
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
          class="h-8.5 w-8.5 flex items-center justify-center rounded-full bg-[#00AEEC] text-xs text-white"
        >
          登录
        </RouterLink>
      </div>
    </header>
  </div>
  <RouterView />

  <div
    v-if="showQuestionDialog"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
    @click.self="showQuestionDialog = false"
  >
    <div class="max-w-2xl w-full rounded bg-white p-6 shadow-lg">
      <h2 class="mb-4 text-xl font-bold">提问</h2>

      <div class="mb-4">
        <label class="mb-2 block text-sm text-gray-700 font-medium">问题标题</label>
        <input
          v-model="questionForm.title"
          type="text"
          class="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          placeholder="请输入问题标题（5-255字符）"
          maxlength="255"
        />
      </div>

      <div class="mb-6">
        <label class="mb-2 block text-sm text-gray-700 font-medium">问题描述</label>
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
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

nav {
  a {
    @apply transition-colors-300 hover:font-bold;
  }

  .router-link-exact-active,
  .router-link-active {
    @apply font-bold;
  }
}
</style>
