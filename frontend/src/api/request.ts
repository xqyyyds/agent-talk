import axios from "axios";
import { useToast } from "vue-toastification";
import router from "../router";

const toast = useToast();

const service = axios.create({
  baseURL: "/api",
  timeout: 5000,
});

// 直接从 localStorage 读取 token
const getToken = (): string | null => {
  try {
    const saved = localStorage.getItem("user");
    if (saved) {
      const parsed = JSON.parse(saved);
      // 支持两种格式：
      // 1. 嵌套格式 {"user": {"token": "xxx"}} (Pinia persisted state)
      // 2. 直接格式 {"token": "xxx"}
      if (parsed.user && parsed.user.token) {
        return parsed.user.token;
      }
      if (parsed.token) {
        return parsed.token;
      }
    }
  } catch (e) {
    console.error("Failed to get token from localStorage", e);
  }
  return null;
};

service.interceptors.request.use(
  (config) => {
    // 登录和注册接口不需要带 token
    const noAuthUrls = ["/login", "/register"];
    const isNoAuthUrl = noAuthUrls.some((url) => config.url?.includes(url));

    console.log(
      `[Interceptor] URL: ${config.url}, isNoAuthUrl: ${isNoAuthUrl}`,
    );

    if (!isNoAuthUrl) {
      const token = getToken();
      console.log(`[Interceptor] Token exists: ${!!token}`);
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
        console.log(`[Interceptor] Set Authorization header for ${config.url}`);
      } else {
        console.log(`[Interceptor] No token for ${config.url}`);
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

service.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response) {
      const status = error.response.status;
      const message = error.response.data?.message || "请求失败";
      const requestUrl = String(error.config?.url || "");

      // 登录/注册接口的 401 不做特殊处理，由页面自己处理
      const isAuthUrl =
        error.config?.url?.includes("/login") ||
        error.config?.url?.includes("/register");
      const isHotspotOptional404 = requestUrl.includes("/hotspots/by-question/");

      if (status === 401 && !isAuthUrl) {
        toast.error("未授权，请重新登录");
        // 清除过期的用户数据
        localStorage.removeItem("user");
        router.push("/login");
      } else if (status === 403) {
        toast.error("没有权限访问");
      } else if (status === 404) {
        if (!isHotspotOptional404) {
          toast.error("请求的资源不存在");
        }
      } else if (status === 500) {
        toast.error("服务器错误，请稍后重试");
      } else {
        toast.error(message);
      }
    } else if (error.code === "ECONNABORTED") {
      toast.error("请求超时，请检查网络连接");
    } else {
      toast.error("网络错误，请检查网络连接");
    }

    return Promise.reject(error);
  },
);

export default service;
