<script setup lang="ts">
import { computed, ref, watch } from "vue";
import ImagePreviewModal from "@/components/ImagePreviewModal.vue";

const props = withDefaults(
  defineProps<{
    src?: string;
    alt?: string;
    fallback?: string;
    imgClass?: string;
    previewable?: boolean;
  }>(),
  {
    src: "",
    alt: "avatar",
    fallback: "",
    imgClass: "",
    previewable: true,
  },
);

const showPreview = ref(false);
const inlineFallback =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="32" fill="#e5e7eb"/><circle cx="32" cy="24" r="12" fill="#9ca3af"/><path d="M14 54c3-10 11-16 18-16s15 6 18 16" fill="#9ca3af"/></svg>`,
  );
const currentSrc = ref("");

watch(
  () => [props.src, props.fallback],
  () => {
    currentSrc.value = props.src || props.fallback || inlineFallback;
  },
  { immediate: true },
);

const displaySrc = computed(() => currentSrc.value || inlineFallback);

function handleClick(event: MouseEvent) {
  if (!props.previewable || !displaySrc.value) return;
  event.preventDefault();
  event.stopPropagation();
  showPreview.value = true;
}

function handleError() {
  if (props.fallback && currentSrc.value !== props.fallback) {
    currentSrc.value = props.fallback;
    return;
  }
  currentSrc.value = inlineFallback;
}
</script>

<template>
  <button
    v-if="props.previewable && displaySrc"
    type="button"
    class="m-0 block border-none bg-transparent p-0"
    @click="handleClick"
  >
    <img
      :src="displaySrc"
      :alt="props.alt"
      :class="props.imgClass"
      @error="handleError"
    />
  </button>

  <img
    v-else
    :src="displaySrc"
    :alt="props.alt"
    :class="props.imgClass"
    @error="handleError"
  />

  <ImagePreviewModal
    :show="showPreview"
    :src="displaySrc"
    :alt="props.alt"
    @close="showPreview = false"
  />
</template>
