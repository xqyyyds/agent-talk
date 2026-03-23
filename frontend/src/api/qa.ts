import type { ApiResponse } from "./types";
import axios from "axios";

const qaRequest = axios.create({
  baseURL: "/agent-api",
  timeout: 180000,
});

export function triggerManualAgentAnswers(questionId: number, agentIds: number[]) {
  return qaRequest.post<ApiResponse>("/qa/manual-answer", {
    question_id: questionId,
    agent_ids: agentIds,
  });
}
