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

function shortenUrl(url: string, maxLength = 72): string {
  if (url.length <= maxLength) return url;
  return `${url.slice(0, 50)}...${url.slice(-16)}`;
}

function trimUrlPunctuation(url: string): { clean: string; tail: string } {
  const match = url.match(/^(.*?)([),.;!?，。；！？）】》]+)?$/);
  if (!match) return { clean: url, tail: "" };
  return { clean: match[1] || "", tail: match[2] || "" };
}

function renderInlineWithLinks(text: string): string {
  if (!text) return "";
  const urlRegex =
    /((?:https?:\/\/|www\.)[^\s<>"']+|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:\/[^\s<>"']*)?)/g;

  const parts = text.split(urlRegex);
  return parts
    .map((part) => {
      if (!part) return "";
      const maybeUrl = /^(?:https?:\/\/|www\.|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,})/i.test(
        part,
      );
      if (!maybeUrl) return escapeHtml(part);

      const { clean, tail } = trimUrlPunctuation(part);
      if (!clean) return escapeHtml(part);

      const href = /^https?:\/\//i.test(clean) ? clean : `https://${clean}`;
      const safeHref = escapeHtml(href);
      const label = escapeHtml(shortenUrl(clean));
      const safeTail = escapeHtml(tail);
      return `<a href="${safeHref}" target="_blank" rel="noopener noreferrer">${label}</a>${safeTail}`;
    })
    .join("");
}

function isBulletLine(line: string): boolean {
  return /^\s*[-*•]\s+/.test(line);
}

function isOrderedLine(line: string): boolean {
  return /^\s*\d+[.)、]\s+/.test(line);
}

function isQuoteLine(line: string): boolean {
  return /^\s*>\s?/.test(line);
}

function renderParagraphBlock(block: string): string {
  const html = renderInlineWithLinks(block).replace(/\n/g, "<br />");
  return `<p>${html}</p>`;
}

function renderListBlock(lines: string[], ordered: boolean): string {
  const tag = ordered ? "ol" : "ul";
  const items = lines
    .map((line) => {
      const stripped = ordered
        ? line.replace(/^\s*\d+[.)、]\s+/, "")
        : line.replace(/^\s*[-*•]\s+/, "");
      return `<li>${renderInlineWithLinks(stripped)}</li>`;
    })
    .join("");
  return `<${tag}>${items}</${tag}>`;
}

function renderQuoteBlock(lines: string[]): string {
  const content = lines
    .map((line) => line.replace(/^\s*>\s?/, ""))
    .join("\n");
  const html = renderInlineWithLinks(content).replace(/\n/g, "<br />");
  return `<blockquote><p>${html}</p></blockquote>`;
}

export function formatRichTextForDisplay(raw: string | null | undefined): string {
  const normalized = normalizeLineBreaks(String(raw ?? ""))
    .replace(/\u0000/g, "")
    .trim();
  if (!normalized) return "";

  const blocks = normalized
    .split(/\n{2,}/)
    .map(block => block.trim())
    .filter(Boolean);

  return blocks
    .map((block) => {
      const lines = block
        .split("\n")
        .map(line => line.trimEnd())
        .filter(Boolean);
      if (!lines.length) return "";

      if (lines.every(isBulletLine)) return renderListBlock(lines, false);
      if (lines.every(isOrderedLine)) return renderListBlock(lines, true);
      if (lines.every(isQuoteLine)) return renderQuoteBlock(lines);
      return renderParagraphBlock(lines.join("\n"));
    })
    .filter(Boolean)
    .join("");
}
