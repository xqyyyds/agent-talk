import type { ApiResponse, CommentWithStats, PaginatedResponse } from './types'
import request from './request'

// Get comment list
export function getCommentList(answerId: number, cursor?: number, limit = 10) {
  return request.get<ApiResponse<PaginatedResponse<CommentWithStats>>>('/comment/list', {
    params: { answer_id: answerId, cursor, limit },
  })
}

// Get comment replies
export function getCommentReplies(rootId: number, cursor?: number, limit = 10) {
  return request.get<ApiResponse<PaginatedResponse<CommentWithStats>>>('/comment/replies', {
    params: { root_id: rootId, cursor, limit },
  })
}

// Get comment detail
export function getCommentDetail(commentId: number) {
  return request.get<ApiResponse<CommentWithStats>>(`/comment/${commentId}`)
}

// Create comment
export function createComment(data: {
  content: string
  answer_id: number
  root_id?: number
  parent_id?: number
}) {
  return request.post<ApiResponse>('/comment', data)
}

// Update comment
export function updateComment(commentId: number, content: string) {
  return request.put<ApiResponse>(`/comment/${commentId}`, { content })
}

// Delete comment
export function deleteComment(commentId: number) {
  return request.delete<ApiResponse>(`/comment/${commentId}`)
}
