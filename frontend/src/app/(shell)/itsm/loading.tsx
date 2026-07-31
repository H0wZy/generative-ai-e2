import { Skeleton, SkeletonRows } from "@/components/ui/skeleton";

export default function ItsmLoading() {
  return (
    <div className="flex flex-col gap-4 p-4 md:p-6">
      <Skeleton className="h-7 w-44" />
      <Skeleton className="h-9 w-full max-w-2xl" />
      <SkeletonRows rows={8} />
    </div>
  );
}
