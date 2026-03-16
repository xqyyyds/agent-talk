import type {
  ApiResponse,
  PaginatedResponse,
  QuestionWithStats,
} from "./types";
import request from "./request";

// Get question list
export function getQuestionList(params: {
  cursor?: number;
  limit?: number;
  tag_id?: number;
  type?: "qa" | "debate";
}) {
  return request.get<ApiResponse<PaginatedResponse<QuestionWithStats>>>(
    "/question/list",
    { params },
  );
}

// Get question detail
export function getQuestionDetail(questionId: number) {
  return request.get<ApiResponse<QuestionWithStats>>(`/question/${questionId}`);
}

// Create question
export function createQuestion(data: {
  title: string;
  content: string;
  tag_ids?: number[];
  type?: "qa" | "debate";
}) {
  return request.post<ApiResponse>("/question", data);
}

// Update question
export function updateQuestion(
  questionId: number,
  data: {
    title?: string;
    content?: string;
    tag_ids?: number[];
  },
) {
  return request.put<ApiResponse>(`/question/${questionId}`, data);
}

// Delete question
export function deleteQuestion(questionId: number) {
  return request.delete<ApiResponse>(`/question/${questionId}`);
}
