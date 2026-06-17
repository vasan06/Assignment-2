"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Clock, Layers, AlertCircle } from "lucide-react";
import { Video } from "@/types";
import { getVideo, logWatch } from "@/services/video";
import VideoPlayer from "@/components/VideoPlayer";

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric", month: "long", day: "numeric",
  });
}

function formatDuration(s?: number | null) {
  if (!s) return null;
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m ${sec}s`;
}

export default function VideoPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [video, setVideo] = useState<Video | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const watchStartRef = useRef<number>(Date.now());
  const loggedRef = useRef(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getVideo(Number(id))
      .then((v) => { setVideo(v); watchStartRef.current = Date.now(); })
      .catch(() => setError("Video not found."))
      .finally(() => setLoading(false));
  }, [id]);

  // Log watch duration when leaving page
  useEffect(() => {
    return () => {
      if (!loggedRef.current && video) {
        const watchDuration = Math.floor((Date.now() - watchStartRef.current) / 1000);
        if (watchDuration > 3) {
          logWatch(video.id, watchDuration).catch(() => {});
          loggedRef.current = true;
        }
      }
    };
  }, [video]);

  if (loading) {
    return (
      <div className="px-6 py-8 max-w-5xl mx-auto">
        <div className="animate-pulse space-y-4">
          <div className="h-5 w-24 bg-surface-2 rounded" />
          <div className="aspect-video bg-surface-2 rounded-xl" />
          <div className="h-6 w-2/3 bg-surface-2 rounded" />
          <div className="h-4 w-1/3 bg-surface-2 rounded" />
        </div>
      </div>
    );
  }

  if (error || !video) {
    return (
      <div className="px-6 py-8 max-w-5xl mx-auto">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-sm text-text-muted hover:text-text-primary mb-6 transition-colors"
        >
          <ArrowLeft size={16} /> Back
        </button>
        <div className="flex items-center gap-3 text-red-400">
          <AlertCircle size={20} />
          <span>{error || "Video not found."}</span>
        </div>
      </div>
    );
  }

  const resolutions = video.available_resolutions
    ? video.available_resolutions.split(",").map((r) => r.trim())
    : [];

  return (
    <div className="px-6 py-6 max-w-5xl mx-auto">
      {/* Back button */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-2 text-sm text-text-muted hover:text-text-primary mb-5 transition-colors"
      >
        <ArrowLeft size={16} /> Back to Browse
      </button>

      {/* Video player */}
      <VideoPlayer video={video} />

      {/* Video info */}
      <div className="mt-5 space-y-3">
        <h1 className="font-display text-xl md:text-2xl font-bold leading-snug">
          {video.title}
        </h1>

        <div className="flex flex-wrap items-center gap-4 text-sm text-text-muted">
          <span className="flex items-center gap-1.5">
            <Clock size={14} />
            {formatDate(video.created_at)}
          </span>
          {formatDuration(video.duration_seconds) && (
            <span className="flex items-center gap-1.5">
              <Clock size={14} />
              {formatDuration(video.duration_seconds)}
            </span>
          )}
          {resolutions.length > 0 && (
            <span className="flex items-center gap-1.5">
              <Layers size={14} />
              Available: {resolutions.join(", ")}
            </span>
          )}
        </div>

        {video.description && (
          <p className="text-sm text-text-muted leading-relaxed max-w-2xl">
            {video.description}
          </p>
        )}
      </div>
    </div>
  );
}
