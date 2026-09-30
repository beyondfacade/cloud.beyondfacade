import type { ReactElement } from "react";
import type { RoomKey } from "../lib/rooms";

const common = { fill: "none", stroke: "currentColor", strokeWidth: 1.4, strokeLinecap: "round", strokeLinejoin: "round" } as const;

/** 방별 상징 — 조건 분기 대신 레지스트리. */
const GLYPHS: Record<RoomKey, (size: number) => ReactElement> = {
  security: (size) => (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <path {...common} d="M16 3.5 26 7.5v8c0 6.2-4.2 10.9-10 13-5.8-2.1-10-6.8-10-13v-8l10-4Z" />
      <path {...common} d="m11.5 16 3.2 3.2 6-6.4" />
    </svg>
  ),
  healthcare: (size) => (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <path {...common} d="M16 27S4.5 20.4 4.5 12.2A6.2 6.2 0 0 1 16 8.9a6.2 6.2 0 0 1 11.5 3.3C27.5 20.4 16 27 16 27Z" />
      <path {...common} d="M8.5 15.5h4l2-3.5 3 6.5 2-3h4" />
    </svg>
  ),
  facility: (size) => (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect {...common} x="5.5" y="5.5" width="21" height="8" rx="2" />
      <rect {...common} x="5.5" y="18.5" width="21" height="8" rx="2" />
      <path {...common} d="M10 9.5h.01M10 22.5h.01M15 9.5h7M15 22.5h7" />
    </svg>
  ),
  users: (size) => (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <circle {...common} cx="12.5" cy="11" r="4.5" />
      <path {...common} d="M4.5 26c.6-4.6 3.8-7.5 8-7.5s7.4 2.9 8 7.5" />
      <circle {...common} cx="22.5" cy="12.5" r="3.5" />
      <path {...common} d="M21.5 18.6c3.4.2 5.6 2.6 6 6" />
    </svg>
  ),
};

export function RoomGlyph({ room, size = 32 }: { room: RoomKey; size?: number }) {
  return GLYPHS[room](size);
}
