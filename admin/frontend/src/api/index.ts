import http from "./http";

export const api = {
  login: (username: string, password: string) =>
    http.post("/admin/auth/login", { username, password }),
  me: () => http.get("/admin/auth/me"),

  overview: () => http.get("/admin/dashboard/overview"),
  loginTrend: () => http.get("/admin/dashboard/login-trend"),
  dashboardCharts: (days = 7) =>
    http.get("/admin/dashboard/charts", { params: { days } }),

  listAdmins: () => http.get("/admin/admin-users"),
  createAdmin: (payload: any) => http.post("/admin/admin-users", payload),
  updateAdmin: (id: number, payload: any) =>
    http.patch(`/admin/admin-users/${id}`, payload),
  deleteAdmin: (id: number) => http.delete(`/admin/admin-users/${id}`),

  listUsers: (params: any) => http.get("/admin/users", { params }),
  createUser: (payload: any) => http.post("/admin/users", payload),
  updateUser: (id: number, payload: any) =>
    http.patch(`/admin/users/${id}`, payload),
  deleteUser: (id: number) => http.delete(`/admin/users/${id}`),

  listAgents: () => http.get("/admin/agents"),
  createAgent: (payload: any) => http.post("/admin/agents", payload),
  updateAgent: (id: number, payload: any) =>
    http.patch(`/admin/agents/${id}`, payload),
  deleteAgent: (id: number) => http.delete(`/admin/agents/${id}`),
  optimizeAgent: (payload: any) => http.post("/admin/agents/optimize", payload),
  playgroundAgent: (payload: any) =>
    http.post("/admin/agents/playground", payload),

  listQuestions: (params: any) =>
    http.get("/admin/content/questions", { params }),
  listAnswers: (params: any) => http.get("/admin/content/answers", { params }),
  listComments: (params: any) =>
    http.get("/admin/content/comments", { params }),
  updateQuestion: (id: number, payload: any) =>
    http.patch(`/admin/content/questions/${id}`, payload),
  updateAnswer: (id: number, payload: any) =>
    http.patch(`/admin/content/answers/${id}`, payload),
  updateComment: (id: number, payload: any) =>
    http.patch(`/admin/content/comments/${id}`, payload),
  deleteQuestion: (id: number) => http.delete(`/admin/content/questions/${id}`),
  deleteAnswer: (id: number) => http.delete(`/admin/content/answers/${id}`),
  deleteComment: (id: number) => http.delete(`/admin/content/comments/${id}`),
  purgeContentByDate: (payload: {
    date: string;
    delete_qa?: boolean;
    delete_debate?: boolean;
    reset_hotspots?: boolean;
  }) => http.post("/admin/content/purge-by-date", payload),

  debateStart: (payload: any) => http.post("/admin/ops/debate/start", payload),
  debateStop: () => http.post("/admin/ops/debate/stop"),
  debateStatus: () => http.get("/admin/ops/debate/status"),
  debateHistory: () => http.get("/admin/ops/debate/history"),
  createCrawlerJob: (source: "zhihu" | "weibo") =>
    http.post(`/admin/ops/crawler/${source}/jobs`),
  listCrawlerJobs: (params?: { source?: "zhihu" | "weibo"; limit?: number }) =>
    http.get("/admin/ops/crawler/jobs", { params }),
  getCrawlerJob: (jobId: string) => http.get(`/admin/ops/crawler/jobs/${jobId}`),
  getCrawlerJobLogs: (jobId: string, tail = 200) =>
    http.get(`/admin/ops/crawler/jobs/${jobId}/logs`, { params: { tail } }),
  runZhihuCrawler: () => http.post("/admin/ops/crawler/zhihu/jobs"),
  runWeiboCrawler: () => http.post("/admin/ops/crawler/weibo/jobs"),
  getRuntimeConfig: () => http.get("/admin/ops/runtime-config"),
  updateRuntimeConfig: (payload: any) =>
    http.put("/admin/ops/runtime-config", payload),
  getQaPolicy: () => http.get("/admin/ops/runtime/qa-policy"),
  updateQaPolicy: (payload: any) =>
    http.put("/admin/ops/runtime/qa-policy", payload),
  getDebatePolicy: () => http.get("/admin/ops/runtime/debate-policy"),
  updateDebatePolicy: (payload: any) =>
    http.put("/admin/ops/runtime/debate-policy", payload),
  getSchedulerPolicy: () => http.get("/admin/ops/runtime/scheduler-policy"),
  updateSchedulerPolicy: (payload: any) =>
    http.put("/admin/ops/runtime/scheduler-policy", payload),
  getRealtimePolicy: () => http.get("/admin/ops/runtime/realtime-policy"),
  updateRealtimePolicy: (payload: any) =>
    http.put("/admin/ops/runtime/realtime-policy", payload),
  getRuntimeCapacity: () => http.get("/admin/ops/runtime/capacity"),
  getLlmAlerts: (limit = 100) =>
    http.get("/admin/ops/runtime/llm-alerts", { params: { limit } }),
  ackLlmAlerts: (ids: string[]) =>
    http.post("/admin/ops/runtime/llm-alerts/ack", { ids }),
  streamUrl: (channel: "hotspots" | "questions" | "debates" | "agents" | "online") =>
    `/api/admin/stream/${channel}`,

  auditLogs: (limit = 100) =>
    http.get("/admin/ops/audit/logs", { params: { limit } }),
};
