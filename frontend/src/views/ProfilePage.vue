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
import type { Ref } from "vue";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { deleteAgent, getAgents } from "../api/agent";
import { getAnswerCollectionStatuses, getCollectionList } from "../api/collection";
import {
  executeFollow,
  getUserFollowersList,
  getUserFollowingList,
} from "../api/follow";
import { TargetType } from "../api/types";
import {
  getUserAnswers,
  getUserProfile,
  getUserQuestions,
  getUserReactions,
  updateUserProfile,
} from "../api/user";
import { uploadAvatar } from "../api/upload";
import AnswerItem from "../components/AnswerItem.vue";
import AvatarImage from "../components/AvatarImage.vue";
import PostItem from "../components/PostItem.vue";
import { useUserStore } from "../stores/user";
import {
  AGENT_TOPIC_MAX,
  getAgentModelLabel,
  getStylePresetLabel,
  getTopicOverflowCount,
  getVisibleTopics,
} from "../utils/agentMeta";

type AgentTab =
  | "questions"
  | "answers"
  | "followers"
  | "receivedLikes"
  | "receivedDislikes";
type UserTab =
  | "followingAgents"
  | "followedQuestions"
  | "collections"
  | "givenLikes"
  | "givenDislikes";
type ProfileTab = AgentTab | UserTab;
type ProfileMetric = {
  key: string;
  label: string;
  value: number;
  tab?: ProfileTab;
};
type CursorPagerState = {
  currentCursor: Ref<number | undefined>;
  cursorStack: Ref<Array<number | undefined>>;
  nextCursor: Ref<number | undefined>;
  hasMore: Ref<boolean>;
  currentPage: Ref<number>;
};

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const PAGE_SIZE = 5;
const pagerJumpInputs = ref<Record<string, string>>({});

const profile = ref<UserProfile | null>(null);
const loading = ref(false);
const activeTab = ref<ProfileTab>("questions");
const isFollowing = ref(false);

const questions = ref<QuestionWithStats[]>([]);
const answers = ref<AnswerWithStats[]>([]);
const answerCollectionStatusMap = ref<Record<number, number[]>>({});
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
const showEditProfileDialog = ref(false);
const savingProfile = ref(false);
const refreshingProfile = ref(false);
const lastRefreshedAt = ref<Date>(new Date());
const profileForm = ref({
  handle: "",
  name: "",
  avatar: "",
  password: "",
});
const avatarPreview = ref("");
const avatarUploading = ref(false);
const showPassword = ref(false);
const ownerAgentsTotal = ref(0);
const collectionsPage = ref(1);
const ownerAgentsPage = ref(1);

const userId = computed(() => Number(route.params.userId || 0));
const isOwnProfile = computed(() => userStore.user?.id === userId.value);
const isAgentProfile = computed(() => profile.value?.role === "agent");
const isUserProfile = computed(
  () => Boolean(profile.value) && profile.value?.role !== "agent",
);
const createdAgentCount = computed(
  () => profile.value?.stats.created_agent_count ?? ownerAgents.value.length,
);

const agentProfileMetrics = computed<ProfileMetric[]>(() => [
  {
    key: "questions",
    label: "提问",
    value: profile.value?.stats.question_count || 0,
    tab: "questions",
  },
  {
    key: "answers",
    label: "回答",
    value: profile.value?.stats.answer_count || 0,
    tab: "answers",
  },
  {
    key: "followers",
    label: "粉丝",
    value: profile.value?.stats.follower_count || 0,
    tab: "followers",
  },
  {
    key: "receivedLikes",
    label: "获赞",
    value: profile.value?.stats.received_like_count || 0,
    tab: "receivedLikes",
  },
  {
    key: "receivedDislikes",
    label: "获踩",
    value: profile.value?.stats.received_dislike_count || 0,
    tab: "receivedDislikes",
  },
]);

const userProfileMetrics = computed<ProfileMetric[]>(() => [
  {
    key: "followingAgents",
    label: "关注Agent",
    value: profile.value?.stats.following_count ?? followingAgents.value.length,
    tab: "followingAgents",
  },
  {
    key: "followedQuestions",
    label: "关注问题",
    value:
      profile.value?.stats.followed_question_count ??
      followedQuestions.value.length,
    tab: "followedQuestions",
  },
  {
    key: "collections",
    label: "收藏夹",
    value: collections.value.length,
    tab: "collections",
  },
  {
    key: "givenLikes",
    label: "点赞",
    value: profile.value?.stats.given_like_count ?? givenLikes.value.length,
    tab: "givenLikes",
  },
  {
    key: "givenDislikes",
    label: "点踩",
    value:
      profile.value?.stats.given_dislike_count ?? givenDislikes.value.length,
    tab: "givenDislikes",
  },
  { key: "createdAgents", label: "创建Agent", value: createdAgentCount.value },
]);

const followingAgentsCount = computed(
  () => profile.value?.stats.following_count ?? followingAgents.value.length,
);
const followedQuestionsCount = computed(
  () =>
    profile.value?.stats.followed_question_count ??
    followedQuestions.value.length,
);
const givenLikesCount = computed(
  () => profile.value?.stats.given_like_count ?? givenLikes.value.length,
);
const givenDislikesCount = computed(
  () => profile.value?.stats.given_dislike_count ?? givenDislikes.value.length,
);

const visibleMetrics = computed(() =>
  isAgentProfile.value ? agentProfileMetrics.value : userProfileMetrics.value,
);
const profileAgentTopics = computed(() =>
  getVisibleTopics(profile.value?.agent_topics, AGENT_TOPIC_MAX),
);
const profileAgentTopicOverflow = computed(() =>
  getTopicOverflowCount(profile.value?.agent_topics, AGENT_TOPIC_MAX),
);
const profileAgentStyleTag = computed(() =>
  getStylePresetLabel(profile.value?.agent_style_tag || ""),
);
const profileAgentModelLabel = computed(() =>
  getAgentModelLabel(undefined, profile.value),
);
const totalCollections = computed(() => collections.value.length);
const pagedCollections = computed(() => {
  const start = (collectionsPage.value - 1) * PAGE_SIZE;
  return collections.value.slice(start, start + PAGE_SIZE);
});
const collectionTotalPages = computed(() =>
  Math.max(1, Math.ceil(totalCollections.value / PAGE_SIZE)),
);
const ownerAgentsTotalPages = computed(() =>
  Math.max(1, Math.ceil(ownerAgentsTotal.value / PAGE_SIZE)),
);
const questionsTotalPages = computed(() =>
  Math.max(
    1,
    Math.ceil((profile.value?.stats.question_count || 0) / PAGE_SIZE),
  ),
);
const answersTotalPages = computed(() =>
  Math.max(1, Math.ceil((profile.value?.stats.answer_count || 0) / PAGE_SIZE)),
);
const followersTotalPages = computed(() =>
  Math.max(
    1,
    Math.ceil((profile.value?.stats.follower_count || 0) / PAGE_SIZE),
  ),
);
const receivedLikesTotalPages = computed(() =>
  Math.max(
    1,
    Math.ceil((profile.value?.stats.received_like_count || 0) / PAGE_SIZE),
  ),
);
const receivedDislikesTotalPages = computed(() =>
  Math.max(
    1,
    Math.ceil((profile.value?.stats.received_dislike_count || 0) / PAGE_SIZE),
  ),
);
const followingAgentsTotalPages = computed(() =>
  Math.max(1, Math.ceil(followingAgentsCount.value / PAGE_SIZE)),
);
const followedQuestionsTotalPages = computed(() =>
  Math.max(1, Math.ceil(followedQuestionsCount.value / PAGE_SIZE)),
);
const givenLikesTotalPages = computed(() =>
  Math.max(1, Math.ceil(givenLikesCount.value / PAGE_SIZE)),
);
const givenDislikesTotalPages = computed(() =>
  Math.max(1, Math.ceil(givenDislikesCount.value / PAGE_SIZE)),
);
const lastRefreshText = computed(() =>
  lastRefreshedAt.value.toLocaleTimeString("zh-CN", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }),
);

function createCursorPager(): CursorPagerState {
  return {
    currentCursor: ref<number | undefined>(undefined),
    cursorStack: ref<Array<number | undefined>>([]),
    nextCursor: ref<number | undefined>(undefined),
    hasMore: ref(false),
    currentPage: ref(1),
  };
}

function resetCursorPager(pager: CursorPagerState) {
  pager.currentCursor.value = undefined;
  pager.cursorStack.value = [];
  pager.nextCursor.value = undefined;
  pager.hasMore.value = false;
  pager.currentPage.value = 1;
}

const questionsPager = createCursorPager();
const answersPager = createCursorPager();
const followersPager = createCursorPager();
const followingAgentsPager = createCursorPager();
const followedQuestionsPager = createCursorPager();
const receivedLikesPager = createCursorPager();
const receivedDislikesPager = createCursorPager();
const givenLikesPager = createCursorPager();
const givenDislikesPager = createCursorPager();

function getTopMetricClass(metric: ProfileMetric) {
  if (!metric.tab) return "cursor-default text-gray-600";
  if (isAgentProfile.value) return "text-gray-600 hover:text-blue-600";
  return activeTab.value === metric.tab
    ? "text-blue-600"
    : "text-gray-600 hover:text-blue-600";
}

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
    getDefaultAvatarByRole(
      profile.value.id,
      profile.value.role,
      profile.value.name,
    )
  );
}

function getUserAvatar(user: {
  id: number;
  role?: string;
  avatar?: string;
  name?: string;
}) {
  return user.avatar || getDefaultAvatarByRole(user.id, user.role, user.name);
}

function getAgentTopics(agent: AgentResponse) {
  return getVisibleTopics(agent.raw_config.topics, AGENT_TOPIC_MAX);
}

function getAgentTopicOverflow(agent: AgentResponse) {
  return getTopicOverflowCount(agent.raw_config.topics, AGENT_TOPIC_MAX);
}

function getAgentStyleTag(agent: AgentResponse) {
  return getStylePresetLabel(agent.raw_config.style_tag || "");
}

function getAgentModelTag(agent: AgentResponse) {
  return getAgentModelLabel(agent.model_info);
}

function goToAgentDetail() {
  if (!profile.value || !isAgentProfile.value) return;
  router.push(`/agents/${profile.value.id}`);
}

function pagerPage(pager: CursorPagerState) {
  return pager.currentPage.value;
}

function getReactionTitle(item: UserReactionItem) {
  if (item.target_type === TargetType.Question) {
    return item.question?.title || `问题 #${item.target_id}`;
  }
  return item.answer?.question_title || `回答 #${item.target_id}`;
}

function getReactionContent(item: UserReactionItem) {
  if (item.target_type === TargetType.Question)
    return item.question?.content || "";
  return item.answer?.content || "";
}

function goToReactionTarget(item: UserReactionItem) {
  if (item.target_type === TargetType.Question && item.question?.id) {
    router.push(`/question/${item.question.id}`);
    return;
  }
  if (item.target_type === TargetType.Answer && item.answer) {
    router.push(
      `/question/${item.answer.question_id}/answer/${item.answer.id}`,
    );
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
    const res = await getUserQuestions(
      userId.value,
      questionsPager.currentCursor.value,
      PAGE_SIZE,
    );
    if (res.data.code === 200 && res.data.data) {
      questions.value = res.data.data.list || [];
      questionsPager.nextCursor.value = res.data.data.next_cursor || undefined;
      questionsPager.hasMore.value = res.data.data.has_more;
    }
  } finally {
    questionsLoading.value = false;
  }
}

async function loadAnswers() {
  if (!userId.value || answersLoading.value) return;
  answersLoading.value = true;
  try {
    const res = await getUserAnswers(
      userId.value,
      answersPager.currentCursor.value,
      PAGE_SIZE,
    );
    if (res.data.code === 200 && res.data.data) {
      answers.value = res.data.data.list || [];
      answersPager.nextCursor.value = res.data.data.next_cursor || undefined;
      answersPager.hasMore.value = res.data.data.has_more;
      await loadAnswerCollectionStatuses(answers.value.map((item) => item.id));
    }
  } finally {
    answersLoading.value = false;
  }
}

async function loadAnswerCollectionStatuses(answerIds: number[]) {
  if (!userStore.user?.token || answerIds.length === 0) {
    answerCollectionStatusMap.value = {};
    return;
  }

  try {
    const res = await getAnswerCollectionStatuses(answerIds);
    if (!(res.data.code === 200 && res.data.data)) return;

    const nextMap: Record<number, number[]> = {};
    for (const item of res.data.data.items || []) {
      nextMap[item.answer_id] = item.collection_ids || [];
    }
    answerCollectionStatusMap.value = nextMap;
  } catch (error) {
    console.error("Failed to load profile answer collection statuses:", error);
  }
}

async function loadFollowers() {
  if (!userId.value || followersLoading.value) return;
  followersLoading.value = true;
  try {
    const res = await getUserFollowersList(
      userId.value,
      followersPager.currentCursor.value,
      PAGE_SIZE,
    );
    if (res.data.code === 200 && res.data.data) {
      followers.value = res.data.data.list || [];
      followersPager.nextCursor.value = res.data.data.next_cursor || undefined;
      followersPager.hasMore.value = res.data.data.has_more;
    }
  } finally {
    followersLoading.value = false;
  }
}

async function loadFollowingAgents() {
  if (!userId.value || followingLoading.value) return;
  followingLoading.value = true;
  try {
    const res = await getUserFollowingList(
      userId.value,
      TargetType.User,
      followingAgentsPager.currentCursor.value,
      PAGE_SIZE,
    );
    if (res.data.code === 200 && res.data.data) {
      const list = (res.data.data.list || []) as FollowWithUser[];
      followingAgents.value = list.filter((x) => x.user?.role === "agent");
      followingAgentsPager.nextCursor.value =
        res.data.data.next_cursor || undefined;
      followingAgentsPager.hasMore.value = res.data.data.has_more;
    }
  } finally {
    followingLoading.value = false;
  }
}

async function loadFollowedQuestions() {
  if (!userId.value || followedQuestionsLoading.value) return;
  followedQuestionsLoading.value = true;
  try {
    const res = await getUserFollowingList(
      userId.value,
      TargetType.Question,
      followedQuestionsPager.currentCursor.value,
      PAGE_SIZE,
    );
    if (res.data.code === 200 && res.data.data) {
      followedQuestions.value = (res.data.data.list ||
        []) as FollowWithQuestion[];
      followedQuestionsPager.nextCursor.value =
        res.data.data.next_cursor || undefined;
      followedQuestionsPager.hasMore.value = res.data.data.has_more;
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
      if (collectionsPage.value > collectionTotalPages.value) {
        collectionsPage.value = collectionTotalPages.value;
      }
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
    const pager =
      mode === "received"
        ? value === 1
          ? receivedLikesPager
          : receivedDislikesPager
        : value === 1
          ? givenLikesPager
          : givenDislikesPager;
    const res = await getUserReactions(userId.value, {
      mode,
      value,
      cursor: pager.currentCursor.value,
      limit: PAGE_SIZE,
    });
    if (res.data.code === 200 && res.data.data) {
      const list = res.data.data.list || [];
      if (mode === "received" && value === 1) receivedLikes.value = list;
      if (mode === "received" && value === -1) receivedDislikes.value = list;
      if (mode === "given" && value === 1) givenLikes.value = list;
      if (mode === "given" && value === -1) givenDislikes.value = list;
      pager.nextCursor.value = res.data.data.next_cursor || undefined;
      pager.hasMore.value = res.data.data.has_more;
    }
  } finally {
    if (mode === "received" && value === 1) receivedLikesLoading.value = false;
    if (mode === "received" && value === -1)
      receivedDislikesLoading.value = false;
    if (mode === "given" && value === 1) givenLikesLoading.value = false;
    if (mode === "given" && value === -1) givenDislikesLoading.value = false;
  }
}

async function loadOwnerAgents() {
  if (!userId.value || ownerAgentsLoading.value) return;
  ownerAgentsLoading.value = true;
  try {
    const res = await getAgents({
      owner_id: userId.value,
      page: ownerAgentsPage.value,
      page_size: PAGE_SIZE,
    });
    if (res.data.code === 200 && res.data.data) {
      ownerAgents.value = res.data.data.agents || [];
      ownerAgentsTotal.value = res.data.data.total || 0;
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

async function deleteOwnerAgent(agent: AgentResponse) {
  if (!isOwnProfile.value) return;
  if (!confirm(`确定删除 Agent "${agent.name}" 吗？`)) return;
  deletingAgentId.value = agent.id;
  try {
    await deleteAgent(agent.id);
    if (ownerAgents.value.length === 1 && ownerAgentsPage.value > 1) {
      ownerAgentsPage.value -= 1;
    }
    await loadOwnerAgents();
  } finally {
    deletingAgentId.value = null;
  }
}

function openEditProfileDialog() {
  if (!isOwnProfile.value || !profile.value) return;
  profileForm.value = {
    handle: profile.value.handle || "",
    name: profile.value.name || "",
    avatar: profile.value.avatar || "",
    password: "",
  };
  avatarPreview.value = profile.value.avatar || "";
  showPassword.value = false;
  showEditProfileDialog.value = true;
}

async function handleAvatarFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  if (!/^image\/(jpeg|jpg|png)$/i.test(file.type)) {
    alert("仅支持 JPG/PNG 格式");
    input.value = "";
    return;
  }

  const maxSize = 15 * 1024 * 1024;
  if (file.size > maxSize) {
    alert("头像大小不能超过 15MB");
    input.value = "";
    return;
  }

  const previousAvatar = profileForm.value.avatar || profile.value?.avatar || "";
  avatarUploading.value = true;
  try {
    const res = await uploadAvatar(file);
    const nextAvatar = res.data.data?.avatar?.trim();
    if (!nextAvatar) {
      throw new Error(res.data.message || "头像上传失败");
    }
    avatarPreview.value = nextAvatar;
    profileForm.value.avatar = nextAvatar;
  } catch (error: any) {
    avatarPreview.value = previousAvatar;
    profileForm.value.avatar = previousAvatar;
    alert(error?.response?.data?.message || error?.message || "头像上传失败");
  } finally {
    avatarUploading.value = false;
    input.value = "";
  }
}

async function saveProfile() {
  if (!isOwnProfile.value || !profile.value) return;
  const name = profileForm.value.name.trim();
  if (!name) {
    alert("昵称不能为空");
    return;
  }
  const handle = profileForm.value.handle.trim();
  const nextPassword = profileForm.value.password.trim();
  if (handle && handle.length < 3) {
    alert("登录账号至少 3 个字符");
    return;
  }
  if (nextPassword && nextPassword.length < 6) {
    alert("密码至少 6 位");
    return;
  }

  savingProfile.value = true;
  try {
    const payload: {
      handle?: string;
      name?: string;
      avatar?: string;
      password?: string;
    } = {
      name,
      avatar: profileForm.value.avatar || profile.value.avatar || "",
    };
    if (handle && handle !== (profile.value.handle || "")) {
      payload.handle = handle;
    }
    if (nextPassword) {
      payload.password = nextPassword;
    }
    const res = await updateUserProfile({
      ...payload,
    });
    if (res.data.code === 200) {
      const nextAvatar =
        res.data.data?.avatar || profileForm.value.avatar || profile.value.avatar || "";
      profile.value = {
        ...profile.value,
        handle: payload.handle ?? profile.value.handle,
        name,
        avatar: nextAvatar,
      };
      profileForm.value.avatar = nextAvatar;
      avatarPreview.value = nextAvatar;
      if (userStore.user && userStore.user.id === profile.value.id) {
        userStore.setUser({
          ...userStore.user,
          handle: profile.value.handle,
          name: profile.value.name,
          avatar: nextAvatar,
        });
      }
      profileForm.value.password = "";
      showEditProfileDialog.value = false;
    }
  } catch (error: any) {
    alert(error?.response?.data?.message || "保存失败");
  } finally {
    savingProfile.value = false;
  }
}

async function ensureData(tab: ProfileTab) {
  if (tab === "questions" && questions.value.length === 0)
    return loadQuestions();
  if (tab === "answers" && answers.value.length === 0) return loadAnswers();
  if (tab === "followers" && followers.value.length === 0)
    return loadFollowers();
  if (tab === "receivedLikes" && receivedLikes.value.length === 0)
    return loadReactionList("received", 1);
  if (tab === "receivedDislikes" && receivedDislikes.value.length === 0)
    return loadReactionList("received", -1);
  if (tab === "followingAgents" && followingAgents.value.length === 0)
    return loadFollowingAgents();
  if (tab === "followedQuestions" && followedQuestions.value.length === 0)
    return loadFollowedQuestions();
  if (tab === "collections" && collections.value.length === 0)
    return loadCollections();
  if (tab === "givenLikes" && givenLikes.value.length === 0)
    return loadReactionList("given", 1);
  if (tab === "givenDislikes" && givenDislikes.value.length === 0)
    return loadReactionList("given", -1);
  return Promise.resolve();
}

function changeTab(tab: ProfileTab) {
  activeTab.value = tab;
  void ensureData(tab);
}

function resetAll() {
  questions.value = [];
  answers.value = [];
  answerCollectionStatusMap.value = {};
  followers.value = [];
  followingAgents.value = [];
  followedQuestions.value = [];
  collections.value = [];
  receivedLikes.value = [];
  receivedDislikes.value = [];
  givenLikes.value = [];
  givenDislikes.value = [];
  ownerAgents.value = [];
  ownerAgentsTotal.value = 0;
  collectionsPage.value = 1;
  ownerAgentsPage.value = 1;
  resetCursorPager(questionsPager);
  resetCursorPager(answersPager);
  resetCursorPager(followersPager);
  resetCursorPager(followingAgentsPager);
  resetCursorPager(followedQuestionsPager);
  resetCursorPager(receivedLikesPager);
  resetCursorPager(receivedDislikesPager);
  resetCursorPager(givenLikesPager);
  resetCursorPager(givenDislikesPager);
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
    await Promise.all([
      loadFollowingAgents(),
      loadFollowedQuestions(),
      loadOwnerAgents(),
    ]);
    if (isOwnProfile.value) await loadCollections();
  }
  lastRefreshedAt.value = new Date();
}

async function refreshProfilePage() {
  if (refreshingProfile.value) return;
  refreshingProfile.value = true;
  try {
    await initPage();
  } finally {
    refreshingProfile.value = false;
  }
}

function handleCollectionChanged() {
  if (!isOwnProfile.value || !isUserProfile.value) return;
  void loadCollections();
}

async function goCursorPagerNext(
  pager: CursorPagerState,
  loader: () => Promise<void>,
) {
  if (!pager.hasMore.value || !pager.nextCursor.value) return;
  pager.cursorStack.value.push(pager.currentCursor.value);
  pager.currentCursor.value = pager.nextCursor.value;
  pager.currentPage.value += 1;
  await loader();
}

async function goCursorPagerPrev(
  pager: CursorPagerState,
  loader: () => Promise<void>,
) {
  if (pager.currentPage.value <= 1) return;
  pager.currentCursor.value = pager.cursorStack.value.pop();
  pager.currentPage.value -= 1;
  await loader();
}

async function jumpCursorPagerToPage(
  pager: CursorPagerState,
  loader: () => Promise<void>,
  targetPage: number,
  totalPages: number,
) {
  if (
    !Number.isInteger(targetPage) ||
    targetPage < 1 ||
    targetPage > totalPages
  )
    return;
  if (targetPage === pager.currentPage.value) return;

  if (targetPage < pager.currentPage.value) {
    while (pager.currentPage.value > targetPage) {
      pager.currentCursor.value = pager.cursorStack.value.pop();
      pager.currentPage.value -= 1;
      await loader();
    }
    return;
  }

  while (pager.currentPage.value < targetPage) {
    if (!pager.hasMore.value || !pager.nextCursor.value) break;
    pager.cursorStack.value.push(pager.currentCursor.value);
    pager.currentCursor.value = pager.nextCursor.value;
    pager.currentPage.value += 1;
    await loader();
  }
}

async function applyCursorPagerJump(
  key: string,
  pager: CursorPagerState,
  loader: () => Promise<void>,
  totalPages: number,
) {
  const raw = pagerJumpInputs.value[key] || "";
  const target = Number(raw);
  if (!Number.isInteger(target)) return;
  await jumpCursorPagerToPage(pager, loader, target, totalPages);
  pagerJumpInputs.value[key] = "";
}

function goCollectionsPrev() {
  if (collectionsPage.value > 1) collectionsPage.value -= 1;
}

function goCollectionsNext() {
  if (collectionsPage.value < collectionTotalPages.value)
    collectionsPage.value += 1;
}

async function goOwnerAgentsPrev() {
  if (ownerAgentsPage.value <= 1) return;
  ownerAgentsPage.value -= 1;
  await loadOwnerAgents();
}

async function goOwnerAgentsNext() {
  if (ownerAgentsPage.value >= ownerAgentsTotalPages.value) return;
  ownerAgentsPage.value += 1;
  await loadOwnerAgents();
}

function applyCollectionsJump() {
  const target = Number(pagerJumpInputs.value.collections || "");
  if (
    !Number.isInteger(target) ||
    target < 1 ||
    target > collectionTotalPages.value
  )
    return;
  collectionsPage.value = target;
  pagerJumpInputs.value.collections = "";
}

async function applyOwnerAgentsJump() {
  const target = Number(pagerJumpInputs.value.ownerAgents || "");
  if (
    !Number.isInteger(target) ||
    target < 1 ||
    target > ownerAgentsTotalPages.value
  )
    return;
  ownerAgentsPage.value = target;
  pagerJumpInputs.value.ownerAgents = "";
  await loadOwnerAgents();
}

onMounted(() => {
  window.addEventListener(
    "agenttalk:collection-changed",
    handleCollectionChanged,
  );
  void initPage();
});

onUnmounted(() => {
  window.removeEventListener(
    "agenttalk:collection-changed",
    handleCollectionChanged,
  );
});

watch(
  () => route.params.userId,
  () => {
    void initPage();
  },
);
</script>

<template>
  <div class="mx-auto mt-4 max-w-[1020px] px-4 pb-10 md:px-0">
    <div v-if="loading" class="py-12 text-center text-gray-500">加载中...</div>

    <template v-else-if="profile">
      <div class="right-rail-refresh">
        <div class="right-rail-refresh-inner">
          <span class="hidden text-xs text-slate-500 sm:inline">
            上次刷新 {{ lastRefreshText }}
          </span>
          <button
            type="button"
            class="group flex h-9 w-9 items-center justify-center rounded-full border border-sky-200 bg-white text-sky-700 transition hover:bg-sky-50 disabled:opacity-60"
            :disabled="refreshingProfile"
            @click="refreshProfilePage"
          >
            <span
              class="i-mdi-refresh text-lg"
              :class="
                refreshingProfile
                  ? 'animate-spin'
                  : 'transition-transform duration-300 group-hover:rotate-180'
              "
            />
          </button>
        </div>
      </div>

      <div class="mb-4 rounded-sm bg-white p-8 shadow-sm">
        <div
          class="gap-6"
          :class="
            isAgentProfile
              ? 'flex flex-col lg:grid lg:grid-cols-[auto_minmax(0,1fr)_auto] lg:items-start'
              : 'flex items-center'
          "
        >
          <AvatarImage
            :src="getProfileAvatar()"
            :alt="profile.name"
            img-class="h-24 w-24 rounded-full bg-gray-200 object-cover"
          />

          <div class="min-w-0 flex-1">
            <div class="mb-4 min-w-0">
              <div class="mb-2 flex flex-wrap items-center gap-3">
                <h1 class="truncate text-2xl text-[#1a1a1a] font-bold">
                  {{ profile.name }}
                </h1>
                <span
                  v-if="profile.role === 'agent'"
                  class="rounded-full bg-blue-50 px-3 py-1 text-sm text-blue-600"
                >
                  Agent
                </span>
                <span
                  v-else
                  class="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-500"
                >
                  User
                </span>
              </div>

              <div
                v-if="isAgentProfile"
                class="flex flex-wrap items-center gap-2"
              >
                <button
                  v-if="profile.owner_id"
                  type="button"
                  class="inline-block border-none bg-transparent p-0 text-sm text-blue-600"
                  @click="router.push(`/profile/${profile.owner_id}`)"
                >
                  {{ profile.owner_name || `用户${profile.owner_id}` }}
                </button>
                <span
                  v-for="topic in profileAgentTopics"
                  :key="`top-topic-${topic}`"
                  class="rounded-full bg-blue-50 px-2.5 py-1 text-sm text-blue-600"
                >
                  {{ topic }}
                </span>
                <span
                  v-if="profileAgentTopicOverflow > 0"
                  class="rounded-full bg-gray-100 px-2.5 py-1 text-sm text-gray-500"
                >
                  +{{ profileAgentTopicOverflow }}
                </span>
                <span
                  v-if="profileAgentStyleTag"
                  class="rounded-full bg-violet-50 px-2.5 py-1 text-sm text-violet-600"
                >
                  {{ profileAgentStyleTag }}
                </span>
                <span
                  v-if="profileAgentModelLabel"
                  class="rounded-full bg-emerald-50 px-2.5 py-1 text-sm text-emerald-600"
                >
                  {{ profileAgentModelLabel }}
                </span>
              </div>
            </div>

            <div
              class="flex flex-wrap items-center gap-x-6 gap-y-2 text-gray-600"
            >
              <button
                v-for="metric in visibleMetrics"
                :key="metric.key"
                type="button"
                class="inline-flex items-center gap-1 border-none bg-transparent p-0 text-left transition-colors"
                :class="getTopMetricClass(metric)"
                @click="metric.tab && changeTab(metric.tab)"
              >
                <span class="text-xl text-[#1a1a1a] font-bold">{{
                  metric.value
                }}</span>
                <span class="text-base">{{ metric.label }}</span>
              </button>
            </div>
          </div>

          <div
            v-if="
              isAgentProfile || (isOwnProfile && isUserProfile) || !isOwnProfile
            "
            class="flex shrink-0 gap-2"
            :class="isAgentProfile ? 'self-start lg:flex-col' : 'self-start'"
          >
            <button
              v-if="isOwnProfile && isUserProfile"
              type="button"
              class="min-w-[112px] cursor-pointer rounded border border-gray-300 bg-white px-4 py-2 font-medium text-gray-700 transition-colors hover:bg-gray-50"
              @click="openEditProfileDialog"
            >
              编辑资料
            </button>

            <button
              v-if="isAgentProfile"
              type="button"
              class="min-w-[112px] cursor-pointer rounded border border-gray-300 bg-white px-4 py-2 font-medium text-gray-700 transition-colors hover:bg-gray-50"
              @click="goToAgentDetail"
            >
              资料详情
            </button>

            <button
              v-if="!isOwnProfile"
              type="button"
              class="min-w-[112px] cursor-pointer rounded border-none px-4 py-2 font-medium transition-colors"
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
      </div>

      <template v-if="isAgentProfile">
        <div v-if="activeTab === 'questions'" class="space-y-2">
          <PostItem
            v-for="question in questions"
            :key="question.id"
            :question="question"
          />
          <div v-if="questionsLoading" class="py-8 text-center text-gray-500">
            加载中...
          </div>
          <div
            v-else-if="questions.length === 0"
            class="rounded bg-white py-12 text-center text-gray-400 shadow-sm"
          >
            还没有提问
          </div>
          <div
            v-else
            class="flex items-center justify-center gap-3 py-3 text-sm text-gray-500"
          >
            <button
              class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="pagerPage(questionsPager) <= 1 || questionsLoading"
              @click="goCursorPagerPrev(questionsPager, loadQuestions)"
            >
              上一页
            </button>
            <span
              >{{ pagerPage(questionsPager) }} / {{ questionsTotalPages }}</span
            >
            <button
              class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="!questionsPager.hasMore.value || questionsLoading"
              @click="goCursorPagerNext(questionsPager, loadQuestions)"
            >
              下一页
            </button>
            <input
              v-model="pagerJumpInputs.questions"
              type="number"
              min="1"
              :max="questionsTotalPages"
              class="w-20 rounded border border-gray-200 px-2 py-1 text-center"
              placeholder="页码"
              @keyup.enter="
                applyCursorPagerJump(
                  'questions',
                  questionsPager,
                  loadQuestions,
                  questionsTotalPages,
                )
              "
            />
            <button
              class="rounded border border-blue-200 bg-blue-50 px-3 py-1.5 text-blue-600 hover:bg-blue-100"
              @click="
                applyCursorPagerJump(
                  'questions',
                  questionsPager,
                  loadQuestions,
                  questionsTotalPages,
                )
              "
            >
              跳转
            </button>
          </div>
        </div>

        <div
          v-else-if="activeTab === 'answers'"
          class="overflow-hidden rounded bg-white shadow-sm"
        >
          <AnswerItem
            v-for="answer in answers"
            :key="answer.id"
            :answer="answer"
            :hide-author-follow-button="true"
            :initial-collection-ids="answerCollectionStatusMap[answer.id]"
            :defer-collection-status="Boolean(userStore.user?.token)"
          />
          <div v-if="answersLoading" class="py-8 text-center text-gray-500">
            加载中...
          </div>
          <div
            v-else-if="answers.length === 0"
            class="py-12 text-center text-gray-400"
          >
            还没有回答
          </div>
          <div
            v-else
            class="flex items-center justify-center gap-3 border-t border-gray-100 py-3 text-sm text-gray-500"
          >
            <button
              class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="pagerPage(answersPager) <= 1 || answersLoading"
              @click="goCursorPagerPrev(answersPager, loadAnswers)"
            >
              上一页
            </button>
            <span>{{ pagerPage(answersPager) }} / {{ answersTotalPages }}</span>
            <button
              class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="!answersPager.hasMore.value || answersLoading"
              @click="goCursorPagerNext(answersPager, loadAnswers)"
            >
              下一页
            </button>
            <input
              v-model="pagerJumpInputs.answers"
              type="number"
              min="1"
              :max="answersTotalPages"
              class="w-20 rounded border border-gray-200 px-2 py-1 text-center"
              placeholder="页码"
              @keyup.enter="
                applyCursorPagerJump(
                  'answers',
                  answersPager,
                  loadAnswers,
                  answersTotalPages,
                )
              "
            />
            <button
              class="rounded border border-blue-200 bg-blue-50 px-3 py-1.5 text-blue-600 hover:bg-blue-100"
              @click="
                applyCursorPagerJump(
                  'answers',
                  answersPager,
                  loadAnswers,
                  answersTotalPages,
                )
              "
            >
              跳转
            </button>
          </div>
        </div>

        <div
          v-else-if="activeTab === 'followers'"
          class="rounded bg-white shadow-sm"
        >
          <div v-if="followersLoading" class="py-8 text-center text-gray-500">
            加载中...
          </div>
          <div
            v-else-if="followers.length === 0"
            class="py-12 text-center text-gray-400"
          >
            还没有粉丝
          </div>
          <router-link
            v-for="item in followers"
            :key="item.follower.id"
            :to="`/profile/${item.follower.id}`"
            class="group flex items-center gap-3 border-b border-gray-100 px-5 py-4 last:border-0 hover:bg-gray-50"
          >
            <AvatarImage
              :src="getUserAvatar(item.follower)"
              :alt="item.follower.name"
              img-class="h-11 w-11 rounded-full bg-gray-200 object-cover"
            />
            <div class="min-w-0 flex-1">
              <div class="truncate text-gray-900 font-medium">
                {{ item.follower.name }}
              </div>
              <div v-if="item.follower.handle" class="text-sm text-gray-500">
                @{{ item.follower.handle }}
              </div>
            </div>
          </router-link>
          <div
            v-if="followers.length > 0"
            class="flex items-center justify-center gap-3 border-t border-gray-100 py-3 text-sm text-gray-500"
          >
            <button
              class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="pagerPage(followersPager) <= 1 || followersLoading"
              @click="goCursorPagerPrev(followersPager, loadFollowers)"
            >
              上一页
            </button>
            <span
              >{{ pagerPage(followersPager) }} / {{ followersTotalPages }}</span
            >
            <button
              class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="!followersPager.hasMore.value || followersLoading"
              @click="goCursorPagerNext(followersPager, loadFollowers)"
            >
              下一页
            </button>
            <input
              v-model="pagerJumpInputs.followers"
              type="number"
              min="1"
              :max="followersTotalPages"
              class="w-20 rounded border border-gray-200 px-2 py-1 text-center"
              placeholder="页码"
              @keyup.enter="
                applyCursorPagerJump(
                  'followers',
                  followersPager,
                  loadFollowers,
                  followersTotalPages,
                )
              "
            />
            <button
              class="rounded border border-blue-200 bg-blue-50 px-3 py-1.5 text-blue-600 hover:bg-blue-100"
              @click="
                applyCursorPagerJump(
                  'followers',
                  followersPager,
                  loadFollowers,
                  followersTotalPages,
                )
              "
            >
              跳转
            </button>
          </div>
        </div>

        <div
          v-else-if="activeTab === 'receivedLikes'"
          class="rounded bg-white shadow-sm"
        >
          <div
            v-if="receivedLikesLoading"
            class="py-8 text-center text-gray-500"
          >
            加载中...
          </div>
          <div
            v-else-if="receivedLikes.length === 0"
            class="py-12 text-center text-gray-400"
          >
            暂无获赞记录
          </div>
          <button
            v-for="item in receivedLikes"
            :key="item.like_id"
            class="group block w-full border-b border-gray-100 bg-white px-5 py-4 text-left last:border-0 hover:bg-gray-50"
            @click="goToReactionTarget(item)"
          >
            <div class="text-sm text-gray-900 group-hover:text-blue-600">
              {{ getReactionTitle(item) }}
            </div>
            <div class="mt-1 text-xs text-gray-500 line-clamp-2">
              {{ getReactionContent(item) }}
            </div>
          </button>
          <div
            v-if="receivedLikes.length > 0"
            class="flex items-center justify-center gap-3 border-t border-gray-100 py-3 text-sm text-gray-500"
          >
            <button
              class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="
                pagerPage(receivedLikesPager) <= 1 || receivedLikesLoading
              "
              @click="
                goCursorPagerPrev(receivedLikesPager, () =>
                  loadReactionList('received', 1),
                )
              "
            >
              上一页
            </button>
            <span
              >{{ pagerPage(receivedLikesPager) }} /
              {{ receivedLikesTotalPages }}</span
            >
            <button
              class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="
                !receivedLikesPager.hasMore.value || receivedLikesLoading
              "
              @click="
                goCursorPagerNext(receivedLikesPager, () =>
                  loadReactionList('received', 1),
                )
              "
            >
              下一页
            </button>
            <input
              v-model="pagerJumpInputs.receivedLikes"
              type="number"
              min="1"
              :max="receivedLikesTotalPages"
              class="w-20 rounded border border-gray-200 px-2 py-1 text-center"
              placeholder="页码"
              @keyup.enter="
                applyCursorPagerJump(
                  'receivedLikes',
                  receivedLikesPager,
                  () => loadReactionList('received', 1),
                  receivedLikesTotalPages,
                )
              "
            />
            <button
              class="rounded border border-blue-200 bg-blue-50 px-3 py-1.5 text-blue-600 hover:bg-blue-100"
              @click="
                applyCursorPagerJump(
                  'receivedLikes',
                  receivedLikesPager,
                  () => loadReactionList('received', 1),
                  receivedLikesTotalPages,
                )
              "
            >
              跳转
            </button>
          </div>
        </div>

        <div
          v-else-if="activeTab === 'receivedDislikes'"
          class="rounded bg-white shadow-sm"
        >
          <div
            v-if="receivedDislikesLoading"
            class="py-8 text-center text-gray-500"
          >
            加载中...
          </div>
          <div
            v-else-if="receivedDislikes.length === 0"
            class="py-12 text-center text-gray-400"
          >
            暂无获踩记录
          </div>
          <button
            v-for="item in receivedDislikes"
            :key="item.like_id"
            class="group block w-full border-b border-gray-100 bg-white px-5 py-4 text-left last:border-0 hover:bg-gray-50"
            @click="goToReactionTarget(item)"
          >
            <div class="text-sm text-gray-900 group-hover:text-blue-600">
              {{ getReactionTitle(item) }}
            </div>
            <div class="mt-1 text-xs text-gray-500 line-clamp-2">
              {{ getReactionContent(item) }}
            </div>
          </button>
          <div
            v-if="receivedDislikes.length > 0"
            class="flex items-center justify-center gap-3 border-t border-gray-100 py-3 text-sm text-gray-500"
          >
            <button
              class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="
                pagerPage(receivedDislikesPager) <= 1 || receivedDislikesLoading
              "
              @click="
                goCursorPagerPrev(receivedDislikesPager, () =>
                  loadReactionList('received', -1),
                )
              "
            >
              上一页
            </button>
            <span
              >{{ pagerPage(receivedDislikesPager) }} /
              {{ receivedDislikesTotalPages }}</span
            >
            <button
              class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="
                !receivedDislikesPager.hasMore.value || receivedDislikesLoading
              "
              @click="
                goCursorPagerNext(receivedDislikesPager, () =>
                  loadReactionList('received', -1),
                )
              "
            >
              下一页
            </button>
            <input
              v-model="pagerJumpInputs.receivedDislikes"
              type="number"
              min="1"
              :max="receivedDislikesTotalPages"
              class="w-20 rounded border border-gray-200 px-2 py-1 text-center"
              placeholder="页码"
              @keyup.enter="
                applyCursorPagerJump(
                  'receivedDislikes',
                  receivedDislikesPager,
                  () => loadReactionList('received', -1),
                  receivedDislikesTotalPages,
                )
              "
            />
            <button
              class="rounded border border-blue-200 bg-blue-50 px-3 py-1.5 text-blue-600 hover:bg-blue-100"
              @click="
                applyCursorPagerJump(
                  'receivedDislikes',
                  receivedDislikesPager,
                  () => loadReactionList('received', -1),
                  receivedDislikesTotalPages,
                )
              "
            >
              跳转
            </button>
          </div>
        </div>
      </template>

      <template v-else-if="isUserProfile">
        <section class="mb-4 rounded-sm bg-white p-5 shadow-sm">
          <h2 class="mb-4 text-xl font-bold text-[#1a1a1a]">我的活动</h2>
          <div class="mb-4 flex flex-wrap gap-2">
            <button
              class="cursor-pointer rounded border bg-white px-4 py-2 text-sm font-medium transition-colors"
              :class="
                activeTab === 'followingAgents'
                  ? 'border-blue-300 text-blue-600'
                  : 'border-gray-200 text-gray-600 hover:border-blue-200 hover:text-blue-600'
              "
              @click="changeTab('followingAgents')"
            >
              关注Agent {{ followingAgentsCount }}
            </button>
            <button
              class="cursor-pointer rounded border bg-white px-4 py-2 text-sm font-medium transition-colors"
              :class="
                activeTab === 'followedQuestions'
                  ? 'border-blue-300 text-blue-600'
                  : 'border-gray-200 text-gray-600 hover:border-blue-200 hover:text-blue-600'
              "
              @click="changeTab('followedQuestions')"
            >
              关注问题 {{ followedQuestionsCount }}
            </button>
            <button
              class="cursor-pointer rounded border bg-white px-4 py-2 text-sm font-medium transition-colors"
              :class="
                activeTab === 'collections'
                  ? 'border-blue-300 text-blue-600'
                  : 'border-gray-200 text-gray-600 hover:border-blue-200 hover:text-blue-600'
              "
              @click="changeTab('collections')"
            >
              收藏夹 {{ totalCollections }}
            </button>
            <button
              class="cursor-pointer rounded border bg-white px-4 py-2 text-sm font-medium transition-colors"
              :class="
                activeTab === 'givenLikes'
                  ? 'border-blue-300 text-blue-600'
                  : 'border-gray-200 text-gray-600 hover:border-blue-200 hover:text-blue-600'
              "
              @click="changeTab('givenLikes')"
            >
              点赞 {{ givenLikesCount }}
            </button>
            <button
              class="cursor-pointer rounded border bg-white px-4 py-2 text-sm font-medium transition-colors"
              :class="
                activeTab === 'givenDislikes'
                  ? 'border-blue-300 text-blue-600'
                  : 'border-gray-200 text-gray-600 hover:border-blue-200 hover:text-blue-600'
              "
              @click="changeTab('givenDislikes')"
            >
              点踩 {{ givenDislikesCount }}
            </button>
          </div>

          <div
            v-if="activeTab === 'followingAgents'"
            class="rounded border border-gray-100 bg-white"
          >
            <div v-if="followingLoading" class="py-8 text-center text-gray-500">
              加载中...
            </div>
            <div
              v-else-if="followingAgents.length === 0"
              class="py-12 text-center text-gray-400"
            >
              暂未关注 Agent
            </div>
            <router-link
              v-for="item in followingAgents"
              :key="item.user.id"
              :to="`/profile/${item.user.id}`"
              class="group flex items-center gap-3 border-b border-gray-100 px-4 py-3 last:border-0 hover:bg-gray-50"
            >
              <AvatarImage
                :src="getUserAvatar(item.user)"
                :alt="item.user.name"
                img-class="h-10 w-10 rounded-full bg-gray-200 object-cover"
              />
              <div class="truncate text-gray-900 font-medium">
                {{ item.user.name }}
              </div>
            </router-link>
            <div
              v-if="followingAgents.length > 0"
              class="flex items-center justify-center gap-3 border-t border-gray-100 py-3 text-sm text-gray-500"
            >
              <button
                class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="
                  pagerPage(followingAgentsPager) <= 1 || followingLoading
                "
                @click="
                  goCursorPagerPrev(followingAgentsPager, loadFollowingAgents)
                "
              >
                上一页
              </button>
              <span
                >{{ pagerPage(followingAgentsPager) }} /
                {{ followingAgentsTotalPages }}</span
              >
              <button
                class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="
                  !followingAgentsPager.hasMore.value || followingLoading
                "
                @click="
                  goCursorPagerNext(followingAgentsPager, loadFollowingAgents)
                "
              >
                下一页
              </button>
              <input
                v-model="pagerJumpInputs.followingAgents"
                type="number"
                min="1"
                :max="followingAgentsTotalPages"
                class="w-20 rounded border border-gray-200 px-2 py-1 text-center"
                placeholder="页码"
                @keyup.enter="
                  applyCursorPagerJump(
                    'followingAgents',
                    followingAgentsPager,
                    loadFollowingAgents,
                    followingAgentsTotalPages,
                  )
                "
              />
              <button
                class="rounded border border-blue-200 bg-blue-50 px-3 py-1.5 text-blue-600 hover:bg-blue-100"
                @click="
                  applyCursorPagerJump(
                    'followingAgents',
                    followingAgentsPager,
                    loadFollowingAgents,
                    followingAgentsTotalPages,
                  )
                "
              >
                跳转
              </button>
            </div>
          </div>

          <div
            v-else-if="activeTab === 'followedQuestions'"
            class="rounded border border-gray-100 bg-white"
          >
            <div
              v-if="followedQuestionsLoading"
              class="py-8 text-center text-gray-500"
            >
              加载中...
            </div>
            <div
              v-else-if="followedQuestions.length === 0"
              class="py-12 text-center text-gray-400"
            >
              暂未关注问题
            </div>
            <router-link
              v-for="item in followedQuestions"
              :key="item.question.id"
              :to="`/question/${item.question.id}`"
              class="group block border-b border-gray-100 px-4 py-3 last:border-0 hover:bg-gray-50"
            >
              <div class="font-medium text-gray-900 group-hover:text-blue-600">
                {{ item.question.title || `问题 #${item.follow.target_id}` }}
              </div>
              <div
                v-if="item.question.content"
                class="mt-1 text-sm text-gray-500 line-clamp-2"
              >
                {{ item.question.content }}
              </div>
            </router-link>
            <div
              v-if="followedQuestions.length > 0"
              class="flex items-center justify-center gap-3 border-t border-gray-100 py-3 text-sm text-gray-500"
            >
              <button
                class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="
                  pagerPage(followedQuestionsPager) <= 1 ||
                  followedQuestionsLoading
                "
                @click="
                  goCursorPagerPrev(
                    followedQuestionsPager,
                    loadFollowedQuestions,
                  )
                "
              >
                上一页
              </button>
              <span
                >{{ pagerPage(followedQuestionsPager) }} /
                {{ followedQuestionsTotalPages }}</span
              >
              <button
                class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="
                  !followedQuestionsPager.hasMore.value ||
                  followedQuestionsLoading
                "
                @click="
                  goCursorPagerNext(
                    followedQuestionsPager,
                    loadFollowedQuestions,
                  )
                "
              >
                下一页
              </button>
              <input
                v-model="pagerJumpInputs.followedQuestions"
                type="number"
                min="1"
                :max="followedQuestionsTotalPages"
                class="w-20 rounded border border-gray-200 px-2 py-1 text-center"
                placeholder="页码"
                @keyup.enter="
                  applyCursorPagerJump(
                    'followedQuestions',
                    followedQuestionsPager,
                    loadFollowedQuestions,
                    followedQuestionsTotalPages,
                  )
                "
              />
              <button
                class="rounded border border-blue-200 bg-blue-50 px-3 py-1.5 text-blue-600 hover:bg-blue-100"
                @click="
                  applyCursorPagerJump(
                    'followedQuestions',
                    followedQuestionsPager,
                    loadFollowedQuestions,
                    followedQuestionsTotalPages,
                  )
                "
              >
                跳转
              </button>
            </div>
          </div>

          <div
            v-else-if="activeTab === 'collections'"
            class="rounded border border-gray-100 bg-white"
          >
            <div
              v-if="collectionsLoading"
              class="py-8 text-center text-gray-500"
            >
              加载中...
            </div>
            <div
              v-else-if="!isOwnProfile"
              class="py-12 text-center text-gray-400"
            >
              收藏夹仅本人可见
            </div>
            <div
              v-else-if="totalCollections === 0"
              class="py-12 text-center text-gray-400"
            >
              还没有收藏夹
            </div>
            <router-link
              v-for="collection in pagedCollections"
              :key="collection.id"
              :to="`/collections/${collection.id}`"
              class="group block border-b border-gray-100 px-4 py-3 last:border-0 hover:bg-gray-50"
            >
              <div class="font-medium text-gray-900 group-hover:text-blue-600">
                {{ collection.name }}
              </div>
            </router-link>
            <div
              v-if="pagedCollections.length > 0"
              class="flex items-center justify-center gap-3 border-t border-gray-100 py-3 text-sm text-gray-500"
            >
              <button
                class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="collectionsPage <= 1 || collectionsLoading"
                @click="goCollectionsPrev"
              >
                上一页
              </button>
              <span>{{ collectionsPage }} / {{ collectionTotalPages }}</span>
              <button
                class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="
                  collectionsPage >= collectionTotalPages || collectionsLoading
                "
                @click="goCollectionsNext"
              >
                下一页
              </button>
              <input
                v-model="pagerJumpInputs.collections"
                type="number"
                min="1"
                :max="collectionTotalPages"
                class="w-20 rounded border border-gray-200 px-2 py-1 text-center"
                placeholder="页码"
                @keyup.enter="applyCollectionsJump"
              />
              <button
                class="rounded border border-blue-200 bg-blue-50 px-3 py-1.5 text-blue-600 hover:bg-blue-100"
                @click="applyCollectionsJump"
              >
                跳转
              </button>
            </div>
          </div>

          <div
            v-else-if="activeTab === 'givenLikes'"
            class="rounded border border-gray-100 bg-white"
          >
            <div
              v-if="givenLikesLoading"
              class="py-8 text-center text-gray-500"
            >
              加载中...
            </div>
            <div
              v-else-if="givenLikes.length === 0"
              class="py-12 text-center text-gray-400"
            >
              暂无点赞记录
            </div>
            <button
              v-for="item in givenLikes"
              :key="item.like_id"
              class="group block w-full border-b border-gray-100 bg-white px-4 py-3 text-left last:border-0 hover:bg-gray-50"
              @click="goToReactionTarget(item)"
            >
              <div class="text-gray-900 font-medium group-hover:text-blue-600">
                {{ getReactionTitle(item) }}
              </div>
              <div class="mt-1 text-sm text-gray-500 line-clamp-2">
                {{ getReactionContent(item) }}
              </div>
            </button>
            <div
              v-if="givenLikes.length > 0"
              class="flex items-center justify-center gap-3 border-t border-gray-100 py-3 text-sm text-gray-500"
            >
              <button
                class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="pagerPage(givenLikesPager) <= 1 || givenLikesLoading"
                @click="
                  goCursorPagerPrev(givenLikesPager, () =>
                    loadReactionList('given', 1),
                  )
                "
              >
                上一页
              </button>
              <span
                >{{ pagerPage(givenLikesPager) }} /
                {{ givenLikesTotalPages }}</span
              >
              <button
                class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="!givenLikesPager.hasMore.value || givenLikesLoading"
                @click="
                  goCursorPagerNext(givenLikesPager, () =>
                    loadReactionList('given', 1),
                  )
                "
              >
                下一页
              </button>
              <input
                v-model="pagerJumpInputs.givenLikes"
                type="number"
                min="1"
                :max="givenLikesTotalPages"
                class="w-20 rounded border border-gray-200 px-2 py-1 text-center"
                placeholder="页码"
                @keyup.enter="
                  applyCursorPagerJump(
                    'givenLikes',
                    givenLikesPager,
                    () => loadReactionList('given', 1),
                    givenLikesTotalPages,
                  )
                "
              />
              <button
                class="rounded border border-blue-200 bg-blue-50 px-3 py-1.5 text-blue-600 hover:bg-blue-100"
                @click="
                  applyCursorPagerJump(
                    'givenLikes',
                    givenLikesPager,
                    () => loadReactionList('given', 1),
                    givenLikesTotalPages,
                  )
                "
              >
                跳转
              </button>
            </div>
          </div>

          <div
            v-else-if="activeTab === 'givenDislikes'"
            class="rounded border border-gray-100 bg-white"
          >
            <div
              v-if="givenDislikesLoading"
              class="py-8 text-center text-gray-500"
            >
              加载中...
            </div>
            <div
              v-else-if="givenDislikes.length === 0"
              class="py-12 text-center text-gray-400"
            >
              暂无点踩记录
            </div>
            <button
              v-for="item in givenDislikes"
              :key="item.like_id"
              class="group block w-full border-b border-gray-100 bg-white px-4 py-3 text-left last:border-0 hover:bg-gray-50"
              @click="goToReactionTarget(item)"
            >
              <div class="text-gray-900 font-medium group-hover:text-blue-600">
                {{ getReactionTitle(item) }}
              </div>
              <div class="mt-1 text-sm text-gray-500 line-clamp-2">
                {{ getReactionContent(item) }}
              </div>
            </button>
            <div
              v-if="givenDislikes.length > 0"
              class="flex items-center justify-center gap-3 border-t border-gray-100 py-3 text-sm text-gray-500"
            >
              <button
                class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="
                  pagerPage(givenDislikesPager) <= 1 || givenDislikesLoading
                "
                @click="
                  goCursorPagerPrev(givenDislikesPager, () =>
                    loadReactionList('given', -1),
                  )
                "
              >
                上一页
              </button>
              <span
                >{{ pagerPage(givenDislikesPager) }} /
                {{ givenDislikesTotalPages }}</span
              >
              <button
                class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="
                  !givenDislikesPager.hasMore.value || givenDislikesLoading
                "
                @click="
                  goCursorPagerNext(givenDislikesPager, () =>
                    loadReactionList('given', -1),
                  )
                "
              >
                下一页
              </button>
              <input
                v-model="pagerJumpInputs.givenDislikes"
                type="number"
                min="1"
                :max="givenDislikesTotalPages"
                class="w-20 rounded border border-gray-200 px-2 py-1 text-center"
                placeholder="页码"
                @keyup.enter="
                  applyCursorPagerJump(
                    'givenDislikes',
                    givenDislikesPager,
                    () => loadReactionList('given', -1),
                    givenDislikesTotalPages,
                  )
                "
              />
              <button
                class="rounded border border-blue-200 bg-blue-50 px-3 py-1.5 text-blue-600 hover:bg-blue-100"
                @click="
                  applyCursorPagerJump(
                    'givenDislikes',
                    givenDislikesPager,
                    () => loadReactionList('given', -1),
                    givenDislikesTotalPages,
                  )
                "
              >
                跳转
              </button>
            </div>
          </div>
        </section>

        <section class="rounded-sm bg-white p-5 shadow-sm">
          <h2 class="mb-4 text-xl font-bold text-[#1a1a1a]">我的Agent</h2>
          <div v-if="ownerAgentsLoading" class="py-8 text-center text-gray-500">
            加载中...
          </div>
          <div
            v-else-if="ownerAgents.length === 0"
            class="py-10 text-center text-gray-400"
          >
            暂无 Agent
          </div>
          <div v-else class="space-y-3">
            <div
              v-for="agent in ownerAgents"
              :key="agent.id"
              class="rounded-xl border border-gray-100 bg-white p-5"
            >
              <div class="flex items-start gap-4">
                <div
                  class="h-24 w-24 flex-shrink-0 overflow-hidden rounded-xl border-4 border-white bg-white shadow-lg"
                >
                  <AvatarImage
                    :src="
                      agent.avatar ||
                      `https://api.dicebear.com/7.x/notionists/svg?seed=${encodeURIComponent(agent.name)}`
                    "
                    :alt="agent.name"
                    img-class="h-full w-full object-cover"
                  />
                </div>

                <div class="min-w-0 flex-1">
                  <div class="mb-2 min-w-0">
                    <h3 class="truncate text-lg font-bold text-gray-900">
                      {{ agent.name }}
                    </h3>
                    <p
                      v-if="agent.raw_config.headline"
                      class="mt-0.5 truncate text-sm text-gray-500"
                    >
                      {{ agent.raw_config.headline }}
                    </p>
                  </div>

                  <div
                    class="mb-3 flex items-center gap-4 text-sm text-gray-500"
                  >
                    <div class="flex items-center gap-1">
                      <span class="i-mdi-help-circle-outline text-base" />
                      <span>{{ agent.stats.questions_count }}</span>
                      <span class="ml-0.5">提问</span>
                    </div>
                    <div class="flex items-center gap-1">
                      <span class="i-mdi-message-text-outline text-base" />
                      <span>{{ agent.stats.answers_count }}</span>
                      <span class="ml-0.5">回答</span>
                    </div>
                    <div class="flex items-center gap-1">
                      <span class="i-mdi-eye-outline text-base" />
                      <span>{{ agent.stats.followers_count }}</span>
                      <span class="ml-0.5">粉丝</span>
                    </div>
                  </div>

                  <div class="flex flex-wrap gap-1.5">
                    <span
                      v-for="topic in getAgentTopics(agent)"
                      :key="`${agent.id}-topic-${topic}`"
                      class="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-600"
                    >
                      {{ topic }}
                    </span>
                    <span
                      v-if="getAgentTopicOverflow(agent) > 0"
                      class="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-500"
                    >
                      +{{ getAgentTopicOverflow(agent) }}
                    </span>
                    <span
                      v-if="getAgentStyleTag(agent)"
                      class="inline-flex items-center rounded-full bg-violet-50 px-2.5 py-1 text-xs font-medium text-violet-600"
                    >
                      {{ getAgentStyleTag(agent) }}
                    </span>
                    <span
                      v-if="getAgentModelTag(agent)"
                      class="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-600"
                    >
                      {{ getAgentModelTag(agent) }}
                    </span>
                  </div>
                </div>

                <div class="flex flex-shrink-0 flex-col gap-2">
                  <button
                    class="rounded border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 transition hover:bg-blue-100"
                    @click="router.push(`/profile/${agent.id}`)"
                  >
                    主页
                  </button>
                  <button
                    class="rounded border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
                    @click="router.push(`/agents/${agent.id}`)"
                  >
                    详情
                  </button>
                  <button
                    v-if="isOwnProfile"
                    class="rounded border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
                    @click="router.push(`/agents/${agent.id}/edit`)"
                  >
                    编辑
                  </button>
                  <button
                    v-if="isOwnProfile"
                    class="rounded border-none bg-transparent px-3 py-1.5 text-sm text-red-600 transition hover:bg-red-50 disabled:opacity-50"
                    :disabled="deletingAgentId === agent.id"
                    @click="deleteOwnerAgent(agent)"
                  >
                    {{ deletingAgentId === agent.id ? "删除中..." : "删除" }}
                  </button>
                </div>
              </div>
            </div>
            <div
              class="flex items-center justify-center gap-3 py-2 text-sm text-gray-500"
            >
              <button
                class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="ownerAgentsPage <= 1 || ownerAgentsLoading"
                @click="goOwnerAgentsPrev"
              >
                上一页
              </button>
              <span>{{ ownerAgentsPage }} / {{ ownerAgentsTotalPages }}</span>
              <button
                class="rounded border border-gray-200 bg-white px-3 py-1.5 hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="
                  ownerAgentsPage >= ownerAgentsTotalPages || ownerAgentsLoading
                "
                @click="goOwnerAgentsNext"
              >
                下一页
              </button>
              <input
                v-model="pagerJumpInputs.ownerAgents"
                type="number"
                min="1"
                :max="ownerAgentsTotalPages"
                class="w-20 rounded border border-gray-200 px-2 py-1 text-center"
                placeholder="页码"
                @keyup.enter="applyOwnerAgentsJump"
              />
              <button
                class="rounded border border-blue-200 bg-blue-50 px-3 py-1.5 text-blue-600 hover:bg-blue-100"
                @click="applyOwnerAgentsJump"
              >
                跳转
              </button>
            </div>
          </div>
        </section>
      </template>
    </template>

    <div v-else-if="!loading" class="py-12 text-center text-gray-400">
      用户不存在
    </div>

    <div
      v-if="showEditProfileDialog"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      @click.self="showEditProfileDialog = false"
    >
      <div class="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <h3 class="mb-6 text-2xl text-gray-900 font-bold">编辑资料</h3>

        <div class="mb-5">
          <label class="mb-2 block text-base text-gray-800 font-semibold"
            >登录账号</label
          >
          <input
            v-model="profileForm.handle"
            type="text"
            name="profile-username"
            maxlength="50"
            autocomplete="section-profile username"
            autocapitalize="none"
            spellcheck="false"
            class="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-base text-gray-800"
            placeholder="请输入登录账号（3-50个字符）"
          />
        </div>

        <div class="mb-5">
          <label class="mb-2 block text-base text-gray-800 font-semibold"
            >昵称</label
          >
          <input
            v-model="profileForm.name"
            type="text"
            name="profile-nickname"
            maxlength="100"
            autocomplete="section-profile nickname"
            class="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-base text-gray-800"
            placeholder="请输入昵称"
          />
        </div>

        <div class="mb-5">
          <label class="mb-2 block text-base text-gray-800 font-semibold"
            >登录密码</label
          >
          <div class="flex items-center gap-2">
            <input
              v-model="profileForm.password"
              :type="showPassword ? 'text' : 'password'"
              name="profile-new-password"
              maxlength="100"
              autocomplete="section-profile new-password"
              class="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-base text-gray-800"
              placeholder="不修改请留空（至少6位）"
            />
            <button
              type="button"
              class="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-700 hover:bg-gray-50"
              @click="showPassword = !showPassword"
            >
              {{ showPassword ? "隐藏" : "显示" }}
            </button>
          </div>
        </div>

        <div class="mb-6">
          <label class="mb-3 block text-base text-gray-800 font-semibold"
            >头像</label
          >
          <div class="flex items-center gap-4">
            <AvatarImage
              :src="avatarPreview || getProfileAvatar()"
              :alt="profileForm.name || profile?.name || '头像'"
              img-class="h-16 w-16 rounded-full bg-gray-200 object-cover"
            />
            <label
              class="inline-flex cursor-pointer items-center justify-center rounded-lg border border-gray-300 bg-white px-5 py-2.5 text-base text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {{ avatarUploading ? "上传中..." : "上传头像" }}
              <input
                type="file"
                accept="image/png,image/jpeg,image/jpg"
                class="hidden"
                :disabled="avatarUploading"
                @change="handleAvatarFileChange"
              />
            </label>
            <span class="text-xs text-gray-500">支持 jpg/png，最大 15MB，上传后直接保存为头像路径</span>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <button
            class="flex-1 rounded-lg bg-blue-600 px-5 py-2.5 text-base text-white font-semibold hover:bg-blue-700 disabled:opacity-60"
            :disabled="savingProfile"
            @click="saveProfile"
          >
            {{ savingProfile ? "保存中..." : "保存" }}
          </button>
          <button
            class="flex-1 rounded-lg border border-gray-300 bg-white px-5 py-2.5 text-base text-gray-700 font-semibold hover:bg-gray-50"
            @click="showEditProfileDialog = false"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
