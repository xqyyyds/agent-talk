// Common response structure
export interface ApiResponse<T = any> {
  code: number;
  message?: string;
  data?: T;
}

// Pagination
export interface PaginatedResponse<T> {
  list: T[];
  next_cursor: number;
  has_more: boolean;
}

// User types
export interface User {
  id: number;
  name: string; // 显示名称（所有人都有）
  handle?: string; // 登录账号（仅真人，Agent 为 undefined）
  role: "user" | "admin" | "agent";
  avatar: string;

  // Agent 专属字段（可选）
  api_key?: string;
  is_system?: boolean;
  owner_id?: number;
  owner_name?: string;
  agent_topics?: string[];
  agent_style_tag?: string;

  is_following?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface UserStats {
  question_count: number;
  answer_count: number;
  follower_count: number;
  following_count: number;
  created_agent_count?: number;
  // Agent 专属统计：收到的赞/踩
  received_like_count?: number;
  received_dislike_count?: number;
  // 真人专属统计：给出的赞/踩、关注的问题数
  given_like_count?: number;
  given_dislike_count?: number;
  followed_question_count?: number;
}

export interface UserProfile extends User {
  stats: UserStats;
}

export interface UserReactionQuestion {
  id: number;
  title: string;
  content: string;
  created_at: string;
}

export interface UserReactionAnswer {
  id: number;
  content: string;
  question_id: number;
  question_title?: string;
  created_at: string;
}

export interface UserReactionItem {
  like_id: number;
  target_type: number;
  target_id: number;
  value: 1 | -1;
  created_at: string;
  question?: UserReactionQuestion;
  answer?: UserReactionAnswer;
}

// Question types
export interface Tag {
  id: number;
  name: string;
  description?: string;
  icon?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Question {
  id: number;
  title: string;
  content: string;
  user_id: number;
  user?: User;
  tags?: Tag[];
  created_at: string;
  updated_at: string;
  is_following?: boolean;
  type?: "qa" | "debate";
}

export interface QuestionStats {
  like_count: number;
  dislike_count: number;
  comment_count: number;
}

export interface QuestionWithStats extends Question {
  stats: QuestionStats;
  reaction_status?: 0 | 1 | 2;
}

// Answer types
export interface Answer {
  id: number;
  content: string;
  question_id: number;
  user_id: number;
  user?: User;
  created_at: string;
  updated_at: string;
}

export interface AnswerStats {
  like_count: number;
  dislike_count: number;
  comment_count: number;
}

export interface AnswerWithStats extends Answer {
  stats: AnswerStats;
  reaction_status?: 0 | 1 | 2;
}

// Answer with question info (for feed)
export interface AnswerWithQuestion extends AnswerWithStats {
  question?: QuestionWithStats;
}

// Comment types
export interface Comment {
  id: number;
  content: string;
  answer_id: number;
  user_id: number;
  user?: User;
  root_id?: number;
  parent_id?: number;
  parent_user?: User;
  created_at: string;
  updated_at: string;
}

export interface CommentStats {
  like_count: number;
  dislike_count: number;
  comment_count: number;
}

export interface CommentWithStats extends Comment {
  stats: CommentStats;
  reaction_status?: 0 | 1 | 2;
  replies?: CommentWithStats[];
}

// Reaction types
export const TargetType = {
  Question: 1,
  Answer: 2,
  Comment: 3,
  User: 4,
} as const;

export type TargetType = (typeof TargetType)[keyof typeof TargetType];

export const ReactionAction = {
  Cancel: 0,
  Like: 1,
  Dislike: 2,
} as const;

export type ReactionAction =
  (typeof ReactionAction)[keyof typeof ReactionAction];

export interface ReactionStatus {
  status: 0 | 1 | 2; // 0=none, 1=like, 2=dislike
}

// Follow types
export interface Follow {
  id: number;
  user_id: number;
  target_type: TargetType;
  target_id: number;
  created_at: string;
  updated_at: string;
}

// Follow with user (for following/followers list)
export interface FollowWithUser {
  follow: Follow;
  user: User;
}

// Follower with user (for followers list)
export interface FollowerWithUser {
  follow: Follow;
  follower: User;
}

// Follow with question (for followed questions list)
export interface FollowWithQuestion {
  follow: Follow;
  question: Question;
}

// Collection types
export interface Collection {
  id: number;
  user_id: number;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface CollectionItem {
  id: number;
  collection_id: number;
  answer_id: number;
  created_at: string;
  updated_at: string;
}

export interface AnswerInCollectionWithStats extends AnswerWithStats {
  collection_item_id: number;
}

// 收藏夹中的回答（带问题信息）
export interface CollectionAnswerWithQuestion {
  id: number;
  content: string;
  question_id: number;
  user_id: number;
  user?: User;
  created_at: string;
  updated_at: string;
  collection_item_id: number;
  stats: AnswerStats;
  reaction_status?: 0 | 1 | 2;
  question?: QuestionWithStats;
}

// ============================================
// Agent 相关类型
// ============================================

/**
 * Agent 元配置（RawConfig 字段）
 */
export interface AgentMeta {
  headline: string;
  bio: string;
  topics: string[];
  bias: string;
  style_tag: string;
  reply_mode: string;
  activity_level: "high" | "medium" | "low";
  expressiveness?: "terse" | "balanced" | "verbose" | "dynamic";
}

export interface DebateStatus {
  status: string;
  current_cycle: number;
  total_cycles: number;
  history_count: number;
  logs: string[];
}

export interface DebateHistoryItem {
  id: number;
  cycle: number;
  topic: string;
  question_id?: number;
  messages: number;
  participants: string[];
  errors: string[];
  created_at: string;
}

/**
 * 创建 Agent 请求
 */
export interface CreateAgentRequest {
  name: string; // 2-50字
  headline: string; // 最大100字
  bio: string; // 最大1000字
  topics: string[]; // 至少1个，每个最大50字
  bias: string; // 最大200字
  style_tag: string; // 最大50字
  reply_mode: string; // 最大50字
  activity_level: "high" | "medium" | "low";
  avatar?: string;
  system_prompt?: string; // 可选，最大5000字
  expressiveness?: "terse" | "balanced" | "verbose" | "dynamic";
}

/**
 * 更新 Agent 请求
 */
export interface UpdateAgentRequest {
  name?: string;
  headline?: string;
  bio?: string;
  topics?: string[];
  bias?: string;
  style_tag?: string;
  reply_mode?: string;
  activity_level?: "high" | "medium" | "low";
  avatar?: string;
  system_prompt?: string;
  expressiveness?: "terse" | "balanced" | "verbose" | "dynamic";
}

/**
 * Agent 响应
 */
export interface AgentResponse {
  id: number;
  name: string;
  avatar: string;
  is_system: boolean;
  owner_id: number;
  owner_name?: string;
  system_prompt?: string;
  raw_config: AgentMeta;
  stats: AgentStats;
  api_key?: string; // 只在创建时返回
  created_at?: string;
  updated_at?: string;
}

/**
 * Agent 统计
 */
export interface AgentStats {
  questions_count: number;
  answers_count: number;
  followers_count: number;
}

/**
 * Agent 列表响应
 */
export interface AgentListResponse {
  agents: AgentResponse[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * Agent 优化请求（Python 服务）
 */
export interface OptimizeAgentRequest {
  name: string;
  headline: string;
  bio: string;
  topics: string;
  bias: string;
  style_tag: string;
  reply_mode: string;
  expressiveness: "terse" | "balanced" | "verbose" | "dynamic";
}

/**
 * Agent 优化响应（Python 服务）
 */
export interface OptimizeAgentResponse {
  code: number;
  data: {
    system_prompt: string;
    is_fallback: boolean;
    structured_output?: any;
    error?: string;
  };
}

/**
 * Agent 测试对话请求（Python 服务）
 */
export interface PlaygroundRequest {
  system_prompt: string;
  question: string;
}

/**
 * Agent 测试对话响应（Python 服务）
 */
export interface PlaygroundResponse {
  code: number;
  data: {
    reply: string;
  };
}

// ============================================
// 热点相关类型（设计文档 第十二章）
// ============================================

/**
 * 知乎/微博原始回答
 */
export interface HotspotAnswer {
  id: number;
  hotspot_id: number;
  author_name: string;
  author_url?: string;
  content: string;
  upvote_count: number;
  comment_count: number;
  rank: number;
  zhihu_answer_id?: string;
  created_at: string;
}

/**
 * 热点项
 */
export interface Hotspot {
  id: number;
  source: "zhihu" | "weibo";
  source_id?: string;
  title: string;
  content?: string;
  url?: string;
  rank: number;
  heat?: string;
  status: "pending" | "processing" | "completed" | "skipped";
  question_id?: number;
  hotspot_date: string;
  crawled_at: string;
  processed_at?: string;
  answers?: HotspotAnswer[];
  created_at: string;
  updated_at: string;
}

/**
 * 热点列表响应
 */
export interface HotspotListResponse {
  hotspots: Hotspot[];
  total: number;
  page: number;
  page_size: number;
}

export interface HotspotDatesResponse {
  dates: string[];
  recent_dates: string[];
  min_date: string;
  max_date: string;
}
