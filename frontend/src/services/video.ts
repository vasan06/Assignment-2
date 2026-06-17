import { apiFetch } from "./api";
import {
  Video,
  ProcessingStatus,
  VideoPlayStats,
  UserActivity,
  UserVideoLog,
  RepeatedVideo,
} from "@/types";

export async function listVideos(search?: string): Promise<Video[]> {
  const qs = search ? `?search=${encodeURIComponent(search)}` : "";
  return apiFetch<Video[]>(`/videos${qs}`);
}

export async function getVideo(id: number): Promise<Video> {
  return apiFetch<Video>(`/videos/${id}`);
}

export async function getUploadStatus(id: number): Promise<ProcessingStatus> {
  return apiFetch<ProcessingStatus>(`/uploads/status/${id}`);
}

export async function logWatch(videoId: number, watchDuration: number) {
  return apiFetch(`/videos/watch-log`, {
    method: "POST",
    body: JSON.stringify({ video_id: videoId, watch_duration: watchDuration }),
  });
}

export async function addFavorite(videoId: number) {
  return apiFetch(`/videos/${videoId}/favorite`, { method: "POST" });
}

export async function removeFavorite(videoId: number) {
  return apiFetch(`/videos/${videoId}/favorite`, { method: "DELETE" });
}

export async function getMyFavorites(): Promise<Video[]> {
  return apiFetch<Video[]>(`/videos/favorites/me`);
}

export async function getMyHistory(): Promise<Video[]> {
  return apiFetch<Video[]>(`/videos/history/me`);
}

export async function uploadVideo(
  title: string,
  description: string,
  file: File
): Promise<{ video: Video; message: string }> {
  const form = new FormData();
  form.append("title", title);
  form.append("description", description);
  form.append("file", file);
  return apiFetch(`/uploads`, { method: "POST", body: form });
}

export async function deleteVideo(id: number) {
  return apiFetch(`/uploads/${id}`, { method: "DELETE" });
}

// Analytics (admin)
export async function getVideoStats(): Promise<VideoPlayStats[]> {
  return apiFetch<VideoPlayStats[]>(`/analytics/video-stats`);
}

export async function getUserActivity(): Promise<UserActivity[]> {
  return apiFetch<UserActivity[]>(`/analytics/user-activity`);
}

export async function getUserVideoLogs(userId: number): Promise<UserVideoLog[]> {
  return apiFetch<UserVideoLog[]>(`/analytics/user/${userId}/logs`);
}

export async function getRepeatedVideos(): Promise<RepeatedVideo[]> {
  return apiFetch<RepeatedVideo[]>(`/analytics/repeated-videos`);
}
