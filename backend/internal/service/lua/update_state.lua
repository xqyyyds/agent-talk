-- KEYS[1]: user_like_bitmap    (ulike:q:uid)
-- KEYS[2]: obj_like_bitmap     (plike:q:oid)
-- KEYS[3]: user_dislike_bitmap (udislike:q:uid)
-- KEYS[4]: obj_dislike_bitmap  (pdislike:q:oid)
-- KEYS[5]: stats_hash_key      (stats:q:oid)

-- ARGV[1]: obj_id
-- ARGV[2]: user_id
-- ARGV[3]: action_type (1=Like, 2=Dislike, 0=Cancel)

local action = tonumber(ARGV[3])
local obj_id = ARGV[1]
local user_id = ARGV[2]

-- 定义 target_like (目标赞状态) 和 target_dislike (目标踩状态)
local target_like = 0
local target_dislike = 0

if action == 1 then
    target_like = 1
elseif action == 2 then
    target_dislike = 1
end

-- ========================================================
-- 1. 处理 [点赞] 逻辑
-- ========================================================
-- R.SETBIT 返回修改前的值 (0 或 1)
local old_like_val = redis.call('R.SETBIT', KEYS[1], obj_id, target_like)

-- 计算赞的增量
local like_delta = 0
if old_like_val == 0 and target_like == 1 then
    like_delta = 1 -- 从没赞变赞 -> +1
elseif old_like_val == 1 and target_like == 0 then
    like_delta = -1 -- 从赞变没赞 -> -1
end

-- 同步 obj_like_bitmap
if like_delta ~= 0 then
    redis.call('R.SETBIT', KEYS[2], user_id, target_like)
end

-- ========================================================
-- 2. 处理 [点踩] 逻辑 (互斥)
-- ========================================================
-- R.SETBIT 返回修改前的值 (0 或 1)
local old_dislike_val = redis.call('R.SETBIT', KEYS[3], obj_id, target_dislike)

-- 计算踩的增量
local dislike_delta = 0
if old_dislike_val == 0 and target_dislike == 1 then
    dislike_delta = 1
elseif old_dislike_val == 1 and target_dislike == 0 then
    dislike_delta = -1
end

-- 同步 obj_dislike_bitmap
if dislike_delta ~= 0 then
    redis.call('R.SETBIT', KEYS[4], user_id, target_dislike)
end

-- ========================================================
-- 3. 原子更新 Hash 计数器
-- ========================================================
-- 先更新点赞计数
if like_delta ~= 0 then
    redis.call('HINCRBY', KEYS[5], 'l', like_delta)
end

-- 再更新点踩计数
if dislike_delta ~= 0 then
    redis.call('HINCRBY', KEYS[5], 'd', dislike_delta)
end

-- ========================================================
-- 4. 修复负数计数的问题
-- ========================================================
-- 如果点赞变成点踩，需要减少点赞计数，增加点踩计数
-- 如果点踩变成点赞，需要减少点踩计数，增加点赞计数
-- 这里我们确保计数器不会为负数
local current_stats = redis.call('HGETALL', KEYS[5])
local current_like = tonumber(current_stats['l']) or 0
local current_dislike = tonumber(current_stats['d']) or 0

-- 确保计数器非负（容错机制）
if current_like < 0 then
    redis.call('HSET', KEYS[5], 'l', 0)
end
if current_dislike < 0 then
    redis.call('HSET', KEYS[5], 'd', 0)
end

return {like_delta, dislike_delta}