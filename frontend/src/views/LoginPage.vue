<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getUserInfo, login, register } from "../api/login";
import { useUserStore } from "../stores/user";

const isRegisterMode = ref(false);
const handle = ref("");
const password = ref("");
const confirmPassword = ref("");
const loading = ref(false);
const errorMessage = ref("");
const successMessage = ref("");
const router = useRouter();
const route = useRoute();
const userStore = useUserStore();

// 获取登录后应该跳转的页面
const redirectPath = (route.query.redirect as string) || "/";

async function handleLogin() {
  if (!handle.value || !password.value) {
    errorMessage.value = "请输入用户名和密码";
    return;
  }

  loading.value = true;
  errorMessage.value = "";

  // 登录前清除旧的用户数据
  localStorage.removeItem("user");

  try {
    const res = await login(handle.value, password.value);

    // 先保存 token 到 localStorage，确保后续请求能用
    const token = res.data.token;
    const userData = {
      expire: res.data.expire,
      token: token,
    };
    localStorage.setItem("user", JSON.stringify(userData));
    userStore.setUser(userData);

    // 获取用户详细信息（直接传入token，避免localStorage同步问题）
    try {
      const infoRes = await getUserInfo(token);
      if (infoRes.status === 200 && infoRes.data.data) {
        const fullUserData = {
          ...userData,
          id: infoRes.data.data.id,
          name: infoRes.data.data.name,
          handle: infoRes.data.data.handle,
          avatar: infoRes.data.data.avatar,
          role: infoRes.data.data.role,
        };
        localStorage.setItem("user", JSON.stringify(fullUserData));
        userStore.setUser(fullUserData);
      }
    } catch (infoError) {
      console.error("获取用户信息失败，但登录成功", infoError);
      // 登录已成功，即使获取用户信息失败也继续
    }

    router.push(redirectPath);
  } catch (e: any) {
    // 登录失败
    localStorage.removeItem("user");
    if (e.response?.status === 401) {
      errorMessage.value = "用户名或密码错误";
    } else {
      errorMessage.value =
        e.response?.data?.message || e.message || "登录请求失败";
    }
  } finally {
    loading.value = false;
  }
}

async function handleRegister() {
  if (!handle.value || !password.value || !confirmPassword.value) {
    errorMessage.value = "请填写所有字段";
    return;
  }

  if (password.value !== confirmPassword.value) {
    errorMessage.value = "两次输入的密码不一致";
    return;
  }

  if (handle.value.length < 3 || handle.value.length > 50) {
    errorMessage.value = "用户名长度应在3-50个字符之间";
    return;
  }

  if (password.value.length < 6) {
    errorMessage.value = "密码长度至少为6个字符";
    return;
  }

  loading.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    const res = await register(handle.value, password.value);
    if (res.data.code === 200 && res.data.data) {
      // 注册成功后自动登录
      userStore.setUser({
        expire: res.data.data.expire,
        token: res.data.data.token,
        id: res.data.data.id,
        name: res.data.data.name,
        handle: res.data.data.handle,
        avatar: res.data.data.avatar,
        role: res.data.data.role,
      });
      router.push(redirectPath);
    }
  } catch (e: any) {
    errorMessage.value = e.response?.data?.message || e.message || "注册失败";
  } finally {
    loading.value = false;
  }
}

function toggleMode() {
  isRegisterMode.value = !isRegisterMode.value;
  errorMessage.value = "";
  successMessage.value = "";
  password.value = "";
  confirmPassword.value = "";
}

function handleSubmit() {
  if (isRegisterMode.value) {
    handleRegister();
  } else {
    handleLogin();
  }
}
</script>

<template>
  <div class="min-h-[calc(100vh-140px)] flex items-center justify-center p-4">
    <div
      class="max-w-md w-full animate-fade-in-up rounded-2xl bg-white p-8 shadow-[0_8px_30px_rgb(0,0,0,0.06)] ring-1 ring-gray-100"
    >
      <div class="mb-10 text-center">
        <h2 class="text-2xl text-gray-800 font-bold">
          {{ isRegisterMode ? "创建账号" : "欢迎回来" }}
        </h2>
        <p class="mt-2 text-sm text-gray-500">
          {{ isRegisterMode ? "注册 AgentTalk 账号" : "登录 AgentTalk 账号" }}
        </p>
      </div>

      <form class="space-y-6" autocomplete="on" @submit.prevent="handleSubmit">
        <div>
          <label
            for="handle"
            class="mb-1 block text-sm text-gray-700 font-medium"
            >用户名</label
          >
          <div class="relative">
            <input
              id="handle"
              v-model="handle"
              type="text"
              name="username"
              required
              autocomplete="section-login username"
              autocapitalize="none"
              spellcheck="false"
              class="block w-full border border-gray-200 rounded-lg bg-gray-50 px-4 py-3 text-sm outline-none transition-all focus:border-[#00AEEC] focus:bg-white focus:ring-1 focus:ring-[#00AEEC]"
              placeholder="请输入用户名"
            />
          </div>
        </div>

        <div>
          <label
            for="password"
            class="mb-1 block text-sm text-gray-700 font-medium"
            >密码</label
          >
          <div class="relative">
            <input
              id="password"
              v-model="password"
              type="password"
              name="password"
              required
              :autocomplete="
                isRegisterMode
                  ? 'section-register new-password'
                  : 'section-login current-password'
              "
              class="block w-full border border-gray-200 rounded-lg bg-gray-50 px-4 py-3 text-sm outline-none transition-all focus:border-[#00AEEC] focus:bg-white focus:ring-1 focus:ring-[#00AEEC]"
              placeholder="请输入密码"
            />
          </div>
        </div>

        <!-- Register-only fields -->
        <template v-if="isRegisterMode">
          <div>
            <label
              for="confirmPassword"
              class="mb-1 block text-sm text-gray-700 font-medium"
              >确认密码</label
            >
            <div class="relative">
              <input
                id="confirmPassword"
                v-model="confirmPassword"
                type="password"
                name="confirmPassword"
                required
                autocomplete="section-register new-password"
                class="block w-full border border-gray-200 rounded-lg bg-gray-50 px-4 py-3 text-sm outline-none transition-all focus:border-[#00AEEC] focus:bg-white focus:ring-1 focus:ring-[#00AEEC]"
                placeholder="请再次输入密码"
              />
            </div>
          </div>
        </template>

        <Transition
          enter-active-class="transition-all duration-300 ease-out"
          enter-from-class="opacity-0 -translate-y-4 max-h-0"
          enter-to-class="opacity-100 translate-y-0 max-h-20"
          leave-active-class="transition-all duration-200 ease-in"
          leave-from-class="opacity-100 translate-y-0 max-h-20"
          leave-to-class="opacity-0 -translate-y-4 max-h-0"
        >
          <div v-if="errorMessage || successMessage">
            <div
              v-if="errorMessage"
              class="rounded-lg bg-red-50 p-3 text-sm text-red-500"
            >
              {{ errorMessage }}
            </div>
            <div
              v-if="successMessage"
              class="rounded-lg bg-green-50 p-3 text-sm text-green-600"
            >
              {{ successMessage }}
            </div>
          </div>
        </Transition>

        <button
          type="submit"
          :disabled="loading"
          class="w-full flex items-center justify-center rounded-lg bg-[#00AEEC] px-4 py-3 text-sm text-white font-semibold shadow-md transition-all disabled:cursor-not-allowed hover:bg-[#009bd1] disabled:opacity-70 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#00AEEC]"
        >
          <span
            v-if="loading"
            class="mr-2 inline-block h-4 w-4 animate-spin border-2 border-current border-t-transparent rounded-full"
          />
          {{
            loading
              ? isRegisterMode
                ? "注册中..."
                : "登录中..."
              : isRegisterMode
                ? "立即注册"
                : "立即登录"
          }}
        </button>
      </form>

      <div class="mt-6 text-center text-sm text-gray-500">
        {{ isRegisterMode ? "已有账号？" : "还没有账号？" }}
        <a
          href="#"
          class="text-[#00AEEC] font-medium hover:text-[#009bd1] hover:underline"
          @click.prevent="toggleMode"
        >
          {{ isRegisterMode ? "立即登录" : "立即注册" }}
        </a>
      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-fade-in-up {
  animation: fadeInUp 0.5s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
