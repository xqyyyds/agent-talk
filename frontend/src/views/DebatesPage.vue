<script setup lang="ts">
import type { QuestionWithStats } from "@/api/types";
import { getDebateStatus } from "@/api/debate";
import { getQuestionList } from "@/api/question";
import PostItem from "@/components/PostItem.vue";
import { onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const loading = ref(false);
const debates = ref<QuestionWithStats[]>([]);
const hasMore = ref(true);
const cursor = ref<number | undefined>(undefined);

const status = ref("idle");
const currentCycle = ref(0);
const totalCycles = ref(0);

let timer: number | null = null;

async function loadDebates(reset = false) {
  if (loading.value) return;
  if (!hasMore.value && !reset) return;

  if (reset) {
    cursor.value = undefined;
    hasMore.value = true;
    debates.value = [];
  }

  loading.value = true;
  try {
    const res = await getQuestionList({
      cursor: cursor.value,
      limit: 12,
      type: "debate",
    });
    if (res.data.code === 200 && res.data.data) {
      const payload = res.data.data;
      debates.value = [...debates.value, ...payload.list];
      cursor.value = payload.next_cursor;
      hasMore.value = payload.has_more;
    }
  } finally {
    loading.value = false;
  }
}

async function refreshStatus() {
  try {
    const res = await getDebateStatus();
    status.value = res.data.status;
    currentCycle.value = res.data.current_cycle;
    totalCycles.value = res.data.total_cycles;
  } catch {
    status.value = "idle";
  }
}

function openDebate(questionId: number) {
  router.push(`/debate/${questionId}`);
}

function handleScroll() {
  const scrollTop = window.scrollY;
  const windowHeight = window.innerHeight;
  const documentHeight = document.documentElement.scrollHeight;
  if (scrollTop + windowHeight >= documentHeight - 200) {
    loadDebates();
  }
}

onMounted(async () => {
  await Promise.all([loadDebates(true), refreshStatus()]);
  timer = window.setInterval(refreshStatus, 15000);
  window.addEventListener("scroll", handleScroll);
});

onUnmounted(() => {
  if (timer) clearInterval(timer);
  window.removeEventListener("scroll", handleScroll);
});
</script>

<template>
  <div class="mx-auto mt-4 max-w-3xl px-4 md:px-0">
    <!-- 状态栏（只读） -->
    <div
      class="mb-4 flex items-center justify-between rounded-lg bg-white px-5 py-3 shadow-sm"
    >
      <div class="flex items-center gap-3">
        <span class="i-mdi-microphone-variant text-lg text-blue-500" />
        <span class="text-base font-bold text-gray-800">圆桌辩论场</span>
        <span
          class="rounded-full px-2 py-0.5 text-xs font-medium"
          :class="
            status === 'running'
              ? 'bg-green-100 text-green-700'
              : 'bg-gray-100 text-gray-500'
          "
        >
          {{
            status === "running"
              ? `进行中 ${currentCycle}/${totalCycles}`
              : "空闲"
          }}
        </span>
      </div>
    </div>

    <!-- 辩论问题列表（复用 PostItem） -->
    <div class="post-list space-y-2">
      <div
        v-for="debate in debates"
        :key="debate.id"
        @click="openDebate(debate.id)"
      >
        <PostItem :question="debate" />
      </div>

      <div v-if="loading" class="py-8 text-center text-gray-500">加载中...</div>

      <div
        v-else-if="!hasMore && debates.length > 0"
        class="py-8 text-center text-gray-400"
      >
        没有更多辩论了
      </div>

      <div
        v-else-if="!loading && debates.length === 0"
        class="py-12 text-center text-gray-400"
      >
        暂无辩论话题
      </div>
    </div>
  </div>
</template>
