import { onMounted, ref } from "vue";
import { api } from "../api";
import { formatBeijingDateTime } from "../utils/datetime";
const tab = ref("questions");
const questionType = ref("all");
const rows = ref([]);
const loading = ref(false);
const error = ref("");
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const pageSizeOptions = [10, 20, 50, 100];
function formatDate(value) {
    return formatBeijingDateTime(value ?? null);
}
function totalPages() {
    return Math.max(1, Math.ceil(total.value / pageSize.value));
}
async function load() {
    loading.value = true;
    error.value = "";
    try {
        if (tab.value === "questions") {
            const { data } = await api.listQuestions({
                page: page.value,
                page_size: pageSize.value,
                q_type: questionType.value === "all" ? undefined : questionType.value,
            });
            rows.value = data.list;
            total.value = data.total || 0;
        }
        else if (tab.value === "answers") {
            const { data } = await api.listAnswers({
                page: page.value,
                page_size: pageSize.value,
            });
            rows.value = data.list;
            total.value = data.total || 0;
        }
        else {
            const { data } = await api.listComments({
                page: page.value,
                page_size: pageSize.value,
            });
            rows.value = data.list;
            total.value = data.total || 0;
        }
    }
    catch (err) {
        error.value = err?.response?.data?.detail || err?.message || "加载失败";
    }
    finally {
        loading.value = false;
    }
}
async function remove(row) {
    loading.value = true;
    error.value = "";
    try {
        if (tab.value === "questions") {
            await api.deleteQuestion(row.id);
        }
        else if (tab.value === "answers") {
            await api.deleteAnswer(row.id);
        }
        else {
            await api.deleteComment(row.id);
        }
        if (rows.value.length === 1 && page.value > 1) {
            page.value -= 1;
        }
        await load();
    }
    catch (err) {
        error.value = err?.response?.data?.detail || err?.message || "删除失败";
    }
    finally {
        loading.value = false;
    }
}
async function editRow(row) {
    if (tab.value === "questions") {
        const title = window.prompt("编辑问题标题", row.title || "");
        if (title === null)
            return;
        const content = window.prompt("编辑问题内容", row.content || "");
        if (content === null)
            return;
        await api.updateQuestion(row.id, { title, content });
        await load();
        return;
    }
    if (tab.value === "answers") {
        const content = window.prompt("编辑回答内容", row.content || "");
        if (content === null)
            return;
        await api.updateAnswer(row.id, { content });
        await load();
        return;
    }
    const content = window.prompt("编辑评论内容", row.content || "");
    if (content === null)
        return;
    await api.updateComment(row.id, { content });
    await load();
}
async function switchTab(next) {
    tab.value = next;
    page.value = 1;
    await load();
}
async function switchQuestionType(next) {
    questionType.value = next;
    page.value = 1;
    await load();
}
async function prevPage() {
    if (page.value <= 1)
        return;
    page.value -= 1;
    await load();
}
async function nextPage() {
    if (page.value >= totalPages())
        return;
    page.value += 1;
    await load();
}
async function onPageSizeChange(event) {
    const target = event.target;
    pageSize.value = Number(target.value);
    page.value = 1;
    await load();
}
onMounted(load);
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "panel" },
});
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
    ...{ class: "section-title" },
});
/** @type {__VLS_StyleScopedClasses['section-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "toolbar content-toolbar" },
});
/** @type {__VLS_StyleScopedClasses['toolbar']} */ ;
/** @type {__VLS_StyleScopedClasses['content-toolbar']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "toolbar-group" },
});
/** @type {__VLS_StyleScopedClasses['toolbar-group']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.switchTab('questions');
            // @ts-ignore
            [switchTab,];
        } },
    ...{ class: "secondary" },
    ...{ class: ({ 'is-active': __VLS_ctx.tab === 'questions' }) },
    disabled: (__VLS_ctx.loading),
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['is-active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.switchTab('answers');
            // @ts-ignore
            [switchTab, tab, loading,];
        } },
    ...{ class: "secondary" },
    ...{ class: ({ 'is-active': __VLS_ctx.tab === 'answers' }) },
    disabled: (__VLS_ctx.loading),
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['is-active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.switchTab('comments');
            // @ts-ignore
            [switchTab, tab, loading,];
        } },
    ...{ class: "secondary" },
    ...{ class: ({ 'is-active': __VLS_ctx.tab === 'comments' }) },
    disabled: (__VLS_ctx.loading),
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['is-active']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "label-inline" },
});
/** @type {__VLS_StyleScopedClasses['label-inline']} */ ;
(__VLS_ctx.total);
if (__VLS_ctx.tab === 'questions') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "toolbar content-toolbar" },
    });
    /** @type {__VLS_StyleScopedClasses['toolbar']} */ ;
    /** @type {__VLS_StyleScopedClasses['content-toolbar']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "toolbar-group" },
    });
    /** @type {__VLS_StyleScopedClasses['toolbar-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "label-inline" },
    });
    /** @type {__VLS_StyleScopedClasses['label-inline']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.tab === 'questions'))
                    return;
                __VLS_ctx.switchQuestionType('all');
                // @ts-ignore
                [tab, tab, loading, total, switchQuestionType,];
            } },
        ...{ class: "secondary" },
        ...{ class: ({ 'is-active': __VLS_ctx.questionType === 'all' }) },
        disabled: (__VLS_ctx.loading),
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
    /** @type {__VLS_StyleScopedClasses['is-active']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.tab === 'questions'))
                    return;
                __VLS_ctx.switchQuestionType('qa');
                // @ts-ignore
                [loading, switchQuestionType, questionType,];
            } },
        ...{ class: "secondary" },
        ...{ class: ({ 'is-active': __VLS_ctx.questionType === 'qa' }) },
        disabled: (__VLS_ctx.loading),
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
    /** @type {__VLS_StyleScopedClasses['is-active']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.tab === 'questions'))
                    return;
                __VLS_ctx.switchQuestionType('debate');
                // @ts-ignore
                [loading, switchQuestionType, questionType,];
            } },
        ...{ class: "secondary" },
        ...{ class: ({ 'is-active': __VLS_ctx.questionType === 'debate' }) },
        disabled: (__VLS_ctx.loading),
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
    /** @type {__VLS_StyleScopedClasses['is-active']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "toolbar content-pagination" },
});
/** @type {__VLS_StyleScopedClasses['toolbar']} */ ;
/** @type {__VLS_StyleScopedClasses['content-pagination']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "toolbar-group" },
});
/** @type {__VLS_StyleScopedClasses['toolbar-group']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.prevPage) },
    ...{ class: "secondary" },
    disabled: (__VLS_ctx.loading || __VLS_ctx.page <= 1),
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "label-inline" },
});
/** @type {__VLS_StyleScopedClasses['label-inline']} */ ;
(__VLS_ctx.page);
(__VLS_ctx.totalPages());
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.nextPage) },
    ...{ class: "secondary" },
    disabled: (__VLS_ctx.loading || __VLS_ctx.page >= __VLS_ctx.totalPages()),
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "toolbar-group" },
});
/** @type {__VLS_StyleScopedClasses['toolbar-group']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
    ...{ class: "label-inline" },
});
/** @type {__VLS_StyleScopedClasses['label-inline']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
    ...{ onChange: (__VLS_ctx.onPageSizeChange) },
    value: (__VLS_ctx.pageSize),
    disabled: (__VLS_ctx.loading),
});
for (const [size] of __VLS_vFor((__VLS_ctx.pageSizeOptions))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        key: (size),
        value: (size),
    });
    (size);
    // @ts-ignore
    [loading, loading, loading, loading, questionType, prevPage, page, page, page, totalPages, totalPages, nextPage, onPageSizeChange, pageSize, pageSizeOptions,];
}
__VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
    ...{ onClick: (__VLS_ctx.load) },
    ...{ class: "secondary" },
    disabled: (__VLS_ctx.loading),
});
/** @type {__VLS_StyleScopedClasses['secondary']} */ ;
if (__VLS_ctx.error) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "panel-soft" },
        ...{ style: {} },
    });
    /** @type {__VLS_StyleScopedClasses['panel-soft']} */ ;
    (__VLS_ctx.error);
}
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "table-wrap" },
});
/** @type {__VLS_StyleScopedClasses['table-wrap']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
    ...{ class: "table" },
});
/** @type {__VLS_StyleScopedClasses['table']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
if (__VLS_ctx.tab === 'questions') {
    __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
        ...{ class: "type-cell" },
    });
    /** @type {__VLS_StyleScopedClasses['type-cell']} */ ;
}
__VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
    ...{ class: "time-cell" },
});
/** @type {__VLS_StyleScopedClasses['time-cell']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
for (const [row] of __VLS_vFor((__VLS_ctx.rows))) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
        key: (row.id),
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        ...{ class: "mono" },
    });
    /** @type {__VLS_StyleScopedClasses['mono']} */ ;
    (row.id);
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        ...{ class: "mono" },
    });
    /** @type {__VLS_StyleScopedClasses['mono']} */ ;
    (row.user_id);
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        ...{ class: "mono" },
    });
    /** @type {__VLS_StyleScopedClasses['mono']} */ ;
    (row.question_id || row.answer_id || "-");
    if (__VLS_ctx.tab === 'questions') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
            ...{ class: "type-cell" },
        });
        /** @type {__VLS_StyleScopedClasses['type-cell']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "badge" },
            ...{ class: (row.type === 'debate' ? 'badge-debate' : 'badge-qa') },
        });
        /** @type {__VLS_StyleScopedClasses['badge']} */ ;
        (row.type || "qa");
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        ...{ class: "time-cell" },
    });
    /** @type {__VLS_StyleScopedClasses['time-cell']} */ ;
    (__VLS_ctx.formatDate(row.created_at));
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
    (row.title || row.content);
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        ...{ class: "actions-cell" },
    });
    /** @type {__VLS_StyleScopedClasses['actions-cell']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.editRow(row);
                // @ts-ignore
                [tab, tab, loading, load, error, error, rows, formatDate, editRow,];
            } },
        ...{ class: "secondary" },
        disabled: (__VLS_ctx.loading),
    });
    /** @type {__VLS_StyleScopedClasses['secondary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.remove(row);
                // @ts-ignore
                [loading, remove,];
            } },
        ...{ class: "warn" },
        disabled: (__VLS_ctx.loading),
    });
    /** @type {__VLS_StyleScopedClasses['warn']} */ ;
    // @ts-ignore
    [loading,];
}
if (!__VLS_ctx.loading && __VLS_ctx.rows.length === 0) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
        colspan: (__VLS_ctx.tab === 'questions' ? 7 : 6),
        ...{ style: {} },
    });
}
// @ts-ignore
[tab, loading, rows,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
