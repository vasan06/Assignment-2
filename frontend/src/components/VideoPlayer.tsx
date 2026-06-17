"use client";

import { useEffect, useRef, useState } from "react";
import Hls from "hls.js";
import {
  Play, Pause, Volume2, VolumeX, Maximize, Minimize,
  Settings, SkipBack, SkipForward, AlertCircle,
} from "lucide-react";
import { Video } from "@/types";

interface Level {
  name: string;
  height: number;
  index: number;
}

function formatTime(s: number): string {
  if (!s || isNaN(s)) return "0:00";
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = Math.floor(s % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  return `${m}:${String(sec).padStart(2, "0")}`;
}

interface Props {
  video: Video;
  onTimeUpdate?: (currentTime: number) => void;
}

export default function VideoPlayer({ video, onTimeUpdate }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);
  const hideControlsTimer = useRef<NodeJS.Timeout | null>(null);

  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(1);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [buffered, setBuffered] = useState(0);
  const [fullscreen, setFullscreen] = useState(false);
  const [showControls, setShowControls] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [levels, setLevels] = useState<Level[]>([]);
  const [currentLevel, setCurrentLevel] = useState(-1); // -1 = Auto
  const [error, setError] = useState("");

  // Map resolution name → HLS level index
  const resolutionNames = ["1080p", "720p", "480p", "360p", "240p", "144p"];

  // ---- HLS setup ----
  useEffect(() => {
    const vid = videoRef.current;
    if (!vid || !video.master_playlist_url) return;

    if (Hls.isSupported()) {
      const hls = new Hls({ startLevel: -1, capLevelToPlayerSize: true });
      hlsRef.current = hls;
      hls.loadSource(video.master_playlist_url);
      hls.attachMedia(vid);

      hls.on(Hls.Events.MANIFEST_PARSED, (_, data) => {
        const lvls: Level[] = data.levels.map((l, i) => ({
          name: resolutionNames.find((n) => {
            const h = parseInt(n);
            return Math.abs(l.height - h) < 50;
          }) || `${l.height}p`,
          height: l.height,
          index: i,
        }));
        // Sort highest → lowest
        lvls.sort((a, b) => b.height - a.height);
        setLevels(lvls);
        setCurrentLevel(-1);
      });

      hls.on(Hls.Events.ERROR, (_, data) => {
        if (data.fatal) {
          setError("Playback error. Please reload.");
        }
      });
    } else if (vid.canPlayType("application/vnd.apple.mpegurl")) {
      // Safari native HLS
      vid.src = video.master_playlist_url;
    } else {
      setError("Your browser does not support HLS video.");
    }

    return () => {
      hlsRef.current?.destroy();
      hlsRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [video.master_playlist_url]);

  // ---- Auto-hide controls ----
  const resetControlsTimer = () => {
    setShowControls(true);
    if (hideControlsTimer.current) clearTimeout(hideControlsTimer.current);
    if (playing) {
      hideControlsTimer.current = setTimeout(() => setShowControls(false), 3000);
    }
  };

  useEffect(() => {
    return () => {
      if (hideControlsTimer.current) clearTimeout(hideControlsTimer.current);
    };
  }, []);

  // ---- Playback controls ----
  const togglePlay = () => {
    const vid = videoRef.current;
    if (!vid) return;
    if (vid.paused) {
      vid.play();
    } else {
      vid.pause();
    }
    resetControlsTimer();
  };

  const skip = (secs: number) => {
    if (videoRef.current) videoRef.current.currentTime += secs;
    resetControlsTimer();
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    videoRef.current.muted = !videoRef.current.muted;
    setMuted(videoRef.current.muted);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = parseFloat(e.target.value);
    if (!videoRef.current) return;
    videoRef.current.volume = v;
    setVolume(v);
    setMuted(v === 0);
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const bar = progressRef.current;
    if (!bar || !videoRef.current || !duration) return;
    const rect = bar.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    videoRef.current.currentTime = pct * duration;
    resetControlsTimer();
  };

  const toggleFullscreen = () => {
    const el = containerRef.current;
    if (!el) return;
    if (!document.fullscreenElement) {
      el.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  };

  const setResolution = (levelIndex: number) => {
    if (hlsRef.current) {
      hlsRef.current.currentLevel = levelIndex;
      setCurrentLevel(levelIndex);
    }
    setShowSettings(false);
    resetControlsTimer();
  };

  const currentResolutionLabel =
    currentLevel === -1
      ? "Auto"
      : levels.find((l) => l.index === currentLevel)?.name ?? "Auto";

  // ---- Native video events ----
  const handleTimeUpdate = () => {
    const vid = videoRef.current;
    if (!vid) return;
    setCurrentTime(vid.currentTime);
    onTimeUpdate?.(vid.currentTime);

    // Buffered
    if (vid.buffered.length > 0) {
      setBuffered(vid.buffered.end(vid.buffered.length - 1));
    }
  };

  useEffect(() => {
    const el = document.addEventListener("fullscreenchange", () => {
      setFullscreen(!!document.fullscreenElement);
    });
    return () => document.removeEventListener("fullscreenchange", () => {});
  }, []);

  const progressPct = duration ? (currentTime / duration) * 100 : 0;
  const bufferedPct = duration ? (buffered / duration) * 100 : 0;

  if (error) {
    return (
      <div className="aspect-video bg-black rounded-xl flex items-center justify-center gap-3 text-red-400">
        <AlertCircle size={24} />
        <span>{error}</span>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`relative aspect-video bg-black rounded-xl overflow-hidden group select-none ${
        fullscreen ? "rounded-none" : ""
      }`}
      onMouseMove={resetControlsTimer}
      onMouseLeave={() => playing && setShowControls(false)}
      onClick={togglePlay}
    >
      <video
        ref={videoRef}
        className="w-full h-full"
        onPlay={() => { setPlaying(true); resetControlsTimer(); }}
        onPause={() => { setPlaying(false); setShowControls(true); }}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={() => setDuration(videoRef.current?.duration ?? 0)}
        playsInline
      />

      {/* Controls overlay */}
      <div
        className={`absolute inset-0 flex flex-col justify-end bg-gradient-to-t from-black/80 via-transparent to-transparent transition-opacity duration-300 ${
          showControls ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Progress bar */}
        <div className="px-4 pb-2">
          <div
            ref={progressRef}
            className="relative h-1.5 bg-white/20 rounded-full cursor-pointer group/bar"
            onClick={handleSeek}
          >
            {/* Buffered */}
            <div
              className="absolute inset-y-0 left-0 bg-white/30 rounded-full"
              style={{ width: `${bufferedPct}%` }}
            />
            {/* Played */}
            <div
              className="absolute inset-y-0 left-0 bg-accent rounded-full"
              style={{ width: `${progressPct}%` }}
            />
            {/* Thumb */}
            <div
              className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3.5 h-3.5 bg-white rounded-full shadow opacity-0 group-hover/bar:opacity-100 transition-opacity"
              style={{ left: `${progressPct}%` }}
            />
          </div>

          {/* Time */}
          <div className="flex justify-between text-xs text-white/70 mt-1">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>

        {/* Buttons row */}
        <div className="flex items-center gap-3 px-4 pb-3">
          {/* Skip back */}
          <button className="text-white hover:text-accent transition-colors" onClick={() => skip(-10)}>
            <SkipBack size={18} />
          </button>

          {/* Play / Pause */}
          <button className="text-white hover:text-accent transition-colors" onClick={togglePlay}>
            {playing ? <Pause size={22} /> : <Play size={22} />}
          </button>

          {/* Skip forward */}
          <button className="text-white hover:text-accent transition-colors" onClick={() => skip(10)}>
            <SkipForward size={18} />
          </button>

          {/* Volume */}
          <button className="text-white hover:text-accent transition-colors" onClick={toggleMute}>
            {muted || volume === 0 ? <VolumeX size={18} /> : <Volume2 size={18} />}
          </button>
          <input
            type="range" min={0} max={1} step={0.05}
            value={muted ? 0 : volume}
            onChange={handleVolumeChange}
            className="w-20 accent-accent"
          />

          <div className="flex-1" />

          {/* Resolution picker */}
          <div className="relative">
            <button
              className="flex items-center gap-1 text-white text-xs hover:text-accent transition-colors px-2 py-1 rounded border border-white/20"
              onClick={() => setShowSettings((s) => !s)}
            >
              <Settings size={14} />
              {currentResolutionLabel}
            </button>

            {showSettings && (
              <div className="absolute bottom-9 right-0 bg-surface-1 border border-border rounded-lg overflow-hidden shadow-xl z-50 min-w-[110px]">
                <button
                  className={`w-full text-left px-4 py-2 text-sm hover:bg-surface-2 transition-colors ${
                    currentLevel === -1 ? "text-accent font-semibold" : "text-text-primary"
                  }`}
                  onClick={() => setResolution(-1)}
                >
                  Auto
                </button>
                {levels.map((l) => (
                  <button
                    key={l.index}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-surface-2 transition-colors ${
                      currentLevel === l.index ? "text-accent font-semibold" : "text-text-primary"
                    }`}
                    onClick={() => setResolution(l.index)}
                  >
                    {l.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Fullscreen */}
          <button className="text-white hover:text-accent transition-colors" onClick={toggleFullscreen}>
            {fullscreen ? <Minimize size={18} /> : <Maximize size={18} />}
          </button>
        </div>
      </div>

      {/* Centre play/pause icon flash */}
      {!playing && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <Play size={56} className="text-white/80 drop-shadow-lg" />
        </div>
      )}
    </div>
  );
}
