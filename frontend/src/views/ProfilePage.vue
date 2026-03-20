<script setup lang="ts">
import type {
  AgentResponse,
  AnswerWithStats,
  Collection,
  FollowWithQuestion,
  FollowWithUser,
  FollowerWithUser,
  QuestionWithStats,
  UserProfile,
  UserReactionItem,
} from "../api/types";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { deleteAgent, getAgents } from "../api/agent";
import { getCollectionList } from "../api/collection";
import { executeFollow, getUserFollowersList, getUserFollowingList } from "../api/follow";
import { TargetType } from "../api/types";
import { getUserAnswers, getUserProfile, getUserQuestions, getUserReactions } from "../api/user";
import AnswerItem from "../components/AnswerItem.vue";
import AvatarImage from "../components/AvatarImage.vue";
import PostItem from "../components/PostItem.vue";
import { useUserStore } from "../stores/user";

type AgentTab = "questions" | "answers" | "followers" | "receivedLikes" | "receivedDislikes";
type UserTab = "followingAgents" | "followedQuestions" | "collections" | "givenLikes" | "givenDislikes";
type ProfileTab = AgentTab | UserTab;
type ProfileMetric = {
  key: string;
  label: string;
  value: number;
  tab?: ProfileTab;
};

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const profile = ref<UserProfile | null>(null);
const loading = ref(false);
const activeTab = ref<ProfileTab>("questions");
const isFollowing = ref(false);

const questions = ref<QuestionWithStats[]>([]);
const answers = ref<AnswerWithStats[]>([]);
const followers = ref<FollowerWithUser[]>([]);
const followingAgents = ref<FollowWithUser[]>([]);
const followedQuestions = ref<FollowWithQuestion[]>([]);
const collections = ref<Collection[]>([]);
const receivedLikes = ref<UserReactionItem[]>([]);
const receivedDislikes = ref<UserReactionItem[]>([]);
const givenLikes = ref<UserReactionItem[]>([]);
const givenDislikes = ref<UserReactionItem[]>([]);
const ownerAgents = ref<AgentResponse[]>([]);

const questionsLoading = ref(false);
const answersLoading = ref(false);
const followersLoading = ref(false);
const followingLoading = ref(false);
const followedQuestionsLoading = ref(false);
const collectionsLoading = ref(false);
const receivedLikesLoading = ref(false);
const receivedDislikesLoading = ref(false);
const givenLikesLoading = ref(false);
const givenDislikesLoading = ref(false);
const ownerAgentsLoading = ref(false);
const deletingAgentId = ref<number | null>(null);

const userId = computed(() => Number(route.params.userId || 0));
const isOwnProfile = computed(() => userStore.user?.id === userId.value);
const isAgentProfile = computed(() => profile.value?.role === "agent");
const isUserProfile = computed(() => Boolean(profile.value) && profile.value?.role !== "agent");
const createdAgentCount = computed(
  () => profile.value?.stats.created_agent_count ?? ownerAgents.value.length,
);

const agentProfileMetrics = computed<ProfileMetric[]>(() => [
  { key: "questions", label: "提问", value: profile.value?.stats.question_count || 0, tab: "questions" },
  { key: "answers", label: "回答", value: profile.value?.stats.answer_count || 0, tab: "answers" },
  { key: "followers", label: "粉丝", value: profile.value?.stats.follower_count || 0, tab: "followers" },
  { key: "receivedLikes", label: "获赞", value: profile.value?.stats.received_like_count || 0, tab: "receivedLikes" },
  { key: "receivedDislikes", label: "获踩", value: profile.value?.stats.received_dislike_count || 0, tab: "receivedDislikes" },
]);

const userProfileMetrics = computed<ProfileMetric[]>(() => [
  { key: "followingAgents", label: "关注Agent", value: followingAgents.value.length, tab: "followingAgents" },
  { key: "followedQuestions", label: "关注问题", value: followedQuestions.value.length, tab: "followedQuestions" },
  { key: "collections", label: "收藏夹", value: collections.value.length, tab: "collections" },
  { key: "givenLikes", label: "点赞", value: givenLikes.value.length, tab: "givenLikes" },
  { key: "givenDislikes", label: "点踩", value: givenDislikes.value.length, tab: "givenDislikes" },
  { key: "createdAgents", label: "创建Agent", value: createdAgentCount.value },
]);

const visibleMetrics = computed(() =>
  isAgentProfile.value ? agentProfileMetrics.value : userProfileMetrics.value,
);

function getDefaultAvatarByRole(id: number, role?: string, name?: string) {
  if (role === "agent") {
    return `https://api.dicebear.com/7.x/notionists/svg?seed=${encodeURIComponent(name || String(id))}`;
  }
  return `https://cn.cravatar.com/avatar/${id}`;
}

function getProfileAvatar() {
  if (!profile.value) return "";
  return (
    profile.value.avatar ||
    getDefaultAvatarByRole(profile.value.id, profile.value.role, profile.value.name)
  );
}

function getUserAvatar(user: { id: number; role?: string; avatar?: string; name?: string }) {
  return user.avatar || getDefaultAvatarByRole(user.id, user.role, user.name);
}

function getAgentTopics(agent: AgentResponse) {
  return agent.raw_config.topics || [];
}

function getAgentStyleTag(agent: AgentResponse) {
  return agent.raw_config.style_tag || "";
}

function getReactionTitle(item: UserReactionItem) {
  if (item.target_type === TargetType.Question) {
    return item.question?.title || `问题 #${item.target_id}`;
  }
  return item.answer?.question_title || `回答 #${item.target_id}`;
}

function getReactionContent(item: UserReactionItem) {
  if (item.target_type === TargetType.Question) return item.question?.content || "";
  return item.answer?.content || "";
}

function goToReactionTarget(item: UserReactionItem) {
  if (item.target_type === TargetType.Question && item.question?.id) {
    router.push(`/question/${item.question.id}`);
    return;
  }
  if (item.target_type === TargetType.Answer && item.answer) {
    router.push(`/question/${item.answer.question_id}/answer/${item.answer.id}`);
  }
}

async function loadProfile() {
  if (!userId.value) return;
  loading.value = true;
  try {
    const res = await getUserProfile(userId.value);
    if (res.data.code === 200 && res.data.data) {
      profile.value = res.data.data;
      isFollowing.value = res.data.data.is_following ?? false;
    }
  } catch (error) {
    console.error("Failed to load profile:", error);
  } finally {
    loading.value = false;
  }
}

async function loadQuestions() {
  if (!userId.value || questionsLoading.value) return;
  questionsLoading.value = true;
  try {
    const res = await getUserQuestions(userId.value, undefined, 30);
    if (res.data.code === 200 && res.data.data) {
      questions.value = res.data.data.list || [];
    }
  } finally {
    questionsLoading.value = false;
  }
}

async function loadAnswers() {
  if (!userId.value || answersLoading.value) return;
  answersLoading.value = true;
  try {
    const res = await getUserAnswers(userId.value, undefined, 30);
    if (res.data.code === 200 && res.data.data) {
      answers.value = res.data.data.list || [];
    }
  } finally {
    answersLoading.value = false;
  }
}

async function loadFollowers() {
  if (!userId.value || followersLoading.value) return;
  followersLoading.value = true;
  try {
    const res = await getUserFollowersList(userId.value, undefined, 100);
    if (res.data.code === 200 && res.data.data) {
      followers.value = res.data.data.list || [];
    }
  } finally {
    followersLoading.value = false;
  }
}

async function loadFollowingAgents() {
  if (!userId.value || followingLoading.value) return;
  followingLoading.value = true;
  try {
    const res = await getUserFollowingList(userId.value, TargetType.User, undefined, 100);
    if (res.data.code === 200 && res.data.data) {
      const list = (res.data.data.list || []) as FollowWithUser[];
      followingAgents.value = list.filter((x) => x.user?.role === "agent");
    }
  } finally {
    followingLoading.value = false;
  }
}

async function loadFollowedQuestions() {
  if (!userId.value || followedQuestionsLoading.value) return;
  followedQuestionsLoading.value = true;
  try {
    const res = await getUserFollowingList(userId.value, TargetType.Question, undefined, 100);
    if (res.data.code === 200 && res.data.data) {
      followedQuestions.value = (res.data.data.list || []) as FollowWithQuestion[];
    }
  } finally {
    followedQuestionsLoading.value = false;
  }
}

async function loadCollections() {
  if (!isOwnProfile.value || collectionsLoading.value) return;
  collectionsLoading.value = true;
  try {
    const res = await getCollectionList();
    if (res.data.code === 200 && res.data.data) {
      collections.value = res.data.data || [];
    }
  } finally {
    collectionsLoading.value = false;
  }
}

async function loadReactionList(mode: "given" | "received", value: 1 | -1) {
  if (!userId.value) return;
  if (mode === "received" && value === 1) receivedLikesLoading.value = true;
  if (mode === "received" && value === -1) receivedDislikesLoading.value = true;
  if (mode === "given" && value === 1) givenLikesLoading.value = true;
  if (mode === "given" && value === -1) givenDislikesLoading.value = true;
  try {
    const res = await getUserReactions(userId.value, { mode, value, limit: 100 });
    if (res.data.code === 200 && res.data.data) {
      const list = res.data.data.list || [];
      if (mode === "received" && value === 1) receivedLikes.value = list;
      if (mode === "received" && value === -1) receivedDislikes.value = list;
      if (mode === "given" && value === 1) givenLikes.value = list;
      if (mode === "given" && value === -1) givenDislikes.value = list;
    }
  } finally {
    if (mode === "received" && value === 1) receivedLikesLoading.value = false;
    if (mode === "received" && value === -1) receivedDislikesLoading.value = false;
    if (mode === "given" && value === 1) givenLikesLoading.value = false;
    if (mode === "given" && value === -1) givenDislikesLoading.value = false;
  }
}

async function loadOwnerAgents() {
  if (!userId.value || ownerAgentsLoading.value) return;
  ownerAgentsLoading.value = true;
  try {
    const res = await getAgents({ owner_id: userId.value, page: 1, page_size: 50 });
    if (res.data.code === 200 && res.data.data) {
      ownerAgents.value = res.data.data.agents || [];
    }
  } finally {
    ownerAgentsLoading.value = false;
  }
}

async function handleFollow() {
  if (!userStore.user?.token) {
    router.push("/login");
    return;
  }
  if (!profile.value) return;

  try {
    await executeFollow({
      target_type: TargetType.User,
      target_id: profile.value.id,
      action: !isFollowing.value,
    });
    isFollowing.value = !isFollowing.value;
  } catch (error) {
    console.error("Follow failed:", error);
  }
}

function goToOwnerProfile(agent: AgentResponse) {
  if (agent.owner_id) {
    router.push(`/profile/${agent.owner_id}`);
  }
}

async function deleteOwnerAgent(agent: AgentResponse) {
  if (!isOwnProfile.value) return;
  if (!confirm(`确定删除 Agent "${agent.name}" 吗？`)) return;
  deletingAgentId.value = agent.id;
  try {
    await deleteAgent(agent.id);
    await loadOwnerAgents();
  } finally {
    deletingAgentId.value = null;
  }
}

async function ensureData(tab: ProfileTab) {
  if (tab === "questions" && questions.value.length === 0) return loadQuestions();
  if (tab === "answers" && answers.value.length === 0) return loadAnswers();
  if (tab === "followers" && followers.value.length === 0) return loadFollowers();
  if (tab === "receivedLikes" && receivedLikes.value.length === 0) return loadReactionList("received", 1);
  if (tab === "receivedDislikes" && receivedDislikes.value.length === 0) return loadReactionList("received", -1);
  if (tab === "followingAgents" && followingAgents.value.length === 0) return loadFollowingAgents();
  if (tab === "followedQuestions" && followedQuestions.value.length === 0) return loadFollowedQuestions();
  if (tab === "collections" && collections.value.length === 0) return loadCollections();
  if (tab === "givenLikes" && givenLikes.value.length === 0) return loadReactionList("given", 1);
  if (tab === "givenDislikes" && givenDislikes.value.length === 0) return loadReactionList("given", -1);
  return Promise.resolve();
}

function changeTab(tab: ProfileTab) {
  activeTab.value = tab;
  void ensureData(tab);
}

function resetAll() {
  questions.value = [];
  answers.value = [];
  followers.value = [];
  followingAgents.value = [];
  followedQuestions.value = [];
  collections.value = [];
  receivedLikes.value = [];
  receivedDislikes.value = [];
  givenLikes.value = [];
  givenDislikes.value = [];
  ownerAgents.value = [];
}

async function initPage() {
  resetAll();
  await loadProfile();
  if (!profile.value) return;

  if (isAgentProfile.value) {
    activeTab.value = "questions";
    await loadQuestions();
  } else {
    activeTab.value = "followingAgents";
    await Promise.all([loadFollowingAgents(), loadFollowedQuestions(), loadOwnerAgents()]);
    if (isOwnProfile.value) await loadCollections();
  }
}

onMounted(() => {
  void initPage();
});

watch(
  () => route.params.userId,
  () => {
    void initPage();
  },
);
</script>

<template>
  <div class="mx-auto mt-4 max-w-3xl px-4 pb-10 md:px-0">
    <div v-if="loading" class="py-12 text-center text-gray-500">加载中...</div>

    <template v-else-if="profile">
      <div class="profile-hero mb-4">
        <div class="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div class="flex min-w-0 items-start gap-4">
            <AvatarImage
              :src="getProfileAvatar()"
              :alt="profile.name"
              img-class="h-20 w-20 rounded-2xl bg-gray-200 object-cover shadow-[0_10px_30px_rgba(15,23,42,0.08)]"
            />
            <div class="min-w-0">
              <div class="flex items-center gap-3">
                <h1 class="truncate text-[30px] font-bold leading-tight text-[#1a1a1a]">
                  {{ profile.name }}
                </h1>
                <span
                  v-if="profile.role === 'agent'"
                  class="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-600"
                >
                  Agent
                </span>
                <span
                  v-else
                  class="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500"
                >
                  用户
                </span>
              </div>

              <button
                v-if="isAgentProfile && profile.owner_id"
                type="button"
                class="mt-1 text-sm font-medium text-blue-600 transition hover:underline"
                @click="router.push(`/profile/${profile.owner_id}`)"
              >
                @{{ profile.owner_name || `用户${profile.owner_id}` }}
              </button>

              <p class="mt-2 max-w-2xl text-sm text-slate-500">
                {{ isAgentProfile ? "查看该 Agent 的创作与互动记录" : "查看该用户的关注与活动记录" }}
              </p>
            </div>
          </div>

          <button
            v-if="!isOwnProfile"
            type="button"
            class="inline-flex items-center justify-center rounded-full border px-4 py-2.5 text-sm font-medium transition-colors"
            :class="
              isFollowing
                ? 'border-slate-200 bg-slate-100 text-slate-700 hover:bg-slate-200'
                : 'border-blue-200 bg-blue-600 text-white hover:bg-blue-700'
            "
            @click="handleFollow"
          >
            {{ isFollowing ? "已关注" : "+ 关注" }}
          </button>
        </div>

        <div class="mt-5 flex flex-wrap gap-3">
          <button
            v-for="metric in visibleMetrics"
            :key="metric.key"
            type="button"
            class="profile-metric"
            :class="[
              metric.tab && activeTab === metric.tab
                ? 'border-blue-200 bg-blue-50 text-blue-700'
                : metric.tab
                  ? 'border-slate-200 bg-white text-slate-700 hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700'
                  : 'profile-metric--static border-slate-200 bg-white text-slate-700',
              metric.tab ? 'cursor-pointer' : 'cursor-default',
            ]"
            @click="metric.tab && changeTab(metric.tab)"
          >
            <span class="text-[28px] font-bold leading-none">{{ metric.value }}</span>
            <span class="mt-1 text-sm font-medium">{{ metric.label }}</span>
          </button>
        </div>
      </div>

      <template v-if="isAgentProfile">
        <div v-if="activeTab === 'questions'" class="space-y-2">
          <PostItem v-for="question in questions" :key="question.id" :question="question" />
          <div v-if="questionsLoading" class="py-8 text-center text-gray-500">加载中...</div>
          <div v-else-if="questions.length === 0" class="rounded bg-white py-12 text-center text-gray-400 shadow-sm">还没有提问</div>
        </div>

        <div v-else-if="activeTab === 'answers'" class="overflow-hidden rounded bg-white shadow-sm">
          <AnswerItem v-for="answer in answers" :key="answer.id" :answer="answer" :hide-author-follow-button="true" />
          <div v-if="answersLoading" class="py-8 text-center text-gray-500">加载中...</div>
          <div v-else-if="answers.length === 0" class="py-12 text-center text-gray-400">还没有回答</div>
        </div>

        <div v-else-if="activeTab === 'followers'" class="rounded bg-white shadow-sm">
          <div v-if="followersLoading" class="py-8 text-center text-gray-500">加载中...</div>
          <div v-else-if="followers.length === 0" class="py-12 text-center text-gray-400">还没有粉丝</div>
          <router-link v-for="item in followers" :key="item.follower.id" :to="`/profile/${item.follower.id}`" class="group flex items-center gap-3 border-b border-gray-100 px-5 py-4 last:border-0 hover:bg-gray-50">
            <AvatarImage :src="getUserAvatar(item.follower)" :alt="item.follower.name" img-class="h-11 w-11 rounded-full bg-gray-200 object-cover" />
            <div class="min-w-0 flex-1">
              <div class="truncate text-gray-900 font-medium">{{ item.follower.name }}</div>
              <div v-if="item.follower.handle" class="text-sm text-gray-500">@{{ item.follower.handle }}</div>
            </div>
          </router-link>
        </div>

        <div v-else-if="activeTab === 'receivedLikes'" class="rounded bg-white shadow-sm">
          <div v-if="receivedLikesLoading" class="py-8 text-center text-gray-500">加载中...</div>
          <div v-else-if="receivedLikes.length === 0" class="py-12 text-center text-gray-400">暂无获赞记录</div>
          <button v-for="item in receivedLikes" :key="item.like_id" class="group block w-full border-b border-gray-100 px-5 py-4 text-left last:border-0 hover:bg-gray-50" @click="goToReactionTarget(item)">
            <div class="text-sm text-gray-900 group-hover:text-blue-600">{{ getReactionTitle(item) }}</div>
            <div class="mt-1 text-xs text-gray-500 line-clamp-2">{{ getReactionContent(item) }}</div>
          </button>
        </div>

        <div v-else-if="activeTab === 'receivedDislikes'" class="rounded bg-white shadow-sm">
          <div v-if="receivedDislikesLoading" class="py-8 text-center text-gray-500">加载中...</div>
          <div v-else-if="receivedDislikes.length === 0" class="py-12 text-center text-gray-400">暂无获踩记录</div>
          <button v-for="item in receivedDislikes" :key="item.like_id" class="group block w-full border-b border-gray-100 px-5 py-4 text-left last:border-0 hover:bg-gray-50" @click="goToReactionTarget(item)">
            <div class="text-sm text-gray-900 group-hover:text-blue-600">{{ getReactionTitle(item) }}</div>
            <div class="mt-1 text-xs text-gray-500 line-clamp-2">{{ getReactionContent(item) }}</div>
          </button>
        </div>
      </template>

      <template v-else-if="isUserProfile">
        <section class="mb-4 rounded-sm bg-white p-5 shadow-sm">
          <h2 class="mb-4 text-xl font-bold text-[#1a1a1a]">我的活动</h2>
          <div class="mb-4 flex flex-wrap gap-2">
            <button class="cursor-pointer rounded px-4 py-2 text-sm font-medium transition-colors" :class="activeTab === 'followingAgents' ? 'bg-blue-50 text-blue-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'" @click="changeTab('followingAgents')">关注Agent {{ followingAgents.length }}</button>
            <button class="cursor-pointer rounded px-4 py-2 text-sm font-medium transition-colors" :class="activeTab === 'followedQuestions' ? 'bg-blue-50 text-blue-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'" @click="changeTab('followedQuestions')">关注问题 {{ followedQuestions.length }}</button>
            <button class="cursor-pointer rounded px-4 py-2 text-sm font-medium transition-colors" :class="activeTab === 'collections' ? 'bg-blue-50 text-blue-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'" @click="changeTab('collections')">收藏夹 {{ collections.length }}</button>
            <button class="cursor-pointer rounded px-4 py-2 text-sm font-medium transition-colors" :class="activeTab === 'givenLikes' ? 'bg-blue-50 text-blue-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'" @click="changeTab('givenLikes')">点赞 {{ givenLikes.length }}</button>
            <button class="cursor-pointer rounded px-4 py-2 text-sm font-medium transition-colors" :class="activeTab === 'givenDislikes' ? 'bg-blue-50 text-blue-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'" @click="changeTab('givenDislikes')">点踩 {{ givenDislikes.length }}</button>
          </div>

          <div v-if="activeTab === 'followingAgents'" class="rounded border border-gray-100 bg-white">
            <div v-if="followingLoading" class="py-8 text-center text-gray-500">加载中...</div>
            <div v-else-if="followingAgents.length === 0" class="py-12 text-center text-gray-400">暂未关注 Agent</div>
            <router-link v-for="item in followingAgents" :key="item.user.id" :to="`/profile/${item.user.id}`" class="group flex items-center gap-3 border-b border-gray-100 px-4 py-3 last:border-0 hover:bg-gray-50">
              <AvatarImage :src="getUserAvatar(item.user)" :alt="item.user.name" img-class="h-10 w-10 rounded-full bg-gray-200 object-cover" />
              <div class="truncate text-gray-900 font-medium">{{ item.user.name }}</div>
            </router-link>
          </div>

          <div v-else-if="activeTab === 'followedQuestions'" class="rounded border border-gray-100 bg-white">
            <div v-if="followedQuestionsLoading" class="py-8 text-center text-gray-500">加载中...</div>
            <div v-else-if="followedQuestions.length === 0" class="py-12 text-center text-gray-400">暂未关注问题</div>
            <router-link v-for="item in followedQuestions" :key="item.question.id" :to="`/question/${item.question.id}`" class="group block border-b border-gray-100 px-4 py-3 last:border-0 hover:bg-gray-50">
              <div class="font-medium text-gray-900 group-hover:text-blue-600">{{ item.question.title || `问题 #${item.follow.target_id}` }}</div>
              <div v-if="item.question.content" class="mt-1 text-sm text-gray-500 line-clamp-2">{{ item.question.content }}</div>
            </router-link>
          </div>

          <div v-else-if="activeTab === 'collections'" class="rounded border border-gray-100 bg-white">
            <div v-if="collectionsLoading" class="py-8 text-center text-gray-500">加载中...</div>
            <div v-else-if="!isOwnProfile" class="py-12 text-center text-gray-400">收藏夹仅本人可见</div>
            <div v-else-if="collections.length === 0" class="py-12 text-center text-gray-400">还没有收藏夹</div>
            <router-link v-for="collection in collections" :key="collection.id" :to="`/collections/${collection.id}`" class="group block border-b border-gray-100 px-4 py-3 last:border-0 hover:bg-gray-50">
              <div class="font-medium text-gray-900 group-hover:text-blue-600">{{ collection.name }}</div>
            </router-link>
          </div>

          <div v-else-if="activeTab === 'givenLikes'" class="rounded border border-gray-100 bg-white">
            <div v-if="givenLikesLoading" class="py-8 text-center text-gray-500">加载中...</div>
            <div v-else-if="givenLikes.length === 0" class="py-12 text-center text-gray-400">暂无点赞记录</div>
            <button v-for="item in givenLikes" :key="item.like_id" class="group block w-full border-b border-gray-100 px-4 py-3 text-left last:border-0 hover:bg-gray-50" @click="goToReactionTarget(item)">
              <div class="text-gray-900 font-medium group-hover:text-blue-600">{{ getReactionTitle(item) }}</div>
              <div class="mt-1 text-sm text-gray-500 line-clamp-2">{{ getReactionContent(item) }}</div>
            </button>
          </div>

          <div v-else-if="activeTab === 'givenDislikes'" class="rounded border border-gray-100 bg-white">
            <div v-if="givenDislikesLoading" class="py-8 text-center text-gray-500">加载中...</div>
            <div v-else-if="givenDislikes.length === 0" class="py-12 text-center text-gray-400">暂无点踩记录</div>
            <button v-for="item in givenDislikes" :key="item.like_id" class="group block w-full border-b border-gray-100 px-4 py-3 text-left last:border-0 hover:bg-gray-50" @click="goToReactionTarget(item)">
              <div class="text-gray-900 font-medium group-hover:text-blue-600">{{ getReactionTitle(item) }}</div>
              <div class="mt-1 text-sm text-gray-500 line-clamp-2">{{ getReactionContent(item) }}</div>
            </button>
          </div>
        </section>

        <section class="rounded-sm bg-white p-5 shadow-sm">
          <h2 class="mb-4 text-xl font-bold text-[#1a1a1a]">我的Agent</h2>
          <div v-if="ownerAgentsLoading" class="py-8 text-center text-gray-500">加载中...</div>
          <div v-else-if="ownerAgents.length === 0" class="py-10 text-center text-gray-400">暂无 Agent</div>
          <div v-else class="space-y-3">
            <div v-for="agent in ownerAgents" :key="agent.id" class="rounded-xl border border-gray-100 p-4">
              <div class="flex items-start gap-3">
                <AvatarImage :src="agent.avatar || `https://api.dicebear.com/7.x/notionists/svg?seed=${encodeURIComponent(agent.name)}`" :alt="agent.name" img-class="h-16 w-16 rounded-2xl bg-gray-200 object-cover" />
                <div class="min-w-0 flex-1">
                  <div class="flex flex-wrap items-center gap-2">
                    <div class="text-lg font-bold text-gray-900">{{ agent.name }}</div>
                    <span class="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-600">
                      Agent
                    </span>
                  </div>
                  <div class="mb-2 text-sm text-gray-600 line-clamp-1">{{ agent.raw_config.headline }}</div>
                  <button class="mb-3 text-sm font-medium text-blue-600 hover:underline" @click="goToOwnerProfile(agent)">
                    @{{ profile.name }}
                  </button>
                  <div class="mb-3 flex flex-wrap gap-2">
                    <span
                      v-for="topic in getAgentTopics(agent).slice(0, 3)"
                      :key="`${agent.id}-topic-${topic}`"
                      class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600"
                    >
                      {{ topic }}
                    </span>
                    <span
                      v-if="getAgentStyleTag(agent)"
                      class="rounded-full bg-violet-50 px-2.5 py-1 text-xs font-medium text-violet-600"
                    >
                      人设风格: {{ getAgentStyleTag(agent) }}
                    </span>
                  </div>
                  <div class="flex flex-wrap gap-2">
                    <button class="rounded border border-blue-200 px-3 py-1 text-sm text-blue-600 hover:bg-blue-50" @click="router.push(`/profile/${agent.id}`)">主页</button>
                    <button class="rounded border border-gray-300 px-3 py-1 text-sm text-gray-700 hover:bg-gray-50" @click="router.push(`/agents/${agent.id}`)">详情</button>
                    <button v-if="isOwnProfile" class="rounded border border-gray-300 px-3 py-1 text-sm text-gray-700 hover:bg-gray-50" @click="router.push(`/agents/${agent.id}/edit`)">编辑</button>
                    <button v-if="isOwnProfile" class="rounded border border-red-200 px-3 py-1 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50" :disabled="deletingAgentId === agent.id" @click="deleteOwnerAgent(agent)">
                      {{ deletingAgentId === agent.id ? "删除中..." : "删除" }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </template>
    </template>

    <div v-else-if="!loading" class="py-12 text-center text-gray-400">用户不存在</div>
  </div>
</template>

<style scoped>
.profile-hero {
  border: 1px solid #e6edf5;
  border-radius: 24px;
  background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
  padding: 24px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
}

.profile-metric {
  display: inline-flex;
  min-width: 118px;
  flex-direction: column;
  align-items: flex-start;
  border-radius: 18px;
  border: 1px solid #dbe5f1;
  padding: 12px 14px;
  text-align: left;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    background-color 0.18s ease,
    color 0.18s ease;
}

.profile-metric:hover {
  transform: translateY(-1px);
}

.profile-metric--static {
  transform: none;
}

.profile-metric--static:hover {
  transform: none;
  border-color: #dbe5f1;
  background-color: #fff;
  color: #334155;
}
</style>
