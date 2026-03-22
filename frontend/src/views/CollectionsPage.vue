<script setup lang="ts">
import type { Collection, CollectionAnswerWithQuestion } from '../api/types'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getCollectionList, getCollectionItems, deleteCollection } from '../api/collection'
import CollectionCard from '../components/CollectionCard.vue'
import { useUserStore } from '../stores/user'

const route = useRoute()
const userStore = useUserStore()

const collections = ref<Collection[]>([])
const collectionsLoading = ref(false)

// 详情页状态
const selectedCollection = ref<Collection | null>(null)
const detailItems = ref<CollectionAnswerWithQuestion[]>([])
const detailLoading = ref(false)
const detailHasMore = ref(true)
const detailCursor = ref<number | undefined>(undefined)

const viewMode = computed(() => route.params.id ? 'detail' : 'list')
const collectionId = computed(() => route.params.id as string | undefined)

// 格式化日期
function formatDate(dateStr: string) {
  const date = new Date(dateStr)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

// 加载收藏夹列表
async function loadCollections() {
  if (!userStore.user?.token)
    return

  collectionsLoading.value = true
  try {
    const res = await getCollectionList()
    if (res.data.code === 200 && res.data.data) {
      collections.value = res.data.data
    }
  }
  catch (error) {
    console.error('Failed to load collections:', error)
  }
  finally {
    collectionsLoading.value = false
  }
}

// 进入详情页
async function enterDetail(collection: Collection) {
  selectedCollection.value = collection
  detailItems.value = []
  detailCursor.value = undefined
  detailHasMore.value = true
  await loadDetailItems()
}

// 加载详情内容
async function loadDetailItems() {
  if (!collectionId.value || detailLoading.value || !detailHasMore.value)
    return

  detailLoading.value = true
  try {
    const res = await getCollectionItems(Number(collectionId.value), detailCursor.value, 10)
    if (res.data.code === 200 && res.data.data) {
      detailItems.value = [...detailItems.value, ...res.data.data.list]
      detailHasMore.value = res.data.data.has_more
      detailCursor.value = res.data.data.next_cursor

      // 找到当前收藏夹的信息
      if (!selectedCollection.value && collections.value.length > 0) {
        selectedCollection.value = collections.value.find(c => c.id === Number(collectionId.value)) || null
      }
    }
  }
  catch (error) {
    console.error('Failed to load collection items:', error)
  }
  finally {
    detailLoading.value = false
  }
}

// 删除收藏夹
async function handleDeleteCollection(e: Event, collection: Collection) {
  e.preventDefault()
  e.stopPropagation()
  if (!confirm(`确定要删除收藏夹"${collection.name}"吗？`))
    return

  try {
    const res = await deleteCollection(collection.id)
    if (res.data.code === 200) {
      collections.value = collections.value.filter(c => c.id !== collection.id)
    }
  }
  catch (error) {
    console.error('Failed to delete collection:', error)
  }
}

onMounted(() => {
  if (viewMode.value === 'list') {
    loadCollections()
  } else if (collectionId.value) {
    loadDetailItems()
    // 同时加载列表（用于返回）
    loadCollections()
  }
})
</script>

<template>
  <div class="mx-auto mt-4 max-w-3xl px-4 pb-10 md:px-0">
    <!-- 列表视图 -->
    <template v-if="viewMode === 'list'">
      <!-- 页面标题 -->
      <div class="mb-6">
        <h1 class="text-2xl font-bold text-gray-900">我的收藏夹</h1>
      </div>

      <!-- 加载状态 -->
      <div v-if="collectionsLoading" class="py-12 text-center text-gray-500">
        加载中...
      </div>

      <!-- 空状态 -->
      <div v-else-if="collections.length === 0" class="rounded-lg bg-white p-12 text-center shadow-sm">
        <div class="mb-4">
          <span class="i-mdi-folder-open-outline inline-block text-6xl text-gray-300" />
        </div>
        <h3 class="text-lg font-medium text-gray-900 mb-2">还没有收藏夹</h3>
        <p class="text-gray-500">在回答页面点击"收藏"按钮即可创建收藏夹并收藏内容</p>
      </div>

      <!-- 收藏夹列表 -->
      <div v-else class="space-y-2">
        <a
          v-for="collection in collections"
          :key="collection.id"
          :href="`/collections/${collection.id}`"
          class="group block rounded-lg bg-white px-5 py-4 shadow-sm border border-gray-100 hover:border-blue-300 hover:shadow-md transition-all"
          @click.prevent="enterDetail(collection)"
        >
          <div class="flex items-center justify-between">
            <!-- 左侧信息 -->
            <div class="flex-1 min-w-0">
              <h3 class="text-lg font-bold text-gray-900 group-hover:text-blue-600 transition-colors">
                {{ collection.name }}
              </h3>
              <div class="mt-1 flex items-center gap-3 text-sm text-gray-400">
                <span>更新于 {{ formatDate(collection.updated_at) }}</span>
              </div>
            </div>

            <!-- 右侧箭头 -->
            <div class="flex items-center gap-2 ml-4">
              <!-- Hover 时显示的操作按钮 -->
              <button
                class="opacity-0 group-hover:opacity-100 flex items-center gap-1 rounded px-2 py-1 text-gray-400 hover:text-red-500 hover:bg-red-50 transition-all"
                @click="handleDeleteCollection($event, collection)"
              >
                <span class="i-mdi-delete text-lg" />
              </button>
              <span class="i-mdi-chevron-right text-gray-400 group-hover:text-blue-600 text-xl" />
            </div>
          </div>
        </a>
      </div>
    </template>

    <!-- 详情视图 -->
    <template v-else-if="viewMode === 'detail'">
      <!-- 返回按钮 + 标题 -->
      <div class="mb-6 flex items-center gap-3">
        <router-link
          to="/collections"
          class="flex items-center gap-1 text-gray-500 hover:text-gray-700 transition-colors"
        >
          <span class="i-mdi-arrow-left text-xl" />
          <span class="text-sm">返回</span>
        </router-link>
      </div>

      <!-- 收藏夹头部 -->
      <div class="mb-6 rounded-lg bg-white p-6 shadow-sm">
        <h1 class="text-2xl font-bold text-gray-900 mb-2">
          {{ selectedCollection?.name }}
        </h1>
        <p class="text-gray-500">收藏夹内容</p>
      </div>

      <!-- 加载状态 -->
      <div v-if="detailLoading && detailItems.length === 0" class="py-12 text-center text-gray-500">
        加载中...
      </div>

      <!-- 空状态 -->
      <div v-else-if="detailItems.length === 0" class="rounded-lg bg-white p-12 text-center shadow-sm">
        <div class="mb-4">
          <span class="i-mdi-folder-open-outline inline-block text-6xl text-gray-300" />
        </div>
        <h3 class="text-lg font-medium text-gray-900 mb-2">这个收藏夹还没有内容</h3>
        <p class="text-gray-500">在回答页面点击"收藏"按钮即可添加内容</p>
      </div>

      <!-- 内容列表 -->
      <div v-else class="space-y-3">
        <CollectionCard
          v-for="item in detailItems"
          :key="item.id"
          :question="(item.question || {
            id: item.question_id,
            title: '问题加载中...',
            content: '',
            user_id: 0,
            created_at: '',
            updated_at: '',
            stats: { like_count: 0, dislike_count: 0, comment_count: 0 }
          })"
          :answer="item"
        />
      </div>

      <!-- 加载更多 -->
      <div v-if="detailHasMore && detailItems.length > 0" class="mt-6 text-center">
        <button
          class="rounded-full border border-gray-300 bg-white px-6 py-2 text-gray-600 font-medium hover:bg-gray-50 transition-colors"
          :disabled="detailLoading"
          @click="loadDetailItems"
        >
          {{ detailLoading ? '加载中...' : '加载更多' }}
        </button>
      </div>
    </template>
  </div>
</template>
