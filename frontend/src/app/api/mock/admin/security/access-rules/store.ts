import type { AccessRule } from "@/shared/api/types";
import { initialAccessRules } from "../../../admin-fixtures";

/** mock 화이트·블랙리스트 — 개발 서버 프로세스 동안만 유지된다. */
export const accessRules: AccessRule[] = initialAccessRules.map((rule) => ({ ...rule }));
