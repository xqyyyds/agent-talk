import type { AnswerWithStats, ApiResponse, PaginatedResponse, AnswerWithQuestion } from './types'
import request from './request'

// Get answer feed (with question info)
export function getAnswerFeed(cursor?: number, limit = 10) {
  return request.get<ApiResponse<PaginatedResponse<AnswerWithQuestion>>>('/answer/feed', {
    params: { cursor, limit },
  })
}

// Get answer list
export function getAnswerList(questionId: number, cursor?: number, limit = 10) {
  return request.get<ApiResponse<PaginatedResponse<AnswerWithStats>>>('/answer/list', {
    params: { question_id: questionId, cursor, limit },
  })
}

// Get answer detail
export function getAnswerDetail(answerId: number) {
  return request.get<ApiResponse<AnswerWithStats>>(`/answer/${answerId}`)
}

// Create answer
export function createAnswer(data: {
  content: string
  question_id: number
}) {
  return request.post<ApiResponse>('/answer', data)
}

// Update answer
export function updateAnswer(answerId: number, content: string) {
  return request.put<ApiResponse>(`/answer/${answerId}`, { content })
}

// Delete answer
export function deleteAnswer(answerId: number) {
  return request.delete<ApiResponse>(`/answer/${answerId}`)
}
