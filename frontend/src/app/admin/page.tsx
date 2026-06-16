"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  Loader2,
  UploadCloud,
  Play,
  Users,
  Repeat,
  Trash2,
} from "lucide-react";
import {
  VideoPlayStats,
  UserActivity,
  RepeatedVideo,
  Video,
} from "@/types";
import {
  getVideoStats,
  getUserActivity,
  getRepeatedVideos,
  listVideos,
  deleteVideo,
} from "@/services/video";
import { useAuth } from "@/context/AuthContext";

function formatDuration(seconds: number): string {
  if (!seconds) return "0s";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  if (m === 0) return `${s}s`;
  return `${m}m ${s}s`;
}

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "Never";
  return new Date(dateStr).toLocaleString();
}

export default function AdminDashboard() {
  const { user, loading: authLoading } = useAuth();
  const [videoStats, setVideoStats] = useState<VideoPlayStats[]>([]);
  const [userActivity, setUserActivity] = useState<UserActivity[]>([]);
  const [repeated, setRepeated] = useState<RepeatedVideo[]>([]);
  const [allVideos, setAllVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (authLoading) return;
    if (!user || user.role !== "admin") {
      setLoading(false);
      return;
    }

    Promise.all([
      getVideoStats(),
      getUserActivity(),
      getRepeatedVideos(),
      listVideos(),
    ])
      .then(([vs, ua, rv, videos]) => {
        setVideoStats(vs);
        setUserActivity(ua);
        setRepeated(rv);
        setAllVideos(videos);
      })
      .catch(() => setError("Failed to load analytics data."))
      .finally(() => setLoading(false));
  }, [user, authLoading]);

  async function handleDelete(id: number) {
    if (!confirm("Delete this video? This cannot be undone.")) return;
    try {
      await deleteVideo(id);
      setAllVideos((prev) => prev.filter((v) => v.id !== id));
      setVideoStats((prev) => prev.filter((v) => v.video_id !== id));
    } catch {
      alert("Failed to delete video.");
    }
  }

  if (authLoading || loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="animate-spin text-text-muted" size={32} />
      </div>
    );
  }

  if (!user || user.role !== "admin") {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-3 text-center px-4">
        <ShieldCheck size={32} className="text-text-muted" />
        <p className="text-text-muted">You need admin access to view this page.</p>
      </div>
    );
  }

  const totalPlays = videoStats.reduce((sum, v) => sum + v.total_plays, 0);
  const totalWatchTime = userActivity.reduce((sum, u) => sum + u.total_watch_time, 0);

  return (
    <div className="px-6 py-6 md:px-10 md:py-8 space-y-10">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl font-bold flex items-center gap-2">
          <ShieldCheck className="text-accent" size={24} />
          Admin dashboard
        </h1>
        <Link
          href="/admin/upload"
          className="flex items-center gap-2 bg-accent text-black text-sm font-medium px-4 py-2 rounded-lg"
        >
          <UploadCloud size={16} />
          Upload video
        </Link>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {/* Summary stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-surface border border-border rounded-xl p-4">
          <p className="text-xs text-text-muted mb-1">Total videos</p>
          <p className="text-2xl font-display font-bold">{allVideos.length}</p>
        </div>
        <div className="bg-surface border border-border rounded-xl p-4">
          <p className="text-xs text-text-muted mb-1">Total plays</p>
          <p className="text-2xl font-display font-bold">{totalPlays}</p>
        </div>
        <div className="bg-surface border border-border rounded-xl p-4">
          <p className="text-xs text-text-muted mb-1">Total watch time</p>
          <p className="text-2xl font-display font-bold">{formatDuration(totalWatchTime)}</p>
        </div>
      </div>

      {/* Video stats table */}
      <section>
        <h2 className="font-display text-lg font-bold mb-3 flex items-center gap-2">
          <Play size={18} className="text-accent" />
          Video performance
        </h2>
        <div className="overflow-x-auto border border-border rounded-xl">
          <table className="w-full text-sm">
            <thead className="bg-surface text-text-muted">
              <tr>
                <th className="text-left px-4 py-2">Title</th>
                <th className="text-left px-4 py-2">Status</th>
                <th className="text-right px-4 py-2">Total plays</th>
                <th className="text-right px-4 py-2">Unique viewers</th>
                <th className="text-right px-4 py-2">Avg watch time</th>
                <th className="text-right px-4 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {allVideos.map((v) => {
                const stats = videoStats.find((s) => s.video_id === v.id);
                return (
                  <tr key={v.id} className="border-t border-border">
                    <td className="px-4 py-2">
                      {v.status === "ready" ? (
                        <Link href={`/videos/${v.id}`} className="hover:text-accent">
                          {v.title}
                        </Link>
                      ) : (
                        v.title
                      )}
                    </td>
                    <td className="px-4 py-2 capitalize text-text-muted">{v.status}</td>
                    <td className="px-4 py-2 text-right">{stats?.total_plays ?? 0}</td>
                    <td className="px-4 py-2 text-right">{stats?.unique_viewers ?? 0}</td>
                    <td className="px-4 py-2 text-right">
                      {formatDuration(stats?.avg_watch_duration ?? 0)}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <button
                        onClick={() => handleDelete(v.id)}
                        className="text-text-muted hover:text-red-400"
                        title="Delete video"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                );
              })}
              {allVideos.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-text-muted">
                    No videos uploaded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* User activity table */}
      <section>
        <h2 className="font-display text-lg font-bold mb-3 flex items-center gap-2">
          <Users size={18} className="text-accent" />
          User activity
        </h2>
        <div className="overflow-x-auto border border-border rounded-xl">
          <table className="w-full text-sm">
            <thead className="bg-surface text-text-muted">
              <tr>
                <th className="text-left px-4 py-2">User</th>
                <th className="text-left px-4 py-2">Email</th>
                <th className="text-right px-4 py-2">Videos watched</th>
                <th className="text-right px-4 py-2">Total watch time</th>
                <th className="text-right px-4 py-2">Last active</th>
              </tr>
            </thead>
            <tbody>
              {userActivity.map((u) => (
                <tr key={u.user_id} className="border-t border-border">
                  <td className="px-4 py-2">{u.name || "—"}</td>
                  <td className="px-4 py-2 text-text-muted">{u.email}</td>
                  <td className="px-4 py-2 text-right">{u.videos_watched}</td>
                  <td className="px-4 py-2 text-right">{formatDuration(u.total_watch_time)}</td>
                  <td className="px-4 py-2 text-right text-text-muted">
                    {formatDate(u.last_active)}
                  </td>
                </tr>
              ))}
              {userActivity.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-text-muted">
                    No user activity yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Repeated videos leaderboard */}
      <section>
        <h2 className="font-display text-lg font-bold mb-3 flex items-center gap-2">
          <Repeat size={18} className="text-accent" />
          Repeated plays
        </h2>
        <div className="overflow-x-auto border border-border rounded-xl">
          <table className="w-full text-sm">
            <thead className="bg-surface text-text-muted">
              <tr>
                <th className="text-left px-4 py-2">Video</th>
                <th className="text-left px-4 py-2">User</th>
                <th className="text-right px-4 py-2">Play count</th>
              </tr>
            </thead>
            <tbody>
              {repeated.map((r, idx) => (
                <tr key={idx} className="border-t border-border">
                  <td className="px-4 py-2">
                    <Link href={`/videos/${r.video_id}`} className="hover:text-accent">
                      {r.title}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-text-muted">{r.user_email}</td>
                  <td className="px-4 py-2 text-right">{r.play_count}</td>
                </tr>
              ))}
              {repeated.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center text-text-muted">
                    No videos have been watched more than once yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
