const BEIJING_TIMEZONE = "Asia/Shanghai";
function parseDateValue(value) {
    if (!value) {
        return null;
    }
    const normalized = value.trim();
    if (!normalized) {
        return null;
    }
    const hasExplicitTimezone = /([zZ]|[+\-]\d{2}:\d{2})$/.test(normalized);
    const isoNoTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$/;
    const candidate = hasExplicitTimezone
        ? normalized
        : isoNoTimezone.test(normalized)
            ? `${normalized}Z`
            : normalized;
    const date = new Date(candidate);
    return Number.isNaN(date.getTime()) ? null : date;
}
export function formatBeijingDateTime(value, withSeconds = true) {
    const date = parseDateValue(value);
    if (!date) {
        return "-";
    }
    return new Intl.DateTimeFormat("zh-CN", {
        timeZone: BEIJING_TIMEZONE,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: withSeconds ? "2-digit" : undefined,
        hour12: false,
    }).format(date);
}
export function formatBeijingTime(value) {
    return new Intl.DateTimeFormat("zh-CN", {
        timeZone: BEIJING_TIMEZONE,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
    }).format(value);
}
