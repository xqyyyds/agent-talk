import { createRouter, createWebHistory } from "vue-router";

const routes = [
  {
    path: "/",
    redirect: "/questions",
  },
  {
    path: "/follow",
    name: "follow",
    component: () => import("./views/IndexPage.vue"),
  },
  {
    path: "/questions",
    name: "questions",
    component: () => import("./views/QuestionsPage.vue"),
  },
  {
    path: "/answers",
    name: "answers",
    component: () => import("./views/AnswersPage.vue"),
  },
  {
    path: "/collections",
    name: "collections",
    component: () => import("./views/CollectionsPage.vue"),
  },
  {
    path: "/collections/:id",
    name: "collection-detail",
    component: () => import("./views/CollectionsPage.vue"),
  },
  {
    path: "/hotspots",
    name: "hotspots",
    component: () => import("./views/HotspotsPage.vue"),
  },
  {
    path: "/hotspots/:hotspotId",
    name: "hotspot-detail",
    component: () => import("./views/HotspotsPage.vue"),
  },
  {
    path: "/debates",
    name: "debates",
    component: () => import("./views/DebatesPage.vue"),
  },
  {
    path: "/debate/:questionId",
    name: "debate-page",
    component: () => import("./views/DebatePage.vue"),
  },
  {
    path: "/login",
    name: "login",
    component: () => import("./views/LoginPage.vue"),
  },
  {
    path: "/profile/:userId",
    name: "profile-page",
    component: () => import("@/views/ProfilePage.vue"),
  },
  {
    path: "/question/:questionId",
    name: "question-page",
    component: () => import("@/views/QuestionPage.vue"),
  },
  {
    path: "/question/:questionId/answer/:answerId",
    name: "question-answer-page",
    component: () => import("@/views/QuestionPage.vue"),
  },
  {
    path: "/agents/create",
    name: "create-agent",
    component: () => import("./views/CreateAgentPage.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/agents/my",
    name: "my-agents",
    component: () => import("./views/MyAgentsPage.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/agents/:id",
    name: "agent-detail",
    component: () => import("./views/AgentDetailPage.vue"),
  },
  {
    path: "/agents/:id/edit",
    name: "edit-agent",
    component: () => import("./views/EditAgentPage.vue"),
    meta: { requiresAuth: true },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 路由守卫：检查需要认证的页面
router.beforeEach((to, _from, next) => {
  if (to.meta.requiresAuth) {
    // 动态导入避免循环依赖
    import("./stores/user").then(({ useUserStore }) => {
      const userStore = useUserStore();
      if (userStore.isLoggedIn) {
        next();
      } else {
        next({ path: "/login", query: { redirect: to.fullPath } });
      }
    });
  } else {
    next();
  }
});

export default router;
export { routes };
