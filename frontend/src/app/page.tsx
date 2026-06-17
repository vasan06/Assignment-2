"use client";

import { useEffect, useState, useCallback } from "react";
import { Film } from "lucide-react";
import { Video } from "@/types";
import { listVideos } from "@/services/video";
import VideoCard from "@/components/VideoCard";
import SearchBar from "@/components/SearchBar";
import VideoGridSkeleton from "@/components/VideoGridSkeleton";

// Home page auto-refreshes every 30 seconds to pick up newly processed videos
const AUTO_REFRESH_INTERVAL_MS = 30_000;

export default function HomePage() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const fetchVideos = useCallback(
    async (showLoader = false) => {
      if (showLoader) setLoading(true);
      setError("");
      try {
        const data = await listVideos(search || undefined);
        setVideos(data);
        setLastRefreshed(new Date());
      } catch {
        setError("Couldn't load videos. Check that the API is running.");
      } finally {
        if (showLoader) setLoading(false);
      }
    },
    [search]
  );

  // Initial load + search change → show skeleton
  useEffect(() => {
    setLoading(true);
    fetchVideos(true);
  }, [fetchVideos]);

  // Auto-refresh every 30 seconds (silent, no skeleton flash)
  useEffect(() => {
    const interval = setInterval(() => {
      fetchVideos(false);
    }, AUTO_REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchVideos]);

  return (
    <div className="px-6 py-6 md:px-10 md:py-8">
      <div className="mb-8">
        <SearchBar onSearch={setSearch} placeholder="Search videos by title" />
      </div>

      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display text-2xl font-bold">
          {search ? `Results for "${search}"` : "Browse"}
        </h1>
        {lastRefreshed && !loading && (
          <span className="text-xs text-text-muted">
            Auto-refreshes every 30s · Last updated {lastRefreshed.toLocaleTimeString()}
          </span>
        )}
      </div>

      {error && <p className="text-sm text-red-400 mb-4">{error}</p>}

      {/* Skeleton loading state */}
      {loading && <VideoGridSkeleton count={8} />}

      {/* Empty state */}
      {!loading && !error && videos.length === 0 && (
        <div className="flex flex-col items-center justify-center text-center text-text-muted py-20 gap-3">
          <Film size={36} />
          <p>
            {search
              ? "No videos match that search."
              : "No videos yet. Check back soon."}
          </p>
        </div>
      )}

      {/* Video grid */}
      {!loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-6">
          {videos.map((v) => (
            <VideoCard key={v.id} video={v} />
          ))}
        </div>
      )}
    </div>
  );
}
