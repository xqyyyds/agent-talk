import { getAnswerCollectionStatuses } from "../api/collection";

type PendingResolver = {
  resolve: (collectionIds: number[]) => void;
  reject: (error: unknown) => void;
};

const pending = new Map<number, PendingResolver[]>();
let flushTimer: number | null = null;

function scheduleFlush() {
  if (flushTimer !== null) return;
  flushTimer = window.setTimeout(() => {
    void flushQueue();
  }, 0);
}

async function flushQueue() {
  const answerIds = Array.from(pending.keys());
  const currentPending = new Map(pending);
  pending.clear();
  if (flushTimer !== null) {
    window.clearTimeout(flushTimer);
    flushTimer = null;
  }
  if (answerIds.length === 0) return;

  try {
    const res = await getAnswerCollectionStatuses(answerIds);
    const items = res.data.data?.items || [];
    const resultMap = new Map<number, number[]>();
    for (const item of items) {
      resultMap.set(item.answer_id, item.collection_ids || []);
    }

    for (const answerId of answerIds) {
      const resolvers = currentPending.get(answerId) || [];
      const collectionIds = resultMap.get(answerId) || [];
      for (const resolver of resolvers) {
        resolver.resolve(collectionIds);
      }
    }
  } catch (error) {
    for (const resolvers of currentPending.values()) {
      for (const resolver of resolvers) {
        resolver.reject(error);
      }
    }
  }
}

export function queueAnswerCollectionStatus(answerId: number) {
  return new Promise<number[]>((resolve, reject) => {
    const resolvers = pending.get(answerId) || [];
    resolvers.push({ resolve, reject });
    pending.set(answerId, resolvers);
    scheduleFlush();
  });
}
