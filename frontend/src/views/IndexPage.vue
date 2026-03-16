<script setup lang="ts">
import type { AnswerWithQuestion } from '../api/types'
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getAnswerFeed } from '../api/answer'
import { getFollowingList } from '../api/follow'
import { TargetType } from '../api/types'
import PostItem from '../components/PostItem.vue'
import { useUserStore } from '../stores/user'

const route = useRoute()
const userStore = useUserStore()

const answers = ref<AnswerWithQuestion[]>([])
const loading = ref(false)
const hasMore = ref(true)
const cursor = ref<number | undefined>(undefined)

async function loadAnswers() {
  if (loading.value || !hasMore.value)
    return

  loading.value = true
  try {
    const currentPath = route.path

    if (currentPath === '/follow') {
      // Load followed answers
      if (!userStore.user?.token) {
        answers.value = []
        hasMore.value = false
        return
      }

      const res = await getFollowingList(TargetType.Answer, cursor.value, 10)
      if (res.data.code === 200 && res.data.data) {
        // For followed answers, we would need to fetch answer details
        // This is a limitation - the API returns follow objects, not full answer objects
        // For now, we'll just show empty state
        answers.value = []
        hasMore.value = false
      }
    }
    else {
      // Load answer feed (for '/' and '/new')
      const res = await getAnswerFeed(cursor.value, 10)

      if (res.data.code === 200 && res.data.data) {
        const newAnswers = res.data.data.list
        answers.value = [...answers.value, ...newAnswers]
        hasMore.value = res.data.data.has_more
        cursor.value = res.data.data.next_cursor
      }
    }
  }
  catch (error) {
    console.error('Failed to load answers:', error)
  }
  finally {
    loading.value = false
  }
}

function resetAndLoad() {
  answers.value = []
  cursor.value = undefined
  hasMore.value = true
  loadAnswers()
}

// Infinite scroll handler
function handleScroll() {
  const scrollTop = window.scrollY
  const windowHeight = window.innerHeight
  const documentHeight = document.documentElement.scrollHeight

  if (scrollTop + windowHeight >= documentHeight - 200) {
    loadAnswers()
  }
}

onMounted(() => {
  resetAndLoad()
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})

// Watch route changes to reload
watch(() => route.path, () => {
  resetAndLoad()
})
</script>

<template>
  <div class="mx-auto mt-4 max-w-3xl px-4 md:px-0">
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
