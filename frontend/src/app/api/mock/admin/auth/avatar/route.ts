import { adminError, mockAdminFrom, mockMe, unauthenticated } from "../../../admin-fixtures";
import { accounts } from "../../users/store";

const MAX_AVATAR_BYTES = 1024 * 1024;

function imageType(bytes: Uint8Array): string | null {
  const head = (start: number, end: number) => String.fromCharCode(...bytes.slice(start, end));
  if (head(0, 8) === "\x89PNG\r\n\x1a\n") return "image/png";
  if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return "image/jpeg";
  if (head(0, 4) === "RIFF" && head(8, 12) === "WEBP") return "image/webp";
  return null;
}

/** 실 API와 같은 계약 — 본문은 이미지 바이트 그대로, PNG·JPEG·WebP 1MB 이하. 응답은 AdminMe. */
export async function PUT(request: Request) {
  const me = mockAdminFrom(request);
  if (!me) return unauthenticated();
  const bytes = new Uint8Array(await request.arrayBuffer());
  const type = imageType(bytes);
  if (!bytes.length || bytes.length > MAX_AVATAR_BYTES || !type) {
    return adminError(400, "INVALID_AVATAR", "PNG·JPG·WebP 사진(1MB 이하)만 올릴 수 있습니다.");
  }
  const account = accounts.get(me.username)!;
  account.avatar = { version: (account.avatar?.version ?? 0) + 1, type, bytes };
  return Response.json(mockMe(me.username));
}
