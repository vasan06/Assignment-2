"use client";

import Link from "next/link";
import Image from "next/image";
import { Clock, PlayCircle } from "lucide-react";
import { Video } from "@/types";

function formatDuration(secs?: number | null): string {
  if (!secs) return "";
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

interface Props {
  video: Video;
}

export default function VideoCard({ video }: Props) {
  const duration = formatDuration(video.duration_seconds);

  return (
    <Link
      href={`/videos/${video.id}`}
      className="group flex flex-col gap-2 cursor-pointer focus:outline-none"
    >
      {/* Thumbnail */}
      <div className="relative aspect-video rounded-lg overflow-hidden bg-surface-2">
        {video.thumbnail_url ? (
          <Image
            src={video.thumbnail_url}
            alt={video.title}
            fill
            className="object-cover transition-transform duration-300 group-hover:scale-105"
            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
          />
        ) : (
          <div className="flex items-center justify-center w-full h-full text-text-muted">
            <PlayCircle size={36} />
          </div>
        )}

        {/* Duration badge */}
        {duration && (
          <span className="absolute bottom-1.5 right-1.5 text-xs bg-black/70 text-white px-1.5 py-0.5 rounded">
            {duration}
          </span>
        )}

        {/* Hover play overlay */}
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-black/30">
          <PlayCircle size={44} className="text-white drop-shadow" />
        </div>
      </div>

      {/* Metadata */}
      <div>
        <h3 className="font-semibold text-sm leading-snug line-clamp-2 group-hover:text-accent transition-colors">
          {video.title}
        </h3>
        <div className="flex items-center gap-1.5 text-xs text-text-muted mt-1">
          <Clock size={12} />
          <span>{formatDate(video.created_at)}</span>
          {video.available_resolutions && (
            <>
              <span>·</span>
              <span>{video.available_resolutions.split(",").length} resolutions</span>
            </>
          )}
        </div>
      </div>
    </Link>
  );
}
