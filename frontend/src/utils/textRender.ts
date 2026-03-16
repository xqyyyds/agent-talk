function escapeHtml(input: string): string {
  return input
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function normalizeLineBreaks(input: string): string {
  return input
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/\\r\\n/g, "\n")
    .replace(/\\n/g, "\n");
}

function isUrl(text: string): boolean {
  return /^https?:\/\/[^\s]+$/i.test(text);
}

function shortenUrl(url: string, maxLength = 72): string {
  if (url.length <= maxLength) return url;
  return `${url.slice(0, 50)}...${url.slice(-16)}`;
}

export function formatRichTextForDisplay(raw: string | null | undefined): string {
  const normalized = normalizeLineBreaks(String(raw ?? "")).trim();
  if (!normalized) return "";

  const urlRegex = /(https?:\/\/[^\s<>"']+)/gi;
  const parts = normalized.split(urlRegex);
  const html = parts
    .map((part) => {
      if (!part) return "";
      if (isUrl(part)) {
        const safeHref = escapeHtml(part);
        const label = escapeHtml(shortenUrl(part));
        return `<a href="${safeHref}" target="_blank" rel="noopener noreferrer">${label}</a>`;
      }
      return escapeHtml(part);
    })
    .join("");

  return html.replace(/\n/g, "<br />");
}

