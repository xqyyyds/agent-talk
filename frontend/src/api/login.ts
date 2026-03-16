import request from "./request";

interface LoginResponse {
  code: number;
  token?: string;
  message?: string;
  expire?: string;
}

export function login(handle: string, password: string) {
  return request.post<LoginResponse>("/login", {
    handle,
    password,
  });
}

interface RegisterResponse {
  code: number;
  message?: string;
  data?: {
    id: number;
    name: string;
    handle: string;
    role: string;
    avatar: string;
    token: string;
    expire: string;
  };
}

export function register(handle: string, password: string) {
  return request.post<RegisterResponse>("/register", {
    handle,
    password,
  });
}

interface LogoutResponse {
  code: number;
  message?: string;
}

export function logout() {
  return request.post<LogoutResponse>("/auth/logout");
}

interface UserInfoResponse {
  code: number;
  data?: {
    id: number;
    name: string;
    handle?: string;
    role: string;
    avatar: string;
    expire: string;
  };
  message?: string;
}
export function getUserInfo(token?: string) {
  const config = token ? { headers: { Authorization: `Bearer ${token}` } } : {};
  return request.get<UserInfoResponse>("/user/info", config);
}
