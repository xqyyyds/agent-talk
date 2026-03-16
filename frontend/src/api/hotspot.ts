import type { ApiResponse, Hotspot, HotspotListResponse } from "./types";
import request from "./request";

/**
 * 获取热点列表（前端展示，走 JWT 认证）
 */
export function getHotspotList(params: {
  page?: number;
  page_size?: number;
  source?: string;
  status?: string;
  date?: string;
}) {
  return request.get<ApiResponse<HotspotListResponse>>("/hotspots", { params });
}

/**
 * 获取热点详情（含知乎原始回答）
 */
export function getHotspotDetail(hotspotId: number) {
  return request.get<ApiResponse<Hotspot>>(`/hotspots/${hotspotId}`);
}

/**
 * 获取有数据的日期列表（期次导航用）
 */
export function getHotspotDates(source?: string) {
  return request.get<ApiResponse<string[]>>("/hotspots/dates", {
    params: source ? { source } : {},
  });
}
