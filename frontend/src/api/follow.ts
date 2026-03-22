import type { ApiResponse, FollowWithQuestion, FollowWithUser, FollowerWithUser, PaginatedResponse, TargetType } from './types'
import request from './request'

// Execute follow/unfollow
export function executeFollow(data: {
  target_type: TargetType
  target_id: number
  action: boolean // true=follow, false=unfollow
}) {
  return request.post<ApiResponse>('/follow', data)
}

// Get following list (users you follow)
export function getFollowingList(targetType: TargetType = 4, cursor?: number, limit = 20) {
  return request.get<ApiResponse<PaginatedResponse<FollowWithUser>>>('/follow/following', {
    params: { target_type: targetType, cursor, limit },
  })
}

export function getUserFollowingList(userId: number, targetType: TargetType = 4, cursor?: number, limit = 20) {
  return request.get<ApiResponse<PaginatedResponse<FollowWithUser | FollowWithQuestion>>>(
    `/user/${userId}/following`,
    {
      params: { target_type: targetType, cursor, limit },
    },
  )
}

// Get followers list (users who follow you)
export function getFollowersList(cursor?: number, limit = 20) {
  return request.get<ApiResponse<PaginatedResponse<FollowerWithUser>>>('/follow/followers', {
    params: { cursor, limit },
  })
}

export function getUserFollowersList(userId: number, cursor?: number, limit = 20) {
  return request.get<ApiResponse<PaginatedResponse<FollowerWithUser>>>(
    `/user/${userId}/followers`,
    {
      params: { cursor, limit },
    },
  )
}
