<script setup lang="ts">
import type { AnswerWithQuestion } from '../api/types'
import { onMounted, onUnmounted, ref } from 'vue'
import { getAnswerFeed } from '../api/answer'
import PostItem from '../components/PostItem.vue'

const answers = ref<AnswerWithQuestion[]>([])
const loading = ref(false)
const hasMore = ref(true)
const cursor = ref<number | undefined>(undefined)

function mergeByAnswerId(
  current: AnswerWithQuestion[],
  incoming: AnswerWithQuestion[],
) {
  const seenAnswerIds = new Set(current.map(item => item.id))
  const dedupedIncoming: AnswerWithQuestion[] = []

  for (const item of incoming) {
    if (seenAnswerIds.has(item.id))
      continue
    seenAnswerIds.add(item.id)
    dedupedIncoming.push(item)
  }

  return [...current, ...dedupedIncoming]
}

async function loadAnswers() {
  if (loading.value || !hasMore.value)
    return

  loading.value = true
  try {
    const res = await getAnswerFeed(cursor.value, 10)

    if (res.data.code === 200 && res.data.data) {
      const newAnswers = res.data.data.list
      answers.value = mergeByAnswerId(answers.value, newAnswers)
      hasMore.value = res.data.data.has_more
      cursor.value = res.data.data.next_cursor
    }
  }
  catch (error) {
    console.error('Failed to load answers:', error)
  }
  finally {
    loading.value = false
  }
}

function handleScroll() {
  const scrollTop = window.scrollY
  const windowHeight = window.innerHeight
  const documentHeight = document.documentElement.scrollHeight

  if (scrollTop + windowHeight >= documentHeight - 200) {
    loadAnswers()
  }
}

onMounted(() => {
  loadAnswers()
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<template>
  <div class="mx-auto mt-4 max-w-[1020px] px-4 md:px-0">
    <div class="post-list space-y-2">
      <PostItem
        v-for="answer in answers"
        :key="answer.id"
        :answer="answer"
      />

      <!-- Loading indicator -->
      <div v-if="loading" class="py-8 text-center text-gray-500">
        加载中...
      </div>

      <!-- No more content -->
      <div v-else-if="!hasMore && answers.length > 0" class="py-8 text-center text-gray-400">
        没有更多内容了
      </div>

      <!-- Empty state -->
      <div v-else-if="!loading && answers.length === 0" class="py-12 text-center text-gray-400">
        暂无内容
      </div>
    </div>
  </div>
</template>
