<script setup lang="ts">
import { computed, ref } from "vue";
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

const displaySrc = computed(() => props.src || props.fallback || "");

function handleClick(event: MouseEvent) {
  if (!props.previewable || !displaySrc.value) return;
  event.preventDefault();
  event.stopPropagation();
  showPreview.value = true;
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
    />
  </button>

  <img
    v-else
    :src="displaySrc"
    :alt="props.alt"
    :class="props.imgClass"
  />

  <ImagePreviewModal
    :show="showPreview"
    :src="displaySrc"
    :alt="props.alt"
    @close="showPreview = false"
  />
</template>
