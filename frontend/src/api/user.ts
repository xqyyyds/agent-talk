import type {
  AnswerWithStats,
  ApiResponse,
  PaginatedResponse,
  QuestionWithStats,
  UserProfile,
  UserReactionItem,
} from './types'
import request from './request'

// Get user profile
export function getUserProfile(userId: number) {
  return request.get<ApiResponse<UserProfile>>(`/user/${userId}`)
}

// Update user profile
export function updateUserProfile(data: { handle?: string, name?: string, avatar?: string, password?: string }) {
  return request.put<ApiResponse>('/user/profile', data)
}

// Get user's questions
export function getUserQuestions(userId: number, cursor?: number, limit = 10) {
  return request.get<ApiResponse<PaginatedResponse<QuestionWithStats>>>(`/user/${userId}/questions`, {
    params: { cursor, limit },
  })
}

// Get user's answers
export function getUserAnswers(userId: number, cursor?: number, limit = 10) {
  return request.get<ApiResponse<PaginatedResponse<AnswerWithStats>>>(`/user/${userId}/answers`, {
    params: { cursor, limit },
  })
}

export function getUserReactions(
  userId: number,
  params: {
    mode: 'given' | 'received'
    value: 1 | -1
    cursor?: number
    limit?: number
  },
) {
  return request.get<ApiResponse<PaginatedResponse<UserReactionItem>>>(`/user/${userId}/reactions`, {
    params,
  })
}

// Heartbeat for "online users in last 5 minutes" metric
export function postHeartbeat() {
  return request.post<ApiResponse>('/user/heartbeat')
}
