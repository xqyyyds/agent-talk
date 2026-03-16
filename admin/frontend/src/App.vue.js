import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
const route = useRoute();
const router = useRouter();
const isLoginPage = computed(() => route.path === "/login");
const navItems = [
    { path: "/dashboard", label: "总览" },
    { path: "/admins", label: "管理员" },
    { path: "/users", label: "用户" },
    { path: "/agents", label: "Agent" },
    { path: "/content", label: "内容治理" },
    { path: "/ops", label: "运维控制" },
    { path: "/audit", label: "审计日志" },
];
function logout() {
    localStorage.removeItem("admin_token");
    router.push("/login");
}
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
if (__VLS_ctx.isLoginPage) {
    let __VLS_0;
    /** @ts-ignore @type {typeof __VLS_components.routerView | typeof __VLS_components.RouterView} */
    routerView;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({}));
    const __VLS_2 = __VLS_1({}, ...__VLS_functionalComponentArgsRest(__VLS_1));
    var __VLS_5 = {};
    var __VLS_3;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "admin-shell" },
    });
    /** @type {__VLS_StyleScopedClasses['admin-shell']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.aside, __VLS_intrinsics.aside)({
        ...{ class: "left-rail" },
    });
    /** @type {__VLS_StyleScopedClasses['left-rail']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "brand" },
    });
    /** @type {__VLS_StyleScopedClasses['brand']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
        ...{ class: "brand-dot" },
    });
    /** @type {__VLS_StyleScopedClasses['brand-dot']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.nav, __VLS_intrinsics.nav)({
        ...{ class: "menu-list" },
    });
    /** @type {__VLS_StyleScopedClasses['menu-list']} */ ;
    for (const [item] of __VLS_vFor((__VLS_ctx.navItems))) {
        let __VLS_6;
        /** @ts-ignore @type {typeof __VLS_components.RouterLink | typeof __VLS_components.RouterLink} */
        RouterLink;
        // @ts-ignore
        const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
            key: (item.path),
            to: (item.path),
            ...{ class: "menu-item" },
            ...{ class: ({ active: __VLS_ctx.route.path === item.path }) },
        }));
        const __VLS_8 = __VLS_7({
            key: (item.path),
            to: (item.path),
            ...{ class: "menu-item" },
            ...{ class: ({ active: __VLS_ctx.route.path === item.path }) },
        }, ...__VLS_functionalComponentArgsRest(__VLS_7));
        /** @type {__VLS_StyleScopedClasses['menu-item']} */ ;
        /** @type {__VLS_StyleScopedClasses['active']} */ ;
        const { default: __VLS_11 } = __VLS_9.slots;
        (item.label);
        // @ts-ignore
        [isLoginPage, navItems, route,];
        var __VLS_9;
        // @ts-ignore
        [];
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.logout) },
        ...{ class: "danger-ghost" },
    });
    /** @type {__VLS_StyleScopedClasses['danger-ghost']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.main, __VLS_intrinsics.main)({
        ...{ class: "main-stage" },
    });
    /** @type {__VLS_StyleScopedClasses['main-stage']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
        ...{ class: "top-strip" },
    });
    /** @type {__VLS_StyleScopedClasses['top-strip']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    (__VLS_ctx.navItems.find((item) => item.path === __VLS_ctx.route.path)
        ?.label || "后台");
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "status-pill" },
    });
    /** @type {__VLS_StyleScopedClasses['status-pill']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "view-wrap" },
    });
    /** @type {__VLS_StyleScopedClasses['view-wrap']} */ ;
    let __VLS_12;
    /** @ts-ignore @type {typeof __VLS_components.routerView | typeof __VLS_components.RouterView} */
    routerView;
    // @ts-ignore
    const __VLS_13 = __VLS_asFunctionalComponent1(__VLS_12, new __VLS_12({}));
    const __VLS_14 = __VLS_13({}, ...__VLS_functionalComponentArgsRest(__VLS_13));
}
// @ts-ignore
[navItems, route, logout,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
