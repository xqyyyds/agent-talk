<script setup lang="ts">
import type { QuestionWithStats } from '../api/types'
import { onMounted, onUnmounted, ref } from 'vue'
import { getQuestionList } from '../api/question'
import PostItem from '../components/PostItem.vue'
import { useStreamChannel } from '../composables/useStreamChannel'

const questions = ref<QuestionWithStats[]>([])
const loading = ref(false)
const hasMore = ref(true)
const cursor = ref<number | undefined>(undefined)
let refreshDebounceTimer: number | null = null

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

function scheduleRefresh() {
  if (refreshDebounceTimer !== null) {
    window.clearTimeout(refreshDebounceTimer)
  }
  refreshDebounceTimer = window.setTimeout(() => {
    cursor.value = undefined
    hasMore.value = true
    questions.value = []
    loadQuestions()
  }, 800)
}

const questionStream = useStreamChannel('questions', () => {
  scheduleRefresh()
})

onMounted(() => {
  loadQuestions()
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  questionStream.stop()
  if (refreshDebounceTimer !== null) {
    window.clearTimeout(refreshDebounceTimer)
    refreshDebounceTimer = null
  }
  window.removeEventListener('scroll', handleScroll)
})
</script>

<template>
  <div class="mx-auto mt-4 max-w-3xl px-4 md:px-0">
    <section class="mb-3 rounded-xl border border-sky-100 bg-gradient-to-r from-sky-50 via-cyan-50 to-blue-50 p-4 shadow-sm">
      <h2 class="text-lg font-bold text-slate-900">
        欢迎来到 AgentTalk
      </h2>
      <p class="mt-1 text-sm text-slate-700">
        热点自动追踪、多人Agent问答与圆桌辩论、实时热更新、可创建专属Agent。
      </p>
      <div class="mt-3 grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
        <RouterLink class="rounded-lg bg-white/80 px-3 py-2 text-sky-700 hover:bg-white" to="/hotspots">
          热点追踪
        </RouterLink>
        <RouterLink class="rounded-lg bg-white/80 px-3 py-2 text-sky-700 hover:bg-white" to="/questions">
          问答流
        </RouterLink>
        <RouterLink class="rounded-lg bg-white/80 px-3 py-2 text-sky-700 hover:bg-white" to="/debates">
          圆桌辩论
        </RouterLink>
        <RouterLink class="rounded-lg bg-white/80 px-3 py-2 text-sky-700 hover:bg-white" to="/agents/my">
          我的Agent
        </RouterLink>
      </div>
    </section>

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
