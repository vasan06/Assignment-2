"use client";

import { useRef, useState } from "react";
import { Upload, CheckCircle, AlertCircle, Loader2, Film, X } from "lucide-react";
import { uploadVideo, getUploadStatus } from "@/services/video";
import { Video, ProcessingStatus } from "@/types";

export default function AdminUploadPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);

  const [uploading, setUploading] = useState(false);
  const [uploadDone, setUploadDone] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  const [uploadError, setUploadError] = useState("");

  const [processingVideo, setProcessingVideo] = useState<Video | null>(null);
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus | null>(null);
  const [polling, setPolling] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    if (!title) setTitle(f.name.replace(/\.[^.]+$/, ""));
    // Object URL for local preview thumbnail
    setPreview(URL.createObjectURL(f));
  };

  const clearFile = () => {
    setFile(null);
    if (preview) URL.revokeObjectURL(preview);
    setPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // Poll processing status every 10s until ready or failed
  const startPolling = (videoId: number) => {
    setPolling(true);
    let attempts = 0;
    const MAX_ATTEMPTS = 180; // 30 minutes max

    const poll = async () => {
      attempts++;
      try {
        const status = await getUploadStatus(videoId);
        setProcessingStatus(status);

        if (status.status === "ready" || status.status === "failed") {
          setPolling(false);
          return;
        }

        if (attempts < MAX_ATTEMPTS) {
          setTimeout(poll, 10_000); // every 10 seconds
        } else {
          setPolling(false);
        }
      } catch {
        if (attempts < MAX_ATTEMPTS) setTimeout(poll, 15_000);
        else setPolling(false);
      }
    };
    setTimeout(poll, 5000); // first check after 5s
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !title.trim()) return;

    setUploading(true);
    setUploadError("");
    setUploadDone(false);
    setProcessingVideo(null);
    setProcessingStatus(null);

    try {
      const result = await uploadVideo(title.trim(), description.trim(), file);
      setUploadDone(true);
      setUploadMessage(result.message);
      setProcessingVideo(result.video);
      startPolling(result.video.id);
      // Reset form fields
      setTitle("");
      setDescription("");
      clearFile();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Upload failed. Check API connection.";
      setUploadError(msg);
    } finally {
      setUploading(false);
    }
  };

  const statusColor = {
    pending: "text-yellow-400",
    processing: "text-blue-400",
    ready: "text-green-400",
    failed: "text-red-400",
  };

  const progressPct =
    processingStatus?.estimated_remaining_seconds != null &&
    processingVideo?.duration_seconds
      ? Math.min(
          95,
          Math.round(
            100 -
              (processingStatus.estimated_remaining_seconds /
                (processingVideo.duration_seconds * 10)) *
                100
          )
        )
      : processingStatus?.status === "ready"
      ? 100
      : processingStatus?.status === "processing"
      ? 40
      : 0;

  return (
    <div className="px-6 py-8 max-w-2xl mx-auto">
      <h1 className="font-display text-2xl font-bold mb-8">Upload Video</h1>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Title */}
        <div>
          <label className="block text-sm font-medium mb-1.5">Title *</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            placeholder="Enter video title"
            className="w-full bg-surface-2 border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-accent transition-colors"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium mb-1.5">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            placeholder="Optional description"
            className="w-full bg-surface-2 border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-accent transition-colors resize-none"
          />
        </div>

        {/* File picker */}
        <div>
          <label className="block text-sm font-medium mb-1.5">Video File *</label>
          {!file ? (
            <div
              className="border-2 border-dashed border-border rounded-xl p-8 flex flex-col items-center gap-3 text-text-muted cursor-pointer hover:border-accent hover:text-text-primary transition-colors"
              onClick={() => fileInputRef.current?.click()}
            >
              <Film size={32} />
              <div className="text-sm text-center">
                <span className="text-accent font-medium">Click to select</span> a video file
                <p className="text-xs mt-1">MP4, MOV, MKV, AVI, WebM supported</p>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-3 bg-surface-2 border border-border rounded-lg px-4 py-3">
              <Film size={18} className="text-accent flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{file.name}</p>
                <p className="text-xs text-text-muted">
                  {(file.size / 1024 / 1024).toFixed(1)} MB
                </p>
              </div>
              <button
                type="button"
                className="text-text-muted hover:text-red-400 transition-colors"
                onClick={clearFile}
              >
                <X size={16} />
              </button>
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>

        {/* Upload button */}
        <button
          type="submit"
          disabled={uploading || !file || !title.trim()}
          className="w-full flex items-center justify-center gap-2 bg-accent hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-lg transition-colors"
        >
          {uploading ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              Uploading…
            </>
          ) : (
            <>
              <Upload size={18} />
              Upload & Process
            </>
          )}
        </button>

        {uploadError && (
          <div className="flex items-center gap-2 text-red-400 text-sm">
            <AlertCircle size={16} />
            <span>{uploadError}</span>
          </div>
        )}
      </form>

      {/* Post-upload status */}
      {uploadDone && processingVideo && (
        <div className="mt-8 p-5 bg-surface-2 rounded-xl border border-border space-y-4">
          <div className="flex items-center gap-2">
            <CheckCircle size={18} className="text-green-400" />
            <span className="text-sm font-semibold text-green-400">
              Upload successful!
            </span>
          </div>
          <p className="text-sm text-text-muted">{uploadMessage}</p>

          {/* Processing status */}
          {processingStatus && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">Processing status</span>
                <span
                  className={`font-semibold capitalize ${
                    statusColor[processingStatus.status as keyof typeof statusColor] ??
                    "text-text-muted"
                  }`}
                >
                  {processingStatus.status}
                  {polling && processingStatus.status === "processing" && (
                    <Loader2 size={12} className="inline ml-1.5 animate-spin" />
                  )}
                </span>
              </div>

              {/* Progress bar */}
              {processingStatus.status === "processing" && (
                <div className="h-1.5 bg-surface-1 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-all duration-1000"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
              )}

              <p className="text-xs text-text-muted leading-relaxed">
                {processingStatus.message}
              </p>

              {processingStatus.status === "ready" && (
                <p className="text-xs text-green-400">
                  ✓ All resolutions ready: {processingStatus.available_resolutions}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
