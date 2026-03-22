<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  show: boolean;
  src: string;
  alt?: string;
}>();

const emit = defineEmits<{
  (e: "close"): void;
}>();

function close() {
  emit("close");
}

const downloadableName = computed(() => {
  const raw = (props.alt || "avatar").trim();
  const safe = raw.replace(/[\\/:*?"<>|]/g, "_");
  return `${safe || "avatar"}.jpg`;
});
</script>

<template>
  <div
    v-if="props.show && props.src"
    class="fixed inset-0 z-[100] flex items-center justify-center bg-black/75 p-4"
    @click.stop
    @click.self="close"
  >
    <button
      class="absolute right-6 top-5 rounded-full bg-black/45 px-3 py-1 text-xl text-white hover:bg-black/65"
      @click="close"
    >
      ×
    </button>

    <div class="absolute left-1/2 top-5 z-[101] flex -translate-x-1/2 items-center gap-2">
      <a
        :href="props.src"
        :download="downloadableName"
        class="rounded-full bg-black/45 px-3 py-1.5 text-sm text-white hover:bg-black/65"
      >
        下载
      </a>
      <a
        :href="props.src"
        target="_blank"
        rel="noopener noreferrer"
        class="rounded-full bg-black/45 px-3 py-1.5 text-sm text-white hover:bg-black/65"
      >
        新窗口打开
      </a>
    </div>

    <img
      :src="props.src"
      :alt="props.alt || 'avatar'"
      class="max-h-[90vh] max-w-[90vw] rounded-xl object-contain shadow-2xl"
    />
  </div>
</template>
