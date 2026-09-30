"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { ADMIN_LOGIN_PATH } from "@/shared/admin-gate";
import { ThemeToggle } from "@/shared/ui/theme-toggle";
import { logoutAdmin } from "../api";
import { useAdminMe } from "../hooks/use-admin-query";
import { ROOMS } from "../lib/rooms";
import { RoomGlyph } from "./room-glyph";
import styles from "./admin.module.css";

const ROLE_LABEL = { viewer: "조회", operator: "운영" } as const;

export function AdminShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const me = useAdminMe();
  const logout = useMutation({
    mutationFn: logoutAdmin,
    onSettled: () => {
      queryClient.removeQueries({ queryKey: ["admin"] });
      router.replace(ADMIN_LOGIN_PATH);
    },
  });

  return (
    <div className={styles.shell}>
      <header className={styles.bar}>
        <div className={styles.barInner}>
          <Link href="/admin" className={styles.brand} aria-label="Metabole 관제실 홈">
            <span className={styles.mark} aria-hidden="true">m.</span>
            <span className={styles.wordmark}>Metabole<small>CONTROL ROOM</small></span>
          </Link>
          <nav className={styles.roomNav} aria-label="관리자 방">
            {ROOMS.map((room) => (
              <Link
                key={room.key}
                href={room.href}
                prefetch={false}
                className={styles.roomLink}
                aria-current={pathname.startsWith(room.href) ? "page" : undefined}
              >
                <RoomGlyph room={room.key} size={16} />
                {room.title}
              </Link>
            ))}
          </nav>
          <div className={styles.barSide}>
            {me.data && (
              <span className={styles.who}>
                <span>{me.data.username}</span>
                <span className={styles.role} data-role={me.data.role}>{ROLE_LABEL[me.data.role]}</span>
              </span>
            )}
            <ThemeToggle />
            <button
              type="button"
              className={styles.ghostButton}
              onClick={() => logout.mutate()}
              disabled={logout.isPending}
            >
              로그아웃
            </button>
          </div>
        </div>
      </header>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
