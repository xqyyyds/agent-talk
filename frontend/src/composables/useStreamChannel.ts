import { onUnmounted } from "vue";

type StreamMessage = {
  event?: string;
  data?: any;
  at?: string;
};

function parsePayload(raw: string): StreamMessage | null {
  const text = (raw || "").trim();
  if (!text) return null;

  try {
    const first = JSON.parse(text);
    if (typeof first === "string") {
      try {
        return JSON.parse(first) as StreamMessage;
      } catch {
        return { data: first };
      }
    }
    return first as StreamMessage;
  } catch {
    return { data: text };
  }
}

export function useStreamChannel(
  channel: "hotspots" | "questions" | "debates" | "agents" | "online",
  onMessage: (message: StreamMessage) => void,
  options?: {
    enabled?: boolean;
    reconnectMs?: number;
  },
) {
  const enabled = options?.enabled ?? true;
  const reconnectMs = options?.reconnectMs ?? 3000;

  let es: EventSource | null = null;
  let reconnectTimer: number | null = null;
  let closed = false;

  const cleanup = () => {
    if (reconnectTimer !== null) {
      window.clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (es) {
      es.close();
      es = null;
    }
  };

  const connect = () => {
    if (!enabled || closed) return;

    cleanup();
    es = new EventSource(`/api/stream/${channel}`);

    es.addEventListener("message", (ev) => {
      const payload = parsePayload((ev as MessageEvent).data);
      if (!payload) return;
      onMessage(payload);
    });

    es.onerror = () => {
      cleanup();
      if (closed) return;
      reconnectTimer = window.setTimeout(() => {
        connect();
      }, reconnectMs);
    };
  };

  connect();

  const stop = () => {
    closed = true;
    cleanup();
  };

  onUnmounted(() => {
    stop();
  });

  return {
    stop,
  };
}
