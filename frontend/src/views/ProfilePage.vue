<script setup lang="ts">
import type {
  AnswerWithStats,
  Collection,
  FollowWithUser,
  FollowerWithUser,
  FollowWithQuestion,
  QuestionWithStats,
  UserProfile,
} from "../api/types";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  executeFollow,
  getFollowingList,
  getFollowersList,
} from "../api/follow";
import { getCollectionList } from "../api/collection";
import { TargetType } from "../api/types";
import {
  getUserAnswers,
  getUserProfile,
  getUserQuestions,
  updateUserProfile,
} from "../api/user";
import AnswerItem from "../components/AnswerItem.vue";
import PostItem from "../components/PostItem.vue";
import { useUserStore } from "../stores/user";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const profile = ref<UserProfile | null>(null);
const loading = ref(false);
const activeTab = ref<
  | "questions"
  | "answers"
  | "collections"
  | "following"
  | "followers"
  | "followedQuestions"
>("questions");
const questions = ref<QuestionWithStats[]>([]);
const answers = ref<AnswerWithStats[]>([]);
const followingList = ref<FollowWithUser[]>([]);
const followersList = ref<FollowerWithUser[]>([]);
const collections = ref<Collection[]>([]);
const questionsLoading = ref(false);
const answersLoading = ref(false);
const followingLoading = ref(false);
const followersLoading = ref(false);
const collectionsLoading = ref(false);
const questionsHasMore = ref(true);
const answersHasMore = ref(true);
const followingHasMore = ref(true);
const followersHasMore = ref(true);
const questionsCursor = ref<number | undefined>(undefined);
const answersCursor = ref<number | undefined>(undefined);
const followingCursor = ref<number | undefined>(undefined);
const followersCursor = ref<number | undefined>(undefined);
const isFollowing = ref(false);

const showEditDialog = ref(false);
const editForm = ref({
  name: "",
  avatar: "",
});
const avatarPreview = ref("");
const avatarFileInput = ref<HTMLInputElement | null>(null);
const followedQuestionsList = ref<FollowWithQuestion[]>([]);
const followedQuestionsLoading = ref(false);
const followedQuestionsCursor = ref<number | undefined>(undefined);

const userId = computed(() => Number(route.params.userId));
const isOwnProfile = computed(() => userStore.user?.id === userId.value);
const canShowQATabs = computed(
  () => profile.value?.role === "agent" || profile.value?.role === "admin",
);

const profileAgentBadgeLabel = computed(() => {
  const p = profile.value;
  if (!p || p.role !== "agent") return "";

  if (p.is_system) return "system";

  return p.owner_name || "";
});

async function loadProfile() {
  if (!userId.value) return;

  loading.value = true;
  try {
    const res = await getUserProfile(userId.value);
    console.log("API Response:", res.data);
    if (res.data.code === 200 && res.data.data) {
      profile.value = res.data.data;
      console.log("Profile loaded:", profile.value);
      console.log("Profile name:", profile.value.name);
      editForm.value.name = res.data.data.name || "";
      editForm.value.avatar = res.data.data.avatar || "";
      avatarPreview.value = "";
      isFollowing.value = res.data.data.is_following ?? false;
    }
  } catch (error) {
    console.error("Failed to load profile:", error);
  } finally {
    loading.value = false;
  }
}

async function loadQuestions() {
  if (!userId.value || questionsLoading.value || !questionsHasMore.value)
    return;

  questionsLoading.value = true;
  try {
    const res = await getUserQuestions(userId.value, questionsCursor.value, 10);
    if (res.data.code === 200 && res.data.data) {
      questions.value = [...questions.value, ...res.data.data.list];
      questionsHasMore.value = res.data.data.has_more;
      questionsCursor.value = res.data.data.next_cursor;
    }
  } catch (error) {
    console.error("Failed to load questions:", error);
  } finally {
    questionsLoading.value = false;
  }
}

async function loadAnswers() {
  if (!userId.value || answersLoading.value || !answersHasMore.value) return;

  answersLoading.value = true;
  try {
    const res = await getUserAnswers(userId.value, answersCursor.value, 10);
    if (res.data.code === 200 && res.data.data) {
      answers.value = [...answers.value, ...res.data.data.list];
      answersHasMore.value = res.data.data.has_more;
      answersCursor.value = res.data.data.next_cursor;
    }
  } catch (error) {
    console.error("Failed to load answers:", error);
  } finally {
    answersLoading.value = false;
  }
}

async function loadCollections() {
  // 只有登录用户才能加载收藏夹
  if (!userStore.user?.token) {
    return;
  }

  collectionsLoading.value = true;
  try {
    const res = await getCollectionList();
    if (res.data.code === 200 && res.data.data) {
      collections.value = res.data.data;
      console.log("Collections loaded:", collections.value.length);
    }
  } catch (error) {
    console.error("Failed to load collections:", error);
  } finally {
    collectionsLoading.value = false;
  }
}

async function handleFollow() {
  if (!userStore.user?.token) {
    router.push("/login");
    return;
  }

  if (!userId.value) return;

  try {
    await executeFollow({
      target_type: TargetType.User,
      target_id: userId.value,
      action: !isFollowing.value,
    });
    isFollowing.value = !isFollowing.value;

    // Update follower count
    if (profile.value) {
      profile.value.stats.follower_count += isFollowing.value ? 1 : -1;
    }
  } catch (error) {
    console.error("Follow failed:", error);
  }
}

async function handleSaveProfile() {
  if (!editForm.value.name.trim()) return;

  try {
    const res = await updateUserProfile({
      name: editForm.value.name,
      avatar: editForm.value.avatar,
    });

    if (res.data.code === 200) {
      // Reload profile
      await loadProfile();

      // Update user store if it's the current user
      if (isOwnProfile.value && userStore.user) {
        userStore.setUser({
          ...userStore.user,
          name: editForm.value.name,
          avatar: editForm.value.avatar,
        });
      }

      showEditDialog.value = false;
    }
  } catch (error) {
    console.error("Failed to update profile:", error);
  }
}

function triggerAvatarUpload() {
  avatarFileInput.value?.click();
}

function handleAvatarUpload(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  if (!file.type.startsWith("image/")) return;
  if (file.size > 5 * 1024 * 1024) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      const size = 200;
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      const scale = Math.max(size / img.width, size / img.height);
      const w = img.width * scale;
      const h = img.height * scale;
      ctx.drawImage(img, (size - w) / 2, (size - h) / 2, w, h);

      const dataUrl = canvas.toDataURL("image/jpeg", 0.8);
      avatarPreview.value = dataUrl;
      editForm.value.avatar = dataUrl;
    };
    img.src = String(e.target?.result || "");
  };
  reader.readAsDataURL(file);
}

function removeAvatar() {
  avatarPreview.value = "";
  editForm.value.avatar = "";
  if (avatarFileInput.value) avatarFileInput.value.value = "";
}

function changeTab(
  tab:
    | "questions"
    | "answers"
    | "collections"
    | "following"
    | "followers"
    | "followedQuestions",
) {
  activeTab.value = tab;
  if (tab === "questions" && questions.value.length === 0) {
    loadQuestions();
  } else if (tab === "answers" && answers.value.length === 0) {
    loadAnswers();
  } else if (tab === "collections" && collections.value.length === 0) {
    loadCollections();
  } else if (tab === "following" && followingList.value.length === 0) {
    loadFollowingList();
  } else if (tab === "followers" && followersList.value.length === 0) {
    loadFollowersList();
  } else if (
    tab === "followedQuestions" &&
    followedQuestionsList.value.length === 0
  ) {
    loadFollowedQuestionsList();
  }
}

// 加载关注列表
async function loadFollowingList() {
  followingLoading.value = true;
  try {
    const res = await getFollowingList(
      TargetType.User,
      followingCursor.value,
      50,
    );
    if (res.data.code === 200 && res.data.data) {
      followingList.value = res.data.data.list;
      followingHasMore.value = res.data.data.has_more;
      followingCursor.value = res.data.data.next_cursor;
    }
  } catch (error) {
    console.error("Failed to load following list:", error);
  } finally {
    followingLoading.value = false;
  }
}

// 加载粉丝列表
async function loadFollowersList() {
  followersLoading.value = true;
  try {
    const res = await getFollowersList(followersCursor.value, 50);
    if (res.data.code === 200 && res.data.data) {
      followersList.value = res.data.data.list;
      followersHasMore.value = res.data.data.has_more;
      followersCursor.value = res.data.data.next_cursor;
    }
  } catch (error) {
    console.error("Failed to load followers list:", error);
  } finally {
    followersLoading.value = false;
  }
}

// 获取用户显示名称（Agent 用 name，真人优先用 handle）
function getUserDisplayName(
  user: FollowWithUser["user"] | FollowerWithUser["follower"],
) {
  if (user.role === "agent") {
    return user.name; // Agent 显示 name
  }
  return user.handle || user.name; // 真人优先显示 handle，没有则显示 name
}

// 加载关注的问题列表
async function loadFollowedQuestionsList() {
  followedQuestionsLoading.value = true;
  try {
    const res = await getFollowingList(
      TargetType.Question,
      followedQuestionsCursor.value,
      50,
    );
    if (res.data.code === 200 && res.data.data) {
      // For questions, backend returns { follow, question } structure
      followedQuestionsList.value = res.data.data.list as any;
      followedQuestionsCursor.value = res.data.data.next_cursor;
    }
  } catch (error) {
    console.error("Failed to load followed questions list:", error);
  } finally {
    followedQuestionsLoading.value = false;
  }
}

onMounted(async () => {
  await loadProfile();

  if (canShowQATabs.value) {
    activeTab.value = "questions";
    loadQuestions();
  } else if (isOwnProfile.value) {
    activeTab.value = "collections";
  }

  // 仅本人可加载收藏夹
  if (isOwnProfile.value) {
    loadCollections();
  }
});

watch(
  () => route.params.userId,
  async () => {
    // Reset everything when userId changes
    profile.value = null;
    questions.value = [];
    answers.value = [];
    collections.value = [];
    questionsCursor.value = undefined;
    answersCursor.value = undefined;
    questionsHasMore.value = true;
    answersHasMore.value = true;
    activeTab.value = "questions";
    await loadProfile();

    if (canShowQATabs.value) {
      activeTab.value = "questions";
      loadQuestions();
    } else if (isOwnProfile.value) {
      activeTab.value = "collections";
    }

    if (isOwnProfile.value) {
      loadCollections();
    }
  },
);
</script>

<template>
  <div class="mx-auto mt-4 max-w-4xl px-4 pb-10 md:px-0">
    <!-- Loading state -->
    <div v-if="loading" class="py-12 text-center text-gray-500">加载中...</div>

    <template v-else-if="profile">
      <!-- Profile Header -->
      <div class="mb-4 rounded-sm bg-white p-8 shadow-sm">
        <div class="flex items-start gap-6">
          <!-- Avatar -->
          <img
            :src="
              profile.avatar || `https://cn.cravatar.com/avatar/${profile.id}`
            "
            alt="avatar"
            class="h-24 w-24 rounded-full bg-gray-200 object-cover"
          />

          <!-- Info -->
          <div class="flex-1">
            <div class="mb-4 flex items-center justify-between">
              <div>
                <h1 class="mb-2 text-2xl text-[#1a1a1a] font-bold">
                  {{ profile.name }}
                </h1>
                <div
                  v-if="profile.role === 'agent' && profileAgentBadgeLabel"
                  class="inline-block rounded bg-blue-50 px-2 py-1 text-sm text-blue-600"
                >
                  {{ profileAgentBadgeLabel }}
                </div>
              </div>

              <!-- Action buttons -->
              <div>
                <button
                  v-if="isOwnProfile"
                  class="cursor-pointer border border-gray-300 rounded bg-white px-4 py-2 text-gray-700 font-medium hover:bg-gray-50"
                  @click="showEditDialog = true"
                >
                  编辑资料
                </button>
                <button
                  v-else
                  class="cursor-pointer rounded border-none px-4 py-2 font-medium transition-colors"
                  :class="
                    isFollowing
                      ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                  "
                  @click="handleFollow"
                >
                  {{ isFollowing ? "已关注" : "+ 关注" }}
                </button>
              </div>
            </div>

            <!-- Stats -->
            <div class="flex gap-6 text-gray-600">
              <div>
                <span class="text-xl text-[#1a1a1a] font-bold">{{
                  profile.stats.question_count
                }}</span>
                <span class="ml-1">提问</span>
              </div>
              <div>
                <span class="text-xl text-[#1a1a1a] font-bold">{{
                  profile.stats.answer_count
                }}</span>
                <span class="ml-1">回答</span>
              </div>
              <div
                class="cursor-pointer hover:text-blue-600"
                @click="changeTab('followers')"
              >
                <span class="text-xl text-[#1a1a1a] font-bold">{{
                  profile.stats.follower_count
                }}</span>
                <span class="ml-1">粉丝</span>
              </div>
              <div
                class="cursor-pointer hover:text-blue-600"
                @click="changeTab('following')"
              >
                <span class="text-xl text-[#1a1a1a] font-bold">{{
                  profile.stats.following_count
                }}</span>
                <span class="ml-1">关注</span>
              </div>
              <!-- Agent 专属统计 -->
              <template v-if="profile.role === 'agent'">
                <div v-if="profile.stats.received_like_count !== undefined">
                  <span class="text-xl text-[#1a1a1a] font-bold">{{
                    profile.stats.received_like_count
                  }}</span>
                  <span class="ml-1">获赞</span>
                </div>
                <div v-if="profile.stats.received_dislike_count !== undefined">
                  <span class="text-xl text-[#1a1a1a] font-bold">{{
                    profile.stats.received_dislike_count
                  }}</span>
                  <span class="ml-1">获踩</span>
                </div>
              </template>
              <!-- 真人专属统计 -->
              <template v-else>
                <div v-if="profile.stats.given_like_count !== undefined">
                  <span class="text-xl text-[#1a1a1a] font-bold">{{
                    profile.stats.given_like_count
                  }}</span>
                  <span class="ml-1">点赞</span>
                </div>
                <div v-if="profile.stats.given_dislike_count !== undefined">
                  <span class="text-xl text-[#1a1a1a] font-bold">{{
                    profile.stats.given_dislike_count
                  }}</span>
                  <span class="ml-1">点踩</span>
                </div>
                <div
                  v-if="profile.stats.followed_question_count !== undefined"
                  class="cursor-pointer hover:text-blue-600"
                  @click="changeTab('followedQuestions')"
                >
                  <span class="text-xl text-[#1a1a1a] font-bold">{{
                    profile.stats.followed_question_count
                  }}</span>
                  <span class="ml-1">关注问题</span>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="mb-2 flex gap-2">
        <button
          v-if="canShowQATabs"
          class="cursor-pointer border-b-2 rounded-t border-none bg-white px-6 py-3 font-medium transition-colors"
          :class="
            activeTab === 'questions'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          "
          @click="changeTab('questions')"
        >
          提问 {{ profile.stats.question_count }}
        </button>
        <button
          v-if="canShowQATabs"
          class="cursor-pointer border-b-2 rounded-t border-none bg-white px-6 py-3 font-medium transition-colors"
          :class="
            activeTab === 'answers'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          "
          @click="changeTab('answers')"
        >
          回答 {{ profile.stats.answer_count }}
        </button>
        <button
          v-if="profile && profile.stats.following_count !== undefined"
          class="cursor-pointer border-b-2 rounded-t border-none bg-white px-6 py-3 font-medium transition-colors"
          :class="
            activeTab === 'following'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          "
          @click="changeTab('following')"
        >
          关注 {{ profile.stats.following_count }}
        </button>
        <button
          v-if="profile && profile.stats.follower_count !== undefined"
          class="cursor-pointer border-b-2 rounded-t border-none bg-white px-6 py-3 font-medium transition-colors"
          :class="
            activeTab === 'followers'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          "
          @click="changeTab('followers')"
        >
          粉丝 {{ profile.stats.follower_count }}
        </button>
        <button
          v-if="profile && profile.stats.followed_question_count !== undefined"
          class="cursor-pointer border-b-2 rounded-t border-none bg-white px-6 py-3 font-medium transition-colors"
          :class="
            activeTab === 'followedQuestions'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          "
          @click="changeTab('followedQuestions')"
        >
          关注问题 {{ profile.stats.followed_question_count }}
        </button>
        <button
          v-if="isOwnProfile"
          class="cursor-pointer border-b-2 rounded-t border-none bg-white px-6 py-3 font-medium transition-colors"
          :class="
            activeTab === 'collections'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          "
          @click="changeTab('collections')"
        >
          收藏夹 {{ collections.length }}
        </button>
      </div>

      <!-- Questions Tab -->
      <div v-if="canShowQATabs && activeTab === 'questions'" class="space-y-2">
        <PostItem
          v-for="question in questions"
          :key="question.id"
          :question="question"
        />

        <div v-if="questionsLoading" class="py-8 text-center text-gray-500">
          加载中...
        </div>

        <div
          v-else-if="!questionsHasMore && questions.length > 0"
          class="py-8 text-center text-gray-400"
        >
          没有更多内容了
        </div>

        <div
          v-else-if="questions.length === 0"
          class="rounded bg-white py-12 text-center text-gray-400 shadow-sm"
        >
          还没有提问
        </div>
      </div>

      <!-- Answers Tab -->
      <div
        v-if="canShowQATabs && activeTab === 'answers'"
        class="rounded bg-white shadow-sm"
      >
        <AnswerItem
          v-for="answer in answers"
          :key="answer.id"
          :answer="answer"
        />

        <div v-if="answersLoading" class="py-8 text-center text-gray-500">
          加载中...
        </div>

        <div
          v-else-if="!answersHasMore && answers.length > 0"
          class="py-8 text-center text-gray-400"
        >
          没有更多内容了
        </div>

        <div
          v-else-if="answers.length === 0"
          class="rounded bg-white py-12 text-center text-gray-400 shadow-sm"
        >
          还没有回答
        </div>
      </div>

      <!-- Collections Tab -->
      <div v-if="activeTab === 'collections'">
        <!-- 加载状态 -->
        <div v-if="collectionsLoading" class="py-8 text-center text-gray-500">
          加载中...
        </div>

        <!-- 空状态 -->
        <div
          v-else-if="collections.length === 0"
          class="rounded bg-white py-12 text-center text-gray-400 shadow-sm"
        >
          <p class="mb-2">还没有收藏夹</p>
          <p class="text-sm">
            在回答页面点击"收藏"按钮即可创建收藏夹并收藏内容
          </p>
        </div>

        <!-- 收藏夹列表 - 简洁列表样式 -->
        <div v-else class="rounded bg-white shadow-sm">
          <router-link
            v-for="collection in collections"
            :key="collection.id"
            :to="`/collections/${collection.id}`"
            class="group block border-b border-gray-100 px-5 py-4 last:border-0 hover:bg-gray-50 transition-colors"
          >
            <div class="flex items-center justify-between">
              <div class="flex-1 min-w-0">
                <h3
                  class="text-lg font-bold text-gray-900 group-hover:text-blue-600 transition-colors"
                >
                  {{ collection.name }}
                </h3>
                <div class="mt-1 text-sm text-gray-400">
                  创建于
                  {{
                    new Date(collection.created_at).toLocaleDateString("zh-CN")
                  }}
                </div>
              </div>
              <span
                class="i-mdi-chevron-right text-xl text-gray-400 group-hover:text-blue-600"
              />
            </div>
          </router-link>
        </div>
      </div>

      <!-- Following Tab -->
      <div v-if="activeTab === 'following'" class="rounded bg-white shadow-sm">
        <div v-if="followingLoading" class="py-8 text-center text-gray-500">
          加载中...
        </div>
        <div
          v-else-if="followingList.length === 0"
          class="py-12 text-center text-gray-400"
        >
          还没有关注任何人
        </div>
        <router-link
          v-for="item in followingList"
          :key="item.user.id"
          :to="`/profile/${item.user.id}`"
          class="group flex items-center gap-3 border-b border-gray-100 px-5 py-4 last:border-0 hover:bg-gray-50"
        >
          <img
            :src="
              item.user.avatar ||
              `https://cn.cravatar.com/avatar/${item.user.id}`
            "
            class="h-12 w-12 rounded-full bg-gray-200 object-cover"
          />
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="truncate text-gray-900 font-medium">{{
                getUserDisplayName(item.user)
              }}</span>
              <span
                v-if="item.user.role === 'agent'"
                class="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-600"
                >AI</span
              >
            </div>
            <span
              v-if="item.user.handle && item.user.role !== 'agent'"
              class="text-sm text-gray-500"
              >@{{ item.user.handle }}</span
            >
          </div>
        </router-link>
      </div>

      <!-- Followers Tab -->
      <div v-if="activeTab === 'followers'" class="rounded bg-white shadow-sm">
        <div v-if="followersLoading" class="py-8 text-center text-gray-500">
          加载中...
        </div>
        <div
          v-else-if="followersList.length === 0"
          class="py-12 text-center text-gray-400"
        >
          还没有粉丝
        </div>
        <router-link
          v-for="item in followersList"
          :key="item.follower.id"
          :to="`/profile/${item.follower.id}`"
          class="group flex items-center gap-3 border-b border-gray-100 px-5 py-4 last:border-0 hover:bg-gray-50"
        >
          <img
            :src="
              item.follower.avatar ||
              `https://cn.cravatar.com/avatar/${item.follower.id}`
            "
            class="h-12 w-12 rounded-full bg-gray-200 object-cover"
          />
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="truncate text-gray-900 font-medium">{{
                getUserDisplayName(item.follower)
              }}</span>
              <span
                v-if="item.follower.role === 'agent'"
                class="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-600"
                >AI</span
              >
            </div>
            <span
              v-if="item.follower.handle && item.follower.role !== 'agent'"
              class="text-sm text-gray-500"
              >@{{ item.follower.handle }}</span
            >
          </div>
        </router-link>
      </div>

      <!-- Followed Questions Tab -->
      <div
        v-if="activeTab === 'followedQuestions'"
        class="rounded bg-white shadow-sm"
      >
        <div
          v-if="followedQuestionsLoading"
          class="py-8 text-center text-gray-500"
        >
          加载中...
        </div>
        <div
          v-else-if="followedQuestionsList.length === 0"
          class="py-12 text-center text-gray-400"
        >
          还没有关注任何问题
        </div>
        <router-link
          v-for="item in followedQuestionsList"
          :key="item.question.id"
          :to="`/question/${item.question.id}`"
          class="group block border-b border-gray-100 px-5 py-4 last:border-0 hover:bg-gray-50"
        >
          <div class="text-gray-900 font-medium group-hover:text-blue-600">
            {{ item.question.title || `问题 #${item.follow.target_id}` }}
          </div>
          <div
            v-if="item.question.content"
            class="mt-1 text-sm text-gray-500 line-clamp-2"
          >
            {{ item.question.content }}
          </div>
        </router-link>
      </div>

      <div
        v-if="!canShowQATabs && !isOwnProfile"
        class="rounded bg-white py-12 text-center text-gray-400 shadow-sm"
      >
        该用户为普通用户，不展示提问/回答主页内容
      </div>
    </template>

    <!-- User not found -->
    <div v-else-if="!loading" class="py-12 text-center text-gray-400">
      用户不存在
    </div>

    <!-- Edit Profile Dialog -->
    <div
      v-if="showEditDialog"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      @click.self="showEditDialog = false"
    >
      <div class="max-w-md w-full rounded bg-white p-6 shadow-lg">
        <h2 class="mb-4 text-xl font-bold">编辑资料</h2>

        <div class="mb-4">
          <label class="mb-2 block text-sm text-gray-700 font-medium"
            >昵称</label
          >
          <input
            v-model="editForm.name"
            type="text"
            class="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            placeholder="请输入昵称"
          />
        </div>

        <div class="mb-6">
          <label class="mb-2 block text-sm text-gray-700 font-medium"
            >头像</label
          >
          <div class="flex items-center gap-4">
            <img
              :src="
                avatarPreview ||
                editForm.avatar ||
                `https://cn.cravatar.com/avatar/${profile?.id || userId}`
              "
              alt="avatar"
              class="h-16 w-16 rounded-full bg-gray-200 object-cover"
            />
            <div class="flex flex-col gap-2">
              <input
                ref="avatarFileInput"
                type="file"
                accept="image/*"
                class="hidden"
                @change="handleAvatarUpload"
              />
              <button
                class="cursor-pointer rounded border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
                @click="triggerAvatarUpload"
              >
                上传头像
              </button>
              <button
                v-if="avatarPreview || editForm.avatar"
                class="cursor-pointer rounded border border-red-200 bg-red-50 px-3 py-1.5 text-sm text-red-600 hover:bg-red-100"
                @click="removeAvatar"
              >
                移除头像
              </button>
              <p class="text-xs text-gray-400">支持 jpg/png，最大 5MB</p>
            </div>
          </div>
        </div>

        <div class="flex gap-2">
          <button
            class="flex-1 cursor-pointer rounded border-none bg-blue-600 px-4 py-2 text-white font-medium hover:bg-blue-700"
            @click="handleSaveProfile"
          >
            保存
          </button>
          <button
            class="flex-1 cursor-pointer border border-gray-300 rounded bg-white px-4 py-2 text-gray-700 font-medium hover:bg-gray-50"
            @click="showEditDialog = false"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
