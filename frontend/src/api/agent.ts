/**
 * Agent API 客户端
 */
import request from "./request";
import type {
  CreateAgentRequest,
  UpdateAgentRequest,
  AgentResponse,
  AgentListResponse,
  AgentModelOptionsResponse,
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
  owner_id?: number;
}) {
  return request.get<ApiResponse<AgentListResponse>>("/agents", { params });
}

/**
 * 获取我的 Agent 列表
 */
export function getMyAgents() {
  return request.get<ApiResponse<AgentResponse[]>>("/agents/my");
}

/**
 * 获取 Agent 详情
 */
export function getAgent(id: number) {
  return request.get<ApiResponse<AgentResponse>>(`/agents/${id}`);
}

/**
 * 获取 Agent 可选模型
 */
export function getAgentModelOptions() {
  return request.get<ApiResponse<AgentModelOptionsResponse>>("/agents/model-options");
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
