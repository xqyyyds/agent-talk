import { createRouter, createWebHistory, } from "vue-router";
import LoginPage from "./pages/LoginPage.vue";
import DashboardPage from "./pages/DashboardPage.vue";
import AdminsPage from "./pages/AdminsPage.vue";
import UsersPage from "./pages/UsersPage.vue";
import AgentsPage from "./pages/AgentsPage.vue";
import ModelManagementPage from "./pages/ModelManagementPage.vue";
import ContentPage from "./pages/ContentPage.vue";
import OpsPage from "./pages/OpsPage.vue";
import AuditPage from "./pages/AuditPage.vue";
import AlertsPage from "./pages/AlertsPage.vue";
const router = createRouter({
    history: createWebHistory(),
    routes: [
        { path: "/login", component: LoginPage, meta: { public: true } },
        { path: "/", redirect: "/dashboard" },
        { path: "/dashboard", component: DashboardPage },
        { path: "/admins", component: AdminsPage },
        { path: "/users", component: UsersPage },
        { path: "/agents", component: AgentsPage },
        { path: "/models", component: ModelManagementPage },
        { path: "/alerts", component: AlertsPage },
        { path: "/content", component: ContentPage },
        { path: "/ops", component: OpsPage },
        { path: "/audit", component: AuditPage },
    ],
});
router.beforeEach((to) => {
    if (to.meta.public) {
        return true;
    }
    const token = localStorage.getItem("admin_token");
    if (!token) {
        return "/login";
    }
    return true;
});
export default router;
