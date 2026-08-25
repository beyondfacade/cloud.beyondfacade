export const config = {
  apiBase: process.env.NEXT_PUBLIC_API_BASE ?? "/api/mock",
  vworldKey: process.env.NEXT_PUBLIC_VWORLD_KEY ?? "",
} as const;
