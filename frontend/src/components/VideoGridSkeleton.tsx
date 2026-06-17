export default function VideoGridSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-6">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="animate-pulse">
          <div className="aspect-video bg-surface-2 rounded-lg mb-3" />
          <div className="h-4 bg-surface-2 rounded w-3/4 mb-2" />
          <div className="h-3 bg-surface-2 rounded w-1/2" />
        </div>
      ))}
    </div>
  );
}
