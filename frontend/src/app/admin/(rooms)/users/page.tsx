import { Suspense } from "react";
import { UsersRoom } from "@/features/admin/components/users-room";
import { RouteFallback } from "@/shared/ui/route-fallback";

export default function UsersRoute() {
  return (
    <Suspense fallback={<RouteFallback label="유저 관리를 불러오는 중" />}>
      <UsersRoom />
    </Suspense>
  );
}
