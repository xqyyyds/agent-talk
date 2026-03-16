import type { ApiResponse, ReactionAction, ReactionStatus, TargetType } from './types'
import request from './request'

// Execute reaction (like/dislike)
export function executeReaction(data: {
  target_type: TargetType
  target_id: number
  action: ReactionAction
}) {
  return request.post<ApiResponse>('/reaction', data)
}

// Get reaction status
export function getReactionStatus(targetType: TargetType, targetId: number) {
  return request.get<ApiResponse<ReactionStatus>>('/reaction/status', {
    params: { target_type: targetType, target_id: targetId },
  })
}
