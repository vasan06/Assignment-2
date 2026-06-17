export interface User {
  id: number;
  email: string;
  name?: string | null;
  role: "admin" | "user";
  created_at: string;
}

export interface Video {
  id: number;
  title: string;
  description?: string | null;
  status: "pending" | "processing" | "ready" | "failed";
  thumbnail_url?: string | null;
  master_playlist_url?: string | null;
  duration_seconds?: number | null;
  available_resolutions?: string | null;
  video_uuid?: string | null;
  processing_started_at?: string | null;
  processing_completed_at?: string | null;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ProcessingStatus {
  video_id: number;
  status: string;
  processing_started_at?: string | null;
  processing_completed_at?: string | null;
  available_resolutions?: string | null;
  estimated_remaining_seconds?: number | null;
  message: string;
}

export interface VideoPlayStats {
  video_id: number;
  title: string;
  total_plays: number;
  unique_viewers: number;
  avg_watch_duration: number;
}

export interface UserActivity {
  user_id: number;
  email: string;
  name?: string | null;
  total_watch_time: number;
  videos_watched: number;
  last_active?: string | null;
}

export interface UserVideoLog {
  video_id: number;
  video_title: string;
  play_count: number;
  total_watch_duration: number;
  last_watched: string;
}

export interface RepeatedVideo {
  video_id: number;
  title: string;
  user_id: number;
  user_email: string;
  play_count: number;
}
