/**
 * Python Agent 服务 API 客户端
 * 用于优化系统提示词和测试对话
 */
import axios from 'axios'
import type { OptimizeAgentRequest, OptimizeAgentResponse, PlaygroundRequest, PlaygroundResponse } from './types'

const PYTHON_AGENT_BASE_URL = import.meta.env.VITE_PYTHON_AGENT_URL || 'http://localhost:8001'

const pythonAgentClient = axios.create({
  baseURL: PYTHON_AGENT_BASE_URL,
  timeout: 60000, // 60秒，优化可能需要较长时间
  headers: {
    'Content-Type': 'application/json'
  }
})

/**
 * 优化 Agent 配置，生成专业的 System Prompt
 */
export async function optimizeAgentPrompt(request: OptimizeAgentRequest): Promise<OptimizeAgentResponse> {
  const response = await pythonAgentClient.post<OptimizeAgentResponse>('/agent/optimize', request)
  return response.data
}

/**
 * 测试 Agent 回答
 */
export async function playgroundChat(request: PlaygroundRequest): Promise<PlaygroundResponse> {
  const response = await pythonAgentClient.post<PlaygroundResponse>('/agent/playground', request)
  return response.data
}
