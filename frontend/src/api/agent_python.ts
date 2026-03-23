import axios from "axios";
import type {
  OptimizeAgentRequest,
  OptimizeAgentResponse,
  PlaygroundRequest,
  PlaygroundResponse,
} from "./types";

const pythonAgentClient = axios.create({
  // Always use same-origin proxy in browser.
  // Real target is resolved by frontend nginx: /agent-api -> agent_service:8001
  baseURL: "/agent-api",
  timeout: 180000,
  headers: {
    "Content-Type": "application/json",
  },
});

export async function optimizeAgentPrompt(
  request: OptimizeAgentRequest,
): Promise<OptimizeAgentResponse> {
  const response = await pythonAgentClient.post<OptimizeAgentResponse>(
    "/agent/optimize",
    request,
  );
  return response.data;
}

export async function playgroundChat(
  request: PlaygroundRequest,
): Promise<PlaygroundResponse> {
  const response = await pythonAgentClient.post<PlaygroundResponse>(
    "/agent/playground",
    request,
  );
  return response.data;
}
