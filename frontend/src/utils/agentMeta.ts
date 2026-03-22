export const AGENT_TOPIC_MAX = 5;

const STYLE_LABEL_MAP: Record<string, string> = {
  严谨专业: "理性分析师",
  温暖治愈: "暖心知己",
  温暖自愈: "暖心知己",
  幽默吐槽: "毒舌段子手",
  犀利毒舌: "独立思考者",
  简洁务实: "实干派",
  热血激情: "阳光使者",
  脑洞类比: "脑洞大师",
  文艺清新: "文艺青年",
};

export function normalizeTopics(topics?: string[] | null): string[] {
  if (!Array.isArray(topics)) return [];
  const values = topics
    .map((item) => String(item || "").trim())
    .filter((item) => item.length > 0);
  return Array.from(new Set(values));
}

export function getVisibleTopics(
  topics?: string[] | null,
  max: number = AGENT_TOPIC_MAX,
): string[] {
  return normalizeTopics(topics).slice(0, Math.max(1, max));
}

export function getTopicOverflowCount(
  topics?: string[] | null,
  max: number = AGENT_TOPIC_MAX,
): number {
  const normalized = normalizeTopics(topics);
  return Math.max(0, normalized.length - Math.max(1, max));
}

export function getStylePresetLabel(styleTag?: string | null): string {
  const key = String(styleTag || "").trim();
  if (!key) return "";
  return STYLE_LABEL_MAP[key] || key;
}
