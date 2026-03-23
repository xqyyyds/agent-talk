import type { ApiResponse, DebateHistoryItem, DebateStatus } from "./types";
import axios from "axios";

const debateRequest = axios.create({
  baseURL: "/agent-api",
  timeout: 180000,
});

export function startDebate(cycle_count?: number) {
  return debateRequest.post<ApiResponse>("/debate/start", { cycle_count });
}

export function stopDebate() {
  return debateRequest.post<ApiResponse>("/debate/stop");
}

export function getDebateStatus() {
  return debateRequest.get<DebateStatus>("/debate/status");
}

export function getDebateHistory(params: { limit?: number; offset?: number }) {
  return debateRequest.get<
    ApiResponse<{ total: number; items: DebateHistoryItem[] }>
  >("/debate/history", { params });
}
