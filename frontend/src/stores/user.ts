import { defineStore } from "pinia";
import { computed, ref, watch } from "vue";

interface User {
  id?: number;
  name?: string;
  handle?: string;
  role?: string;
  avatar?: string;
  api_key?: string;
  is_system?: boolean;
  owner_id?: number;
  token?: string;
  expire?: string;
}

const STORAGE_KEY = "user";

function normalizeStoredUser(parsed: any): User | null {
  if (!parsed || typeof parsed !== "object") return null;
  const candidate = parsed.user && typeof parsed.user === "object" ? parsed.user : parsed;
  if (!candidate?.token) return null;
  return candidate as User;
}

function loadFromStorage(): User | null {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) return null;

    const parsed = JSON.parse(saved);
    const normalized = normalizeStoredUser(parsed);
    if (!normalized) return null;

    // Only enforce expiry when it exists.
    if (normalized.expire && new Date(normalized.expire) <= new Date()) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }

    return normalized;
  } catch (e) {
    console.error("Failed to load user from localStorage", e);
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export const useUserStore = defineStore("user", () => {
  const user = ref<User | null>(loadFromStorage());

  const isLoggedIn = computed(() => {
    if (!user.value?.token) return false;
    if (user.value.expire) {
      return new Date(user.value.expire) > new Date();
    }
    return true;
  });

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
    if (newUser) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newUser));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  };

  const logout = () => {
    user.value = null;
    localStorage.removeItem(STORAGE_KEY);
  };

  return {
    user,
    isLoggedIn,
    setUser,
    logout,
  };
});
