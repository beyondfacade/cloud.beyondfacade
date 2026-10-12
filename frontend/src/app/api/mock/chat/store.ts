/** 채팅 mock — 개발 서버 프로세스 동안만 유지. 회원 id는 mock 회원 목록 순서(ops=1, viewer=2, …). */
import type { AdminMe, AdminRole, ChatExpert, ChatExpertStatus, ChatMessage, ChatReply, ChatRoom } from "@/shared/api/types";
import { adminError } from "../admin-fixtures";
import { accounts, memberId } from "../admin/users/store";

export const PAGE_SIZE = 50;
const MAX_BODY_LENGTH = 500;
const MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024;
const RATE_LIMIT = { count: 5, windowMs: 10_000 };
const FIXED_ROOMS = [
  { key: "global", kind: "global", title: "전체", admits: () => true },
  { key: "operators", kind: "operators", title: "관리자", admits: (me: AdminMe) => me.can_operate },
] as const;
const DIRECT = /^dm:([1-9]\d*):([1-9]\d*)$/;

export const messages: ChatMessage[] = [
  {
    id: 1, room: "global", sender_id: 1, sender_username: "ops", sender_role: "operator",
    body: "메타볼레 채팅에 오신 걸 환영해요. 상권 이야기 자유롭게 나눠 주세요.", deleted: false,
    created_at: "2026-10-12T00:10:00Z", reply_to: null, attachment: null, sender_avatar_version: null,
  },
  {
    id: 2, room: "global", sender_id: 2, sender_username: "viewer", sender_role: "viewer",
    body: "성수동 카페 리포트 보신 분 계세요?", deleted: false, created_at: "2026-10-12T00:12:00Z", reply_to: null,
    attachment: null, sender_avatar_version: null,
  },
];
/** 메시지 id → PDF 바이트 */
export const attachments = new Map<number, Uint8Array>();
/** "회원id:방" → 마지막으로 읽은 메시지 id */
export const reads = new Map<string, number>();
/** 전문가 상담 시간당 요금(원) — 실 API는 admin_user.hourly_rate */
const HOURLY_RATES = new Map([["park.expert", 30_000]]);
const CONSULTATION_HOURS = [1, 2, 3];
/** 산 상담 — 끝나기 전까지 그 전문가는 '대화 중' */
export const consultations: { viewerId: number; expertId: number; endsAt: number }[] = [];

export { memberId };

const usernameOf = (id: number) => [...accounts.keys()][id - 1];

function directPartner(key: string, me: number): number | null {
  const match = DIRECT.exec(key);
  if (!match) return null;
  const [low, high] = [Number(match[1]), Number(match[2])];
  if (low >= high || (me !== low && me !== high)) return null;
  return me === low ? high : low;
}

/** 들어갈 수 없으면 실 API와 같은 오류 응답, 들어갈 수 있으면 null. */
export function roomDenied(me: AdminMe, key: string): Response | null {
  const fixed = FIXED_ROOMS.find((room) => room.key === key);
  if (fixed) return fixed.admits(me) ? null : adminError(403, "CHAT_ROOM_FORBIDDEN", "들어갈 수 없는 채팅방입니다.");
  const match = DIRECT.exec(key);
  if (!match || Number(match[1]) >= Number(match[2])) return adminError(404, "CHAT_ROOM_NOT_FOUND", "없는 채팅방입니다.");
  return directPartner(key, memberId(me.username)) ? null : adminError(403, "CHAT_ROOM_FORBIDDEN", "들어갈 수 없는 채팅방입니다.");
}

const replyOf = (id: number | null): ChatReply | null => {
  const original = id ? messages.find((m) => m.id === id) : undefined;
  if (!original) return null;
  return {
    id: original.id, sender_username: original.sender_username, deleted: original.deleted,
    preview: original.deleted ? null : (() => {
      const line = (original.body ?? "").split("\n")[0];
      return line.length > 80 ? `${line.slice(0, 80)}…` : line;
    })(),
  };
};

/** 저장본은 답장 원문 id만 갖고, 내보낼 때마다 원문·보낸 사람의 지금 상태로 미리보기·사진 버전을 채운다. */
export const present = (message: ChatMessage): ChatMessage => ({
  ...message, reply_to: replyOf(message.reply_to?.id ?? null), attachment: message.deleted ? null : message.attachment,
  sender_avatar_version: accounts.get(message.sender_username)?.avatar?.version ?? null,
});

function summary(me: AdminMe, key: string, kind: ChatRoom["kind"], title: string, partner: number | null): ChatRoom {
  const myId = memberId(me.username);
  const lastRead = reads.get(`${myId}:${key}`) ?? 0;
  const inRoom = messages.filter((m) => m.room === key);
  const last = inRoom.at(-1);
  return {
    key, kind, title, partner_id: partner,
    partner_avatar_version: (partner && accounts.get(usernameOf(partner) ?? "")?.avatar?.version) || null,
    unread: inRoom.filter((m) => m.id > lastRead && !m.deleted && m.sender_username !== me.username).length,
    last_message: last ? present(last) : null,
  };
}

export function roomsFor(me: AdminMe): ChatRoom[] {
  const myId = memberId(me.username);
  const fixed = FIXED_ROOMS.filter((room) => room.admits(me)).map((room) => summary(me, room.key, room.kind, room.title, null));
  const directKeys = [...new Set(messages.map((m) => m.room).filter((key) => directPartner(key, myId)))];
  const directs = directKeys
    .map((key) => {
      const partner = directPartner(key, myId)!;
      return summary(me, key, "direct", usernameOf(partner) ?? "알 수 없음", partner);
    })
    .sort((a, b) => (b.last_message?.id ?? 0) - (a.last_message?.id ?? 0));
  return [...fixed, ...directs];
}

/** 1:1은 일반 회원이 전문가에게만 건다 — 실 API chat_policy와 같은 규칙. */
const canOpenDirect = (role: AdminRole, peerRole: AdminRole) => role === "viewer" && peerRole === "expert";
const canTalkDirect = (role: AdminRole, partnerRole: AdminRole) => canOpenDirect(role, partnerRole) || canOpenDirect(partnerRole, role);

export function directRoom(me: AdminMe, userId: number): ChatRoom | Response {
  const myId = memberId(me.username);
  const peer = usernameOf(userId);
  const account = peer ? accounts.get(peer) : undefined;
  if (userId === myId || !peer || !account?.user.is_active) {
    return adminError(404, "CHAT_MEMBER_NOT_FOUND", "대화 상대를 찾을 수 없습니다.");
  }
  if (!canOpenDirect(me.role, account.user.role)) {
    return adminError(403, "CHAT_ROOM_FORBIDDEN", "1:1 대화는 일반 회원이 전문가에게만 걸 수 있습니다.");
  }
  if (expertStatus(userId, myId) === "busy") {
    return adminError(409, "CHAT_EXPERT_BUSY", "이 전문가는 지금 다른 회원과 상담 중입니다.");
  }
  return summary(me, `dm:${Math.min(myId, userId)}:${Math.max(myId, userId)}`, "direct", peer, userId);
}

function expertStatus(expertId: number, myId: number): ChatExpertStatus {
  const holder = consultations.find((c) => c.expertId === expertId && c.endsAt > Date.now());
  if (!holder) return "available";
  return holder.viewerId === myId ? "mine" : "busy";
}

export function searchMembers(me: AdminMe, q: string): ChatExpert[] {
  const needle = q.trim().toLowerCase();
  const myId = memberId(me.username);
  return [...accounts.values()]
    .map((account) => account.user)
    .filter((user) => canOpenDirect(me.role, user.role) && user.is_active && user.username.toLowerCase().includes(needle))
    .sort((a, b) => a.username.localeCompare(b.username))
    .slice(0, 50)
    .map((user) => {
      const id = memberId(user.username);
      return {
        id, username: user.username, specialty: accounts.get(user.username)?.specialty ?? null,
        hourly_rate: HOURLY_RATES.get(user.username) ?? null, status: expertStatus(id, myId),
        avatar_version: accounts.get(user.username)?.avatar?.version ?? null,
      };
    });
}

/** 더미 구매(결제 없음) — 산 뒤 1:1 방. */
export function buyConsultation(me: AdminMe, expertId: number, hours: number): ChatRoom | Response {
  if (me.role !== "viewer") return adminError(403, "CHAT_ROOM_FORBIDDEN", "상담은 일반 회원만 살 수 있습니다.");
  if (!CONSULTATION_HOURS.includes(hours)) return adminError(400, "INVALID_CONSULTATION", "상담 시간은 1~3시간 중에서 골라 주세요.");
  const expert = accounts.get(usernameOf(expertId) ?? "")?.user;
  if (!expert?.is_active || expert.role !== "expert") return adminError(404, "CHAT_MEMBER_NOT_FOUND", "전문가를 찾을 수 없습니다.");
  if (!HOURLY_RATES.has(expert.username)) return adminError(400, "INVALID_CONSULTATION", "요금이 정해지지 않은 전문가입니다.");
  if (expertStatus(expertId, memberId(me.username)) !== "available") {
    return adminError(409, "CHAT_EXPERT_BUSY", "이 전문가는 지금 상담 중입니다.");
  }
  consultations.push({ viewerId: memberId(me.username), expertId, endsAt: Date.now() + hours * 3_600_000 });
  return directRoom(me, expertId);
}

function partnerDenied(me: AdminMe, room: string): Response | null {
  const partner = directPartner(room, memberId(me.username));
  const partnerUser = partner ? accounts.get(usernameOf(partner))?.user : undefined;
  if (room.startsWith("dm:") && !partnerUser?.is_active) {
    return adminError(404, "CHAT_MEMBER_NOT_FOUND", "대화 상대를 찾을 수 없습니다.");
  }
  if (partnerUser && !canTalkDirect(me.role, partnerUser.role)) {
    return adminError(403, "CHAT_ROOM_FORBIDDEN", "1:1 대화는 일반 회원과 전문가 사이에서만 할 수 있습니다.");
  }
  return null;
}

function tooFast(me: AdminMe, now: number): Response | null {
  const recent = messages.filter((m) => m.sender_username === me.username && now - Date.parse(m.created_at) < RATE_LIMIT.windowMs);
  return recent.length >= RATE_LIMIT.count
    ? adminError(429, "CHAT_TOO_FAST", "메시지를 너무 빨리 보내고 있어요. 잠시 후 다시 보내 주세요.")
    : null;
}

function append(me: AdminMe, room: string, body: string, now: number, extra: Partial<ChatMessage>): ChatMessage {
  const message: ChatMessage = {
    id: (messages.at(-1)?.id ?? 0) + 1, room, sender_id: memberId(me.username), sender_username: me.username,
    sender_role: me.role, body, deleted: false, created_at: new Date(now).toISOString(), reply_to: null, attachment: null, sender_avatar_version: null, ...extra,
  };
  messages.push(message);
  return present(message);
}

export function send(me: AdminMe, room: string, body: string, replyToId: number | null): ChatMessage | Response {
  const denied = partnerDenied(me, room);
  if (denied) return denied;
  const text = body.trim();
  if (!text || text.length > MAX_BODY_LENGTH) return adminError(400, "INVALID_CHAT_MESSAGE", "메시지는 1~500자로 입력해 주세요.");
  const now = Date.now();
  const fast = tooFast(me, now);
  if (fast) return fast;
  if (replyToId && messages.find((m) => m.id === replyToId)?.room !== room) {
    return adminError(404, "CHAT_MESSAGE_NOT_FOUND", "답장할 메시지를 찾을 수 없습니다.");
  }
  return append(me, room, text, now, {
    reply_to: replyToId ? { id: replyToId, sender_username: "", preview: null, deleted: false } : null,
  });
}

/** 1:1 대화 PDF — 실 API처럼 5MB 이하, .pdf 이름, %PDF- 로 시작. */
export function sendAttachment(me: AdminMe, room: string, name: string, content: Uint8Array): ChatMessage | Response {
  if (!room.startsWith("dm:")) return adminError(403, "CHAT_ROOM_FORBIDDEN", "PDF는 1:1 대화에서만 올릴 수 있습니다.");
  const denied = partnerDenied(me, room);
  if (denied) return denied;
  const fileName = name.replace(/\\/g, "/").split("/").at(-1)!.trim();
  const isPdf = new TextDecoder().decode(content.slice(0, 5)) === "%PDF-";
  if (!fileName.toLowerCase().endsWith(".pdf") || fileName.length > 120 || !isPdf || content.length > MAX_ATTACHMENT_BYTES) {
    return adminError(400, "INVALID_CHAT_ATTACHMENT", "5MB 이하 PDF 파일만 올릴 수 있어요.");
  }
  const now = Date.now();
  const fast = tooFast(me, now);
  if (fast) return fast;
  const message = append(me, room, fileName, now, { attachment: { name: fileName, size: content.length } });
  attachments.set(message.id, content);
  return message;
}
