import { defineStore } from "pinia";
import { computed, ref, watch } from "vue";

interface User {
  id?: number;
  name?: string; // 显示名称（所有人都有）
  handle?: string; // 登录账号（仅真人，Agent 为 undefined）
  role?: string;
  avatar?: string;

  // Agent 专属字段（可选）
  api_key?: string;
  is_system?: boolean;
  owner_id?: number;

  token?: string;
  expire?: string; // 改为 string 便于序列化
}

const STORAGE_KEY = "user";

export const useUserStore = defineStore("user", () => {
  // 从 localStorage 初始化
  const loadFromStorage = (): User | null => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        // 检查 token 是否过期
        if (parsed.expire && new Date(parsed.expire) > new Date()) {
          return parsed;
        }
        // Token 已过期，清除
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch (e) {
      console.error("Failed to load user from localStorage", e);
      localStorage.removeItem(STORAGE_KEY);
    }
    return null;
  };

  const user = ref<User | null>(loadFromStorage());

  // 检查是否已登录且 token 未过期
  const isLoggedIn = computed(() => {
    if (!user.value?.token) return false;
    if (user.value.expire) {
      return new Date(user.value.expire) > new Date();
    }
    return true;
  });

  // 监听 user 变化，自动保存到 localStorage
  watch(
    user,
    (newUser) => {
      if (newUser) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(newUser));
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    },
    { deep: true, immediate: true },
  );

  const setUser = (newUser: User | null) => {
    user.value = newUser;
    // 同步写入 localStorage，确保后续请求能立即获取 token
    if (newUser) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newUser));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  };

  const logout = () => {
    user.value = null;
    // 同步清除 localStorage
    localStorage.removeItem(STORAGE_KEY);
  };

  return {
    user,
    isLoggedIn,
    setUser,
    logout,
  };
});
