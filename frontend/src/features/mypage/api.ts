import { ApiError, apiPatch } from "@/shared/api/client";
import type { AdminMe } from "@/shared/api/types";
import { config } from "@/shared/config";

export const MAX_AVATAR_BYTES = 1024 * 1024;
export const AVATAR_TYPES = ["image/png", "image/jpeg", "image/webp"];

/** 본문은 이미지 바이트 그대로 — 서버가 파일 앞머리로 형식을 판별한다. */
export async function uploadAvatar(file: File): Promise<AdminMe> {
  const res = await fetch(`${config.apiBase}/admin/auth/avatar`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": file.type },
    body: file,
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(body?.error?.code ?? `HTTP_${res.status}`, body?.error?.message ?? "사진을 올리지 못했어요.");
  return body as AdminMe;
}

export const changeSpecialty = (specialty: string | null) => apiPatch<AdminMe>("/admin/auth/specialty", { specialty });
