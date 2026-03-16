/**
 * Agent API 客户端
 */
import request from "./request";
import type {
  CreateAgentRequest,
  UpdateAgentRequest,
  AgentResponse,
  AgentListResponse,
} from "./types";

interface ApiResponse<T> {
  code: number;
  message?: string;
  data?: T;
}

/**
 * 获取 Agent 列表（分页）
 */
export function getAgents(params?: {
  page?: number;
  page_size?: number;
  is_system?: boolean;
}) {
  return request.get<ApiResponse<AgentListResponse>>("/agents", { params });
}

/**
 * 获取我的 Agent 列表
 */
export function getMyAgents() {
  // DEBUG: 检查 localStorage 和 token
  const userData = localStorage.getItem("user");
  console.log("[getMyAgents] localStorage user:", userData);
  if (userData) {
    try {
      const parsed = JSON.parse(userData);
      console.log(
        "[getMyAgents] parsed token:",
        parsed.token ? "exists" : "missing",
      );
    } catch (e) {
      console.error("[getMyAgents] parse error:", e);
    }
  }
  return request.get<ApiResponse<AgentResponse[]>>("/agents/my");
}

/**
 * 获取 Agent 详情
 */
export function getAgent(id: number) {
  return request.get<ApiResponse<AgentResponse>>(`/agents/${id}`);
}

/**
 * 创建 Agent
 */
export function createAgent(data: CreateAgentRequest) {
  return request.post<ApiResponse<AgentResponse>>("/agents", data);
}

/**
 * 更新 Agent
 */
export function updateAgent(id: number, data: UpdateAgentRequest) {
  return request.put<ApiResponse<AgentResponse>>(`/agents/${id}`, data);
}

/**
 * 删除 Agent
 */
export function deleteAgent(id: number) {
  return request.delete<ApiResponse<void>>(`/agents/${id}`);
}
