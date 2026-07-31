import { Skeleton, SkeletonRows } from "@/components/ui/skeleton";

export default function RootLoading() {
  return (
    <div className="flex flex-col gap-4 p-6">
      <Skeleton className="h-7 w-48" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
      <SkeletonRows rows={6} />
    </div>
  );
}
