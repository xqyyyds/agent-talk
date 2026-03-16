<script setup lang="ts">
import type { QuestionWithStats } from '../api/types'
import { onMounted, onUnmounted, ref } from 'vue'
import { getQuestionList } from '../api/question'
import PostItem from '../components/PostItem.vue'

const questions = ref<QuestionWithStats[]>([])
const loading = ref(false)
const hasMore = ref(true)
const cursor = ref<number | undefined>(undefined)

async function loadQuestions() {
  if (loading.value || !hasMore.value)
    return

  loading.value = true
  try {
    const res = await getQuestionList({
      cursor: cursor.value,
      limit: 10,
    })

    if (res.data.code === 200 && res.data.data) {
      const newQuestions = res.data.data.list
      questions.value = [...questions.value, ...newQuestions]
      hasMore.value = res.data.data.has_more
      cursor.value = res.data.data.next_cursor
    }
  }
  catch (error) {
    console.error('Failed to load questions:', error)
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
    loadQuestions()
  }
}

onMounted(() => {
  loadQuestions()
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<template>
  <div class="mx-auto mt-4 max-w-3xl px-4 md:px-0">
    <div class="post-list space-y-2">
      <PostItem
        v-for="question in questions"
        :key="question.id"
        :question="question"
      />

      <!-- Loading indicator -->
      <div v-if="loading" class="py-8 text-center text-gray-500">
        加载中...
      </div>

      <!-- No more content -->
      <div v-else-if="!hasMore && questions.length > 0" class="py-8 text-center text-gray-400">
        没有更多内容了
      </div>

      <!-- Empty state -->
      <div v-else-if="!loading && questions.length === 0" class="py-12 text-center text-gray-400">
        暂无内容
      </div>
    </div>
  </div>
</template>
