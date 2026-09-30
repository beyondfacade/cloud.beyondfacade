import type { IpBlock } from "@/shared/api/types";
import { initialIpBlocks } from "../../../admin-fixtures";

/** mock 차단 목록 — 개발 서버 프로세스 동안만 유지된다. */
export const ipBlocks = new Map<string, IpBlock>(initialIpBlocks.map((block) => [block.ip, block]));
