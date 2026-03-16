import type { AnswerInCollectionWithStats, ApiResponse, Collection, PaginatedResponse } from './types'
import request from './request'

// Create collection
export function createCollection(name: string) {
  return request.post<ApiResponse<Collection>>('/collection', { name })
}

// Get collection list
export function getCollectionList() {
  return request.get<ApiResponse<Collection[]>>('/collection/list')
}

// Add answer to collection
export function addToCollection(collectionId: number, answerId: number) {
  return request.post<ApiResponse>('/collection/item', {
    collection_id: collectionId,
    answer_id: answerId,
  })
}

// Remove answer from collection
export function removeFromCollection(collectionId: number, answerId: number) {
  return request.delete<ApiResponse>('/collection/item', {
    params: { collection_id: collectionId, answer_id: answerId },
  })
}

// Get collection items
export function getCollectionItems(collectionId: number, cursor?: number, limit = 10) {
  return request.get<ApiResponse<PaginatedResponse<AnswerInCollectionWithStats>>>('/collection/items', {
    params: { collection_id: collectionId, cursor, limit },
  })
}

// Delete collection
export function deleteCollection(collectionId: number) {
  return request.delete<ApiResponse>(`/collection/${collectionId}`)
}
