"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { UploadCloud, Loader2, CheckCircle, XCircle, Film, Clock, X } from "lucide-react";
import { uploadVideo, getUploadStatus } from "@/services/video";
import { ApiError } from "@/services/api";
import { ProcessingStatus, Video } from "@/types";

// ── Types ─────────────────────────────────────────────────────────────────────

type Phase = "idle" | "uploading" | "processing" | "ready" | "failed";

const STATUS_COLOR: Record<string, string> = {
  pending:    "text-yellow-400",
  processing: "text-blue-400",
  ready:      "text-green-400",
  failed:     "text-red-400",
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function UploadForm() {
  const [title, setTitle]             = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile]               = useState<File | null>(null);

  const [phase, setPhase]                     = useState<Phase>("idle");
  const [message, setMessage]                 = useState("");
  const [video, setVideo]                     = useState<Video | null>(null);
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollingTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const router = useRouter();

  // ── Helpers ────────────────────────────────────────────────────────────────

  const clearFile = () => {
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const stopPolling = () => {
    if (pollingTimer.current) {
      clearTimeout(pollingTimer.current);
      pollingTimer.current = null;
    }
  };

  const reset = () => {
    stopPolling();
    setPhase("idle");
    setMessage("");
    setVideo(null);
    setProcessingStatus(null);
  };

  // ── Polling — called once upload returns, runs every 10 s ─────────────────

  const startPolling = (videoId: number) => {
    let attempts = 0;
    const MAX = 180; // 30 min max

    const poll = async () => {
      attempts++;
      try {
        const status = await getUploadStatus(videoId);
        setProcessingStatus(status);

        if (status.status === "ready") {
          setPhase("ready");
          setMessage("Your video is ready to watch.");
          return;
        }
        if (status.status === "failed") {
          setPhase("failed");
          setMessage("Transcoding failed. Please try uploading again.");
          return;
        }
        // Still processing — schedule next poll
        if (attempts < MAX) {
          pollingTimer.current = setTimeout(poll, 10_000);
        } else {
          setPhase("failed");
          setMessage("Timed out waiting for transcoding. Check the video page later.");
        }
      } catch {
        // Network blip — retry with a longer interval
        if (attempts < MAX) {
          pollingTimer.current = setTimeout(poll, 15_000);
        }
      }
    };

    pollingTimer.current = setTimeout(poll, 5_000); // first check after 5 s
  };

  // ── Submit ─────────────────────────────────────────────────────────────────

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !title.trim()) return;

    stopPolling();
    setPhase("uploading");
    setMessage("Uploading to S3…");
    setVideo(null);
    setProcessingStatus(null);

    try {
      const res = await uploadVideo(title.trim(), description.trim(), file);
      setVideo(res.video);

      if (res.video.status === "ready") {
        // Edge case: local FFmpeg finished synchronously
        setPhase("ready");
        setMessage("Video uploaded and ready to watch.");
        return;
      }

      // Normal path: GitHub Actions is handling it asynchronously
      setPhase("processing");
      setMessage(res.message);
      setTitle("");
      setDescription("");
      clearFile();
      startPolling(res.video.id);
    } catch (err) {
      setPhase("failed");
      setMessage(err instanceof ApiError ? err.message : "Upload failed. Please try again.");
    }
  };

  // ── Progress bar estimate ──────────────────────────────────────────────────

  const progressPct =
    processingStatus?.status === "ready"
      ? 100
      : processingStatus?.estimated_remaining_seconds != null && video?.duration_seconds
      ? Math.min(
          95,
          Math.round(
            100 -
              (processingStatus.estimated_remaining_seconds /
                (video.duration_seconds * 10)) *
                100
          )
        )
      : processingStatus?.status === "processing"
      ? 35
      : 0;

  const busy = phase === "uploading" || phase === "processing";

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <form onSubmit={handleSubmit} className="max-w-lg space-y-4">

      {/* Title */}
      <div>
        <label className="block text-sm mb-1 text-text-muted">Title</label>
        <input
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          disabled={busy}
          className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm
                     focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent
                     disabled:opacity-50"
          placeholder="Video title"
        />
      </div>

      {/* Description */}
      <div>
        <label className="block text-sm mb-1 text-text-muted">Description</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={busy}
          rows={3}
          className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm
                     focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent
                     disabled:opacity-50"
          placeholder="What's this video about?"
        />
      </div>

      {/* File picker */}
      <div>
        <label className="block text-sm mb-1 text-text-muted">Video file</label>
        {!file ? (
          <label className="flex flex-col items-center justify-center gap-2 border border-dashed
                            border-border rounded-lg py-8 cursor-pointer hover:border-accent
                            transition-colors">
            <UploadCloud size={28} className="text-text-muted" />
            <span className="text-sm text-text-muted">Click to choose a video file</span>
            <input
              ref={fileInputRef}
              type="file"
              accept="video/*"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                setFile(f);
                if (!title) setTitle(f.name.replace(/\.[^.]+$/, ""));
              }}
            />
          </label>
        ) : (
          <div className="flex items-center gap-3 bg-surface border border-border rounded-lg px-3 py-2.5">
            <Film size={16} className="text-accent flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{file.name}</p>
              <p className="text-xs text-text-muted">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
            </div>
            <button type="button" onClick={clearFile} className="text-text-muted hover:text-red-400">
              <X size={14} />
            </button>
          </div>
        )}
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={busy || !file || !title.trim()}
        className="flex items-center justify-center gap-2 w-full bg-accent text-black font-medium
                   rounded-lg py-2.5 disabled:opacity-60 transition-opacity"
      >
        {busy && <Loader2 size={16} className="animate-spin" />}
        {phase === "uploading"   ? "Uploading…"             :
         phase === "processing"  ? "Transcoding in progress…" :
                                   "Upload video"}
      </button>

      {/* Status panel — shown after submit */}
      {phase !== "idle" && (
        <div className={`rounded-lg px-3 py-3 space-y-2 text-sm border ${
          phase === "failed" ? "bg-red-950/40 border-red-800/40" :
          phase === "ready"  ? "bg-green-950/40 border-green-800/40" :
                               "bg-surface border-border"
        }`}>

          {/* Header */}
          <div className="flex items-center gap-2">
            {phase === "failed"     && <XCircle    size={15} className="text-red-400" />}
            {phase === "ready"      && <CheckCircle size={15} className="text-green-400" />}
            {busy                   && <Loader2    size={15} className="animate-spin text-accent" />}
            <span className={
              phase === "failed" ? "text-red-400 font-medium" :
              phase === "ready"  ? "text-green-400 font-medium" :
                                   "text-text-muted"
            }>
              {message}
            </span>
          </div>

          {/* Live processing detail */}
          {processingStatus && phase === "processing" && (
            <div className="space-y-1.5 pt-1">
              <div className="flex justify-between text-xs">
                <span>
                  Status:{" "}
                  <span className={STATUS_COLOR[processingStatus.status] ?? "text-text-muted"}>
                    {processingStatus.status}
                  </span>
                </span>
                {(processingStatus.estimated_remaining_seconds ?? 0) > 0 && (
                  <span className="flex items-center gap-1 text-text-muted">
                    <Clock size={10} />
                    ~{Math.ceil(processingStatus.estimated_remaining_seconds! / 60)} min left
                  </span>
                )}
              </div>
              <div className="h-1.5 bg-surface-2 rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent rounded-full transition-all duration-1000"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <p className="text-xs text-text-muted">{processingStatus.message}</p>
            </div>
          )}

          {/* Ready — watch button */}
          {phase === "ready" && video && (
            <div className="flex gap-2 pt-1">
              <button
                type="button"
                onClick={() => router.push(`/videos/${video.id}`)}
                className="flex-1 bg-accent text-black text-xs font-semibold rounded px-3 py-1.5"
              >
                Watch now
              </button>
              <button
                type="button"
                onClick={reset}
                className="text-xs text-text-muted hover:text-text-primary px-2"
              >
                Upload another
              </button>
            </div>
          )}

          {/* Failed — retry */}
          {phase === "failed" && (
            <button type="button" onClick={reset} className="text-xs text-red-400 hover:underline">
              Try again
            </button>
          )}
        </div>
      )}
    </form>
  );
}
