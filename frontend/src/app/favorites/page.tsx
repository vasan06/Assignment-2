"use client";

import { useEffect, useState } from "react";
import { Heart, Loader2 } from "lucide-react";
import Link from "next/link";
import { Video } from "@/types";
import { getMyFavorites } from "@/services/video";
import { useAuth } from "@/context/AuthContext";
import VideoCard from "@/components/VideoCard";

export default function FavoritesPage() {
  const { user, loading: authLoading } = useAuth();
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }
    getMyFavorites()
      .then(setVideos)
      .finally(() => setLoading(false));
  }, [user]);

  if (authLoading || loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="animate-spin text-text-muted" size={32} />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-3 text-center px-4">
        <Heart size={32} className="text-text-muted" />
        <p className="text-text-muted">
          <Link href="/login" className="text-accent hover:underline">
            Log in
          </Link>{" "}
          to see your favorites.
        </p>
      </div>
    );
  }

  return (
    <div className="px-6 py-6 md:px-10 md:py-8">
      <h1 className="font-display text-2xl font-bold mb-6">Favorites</h1>

      {videos.length === 0 ? (
        <div className="flex flex-col items-center justify-center text-center text-text-muted py-20 gap-3">
          <Heart size={36} />
          <p>No favorites yet. Tap the heart on a video to save it here.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-6">
          {videos.map((v) => (
            <VideoCard key={v.id} video={v} />
          ))}
        </div>
      )}
    </div>
  );
}
