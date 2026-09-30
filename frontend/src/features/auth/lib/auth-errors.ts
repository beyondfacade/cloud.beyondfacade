/** 구글 왕복이 실패하면 백엔드가 /login?error=CODE로 돌려보낸다 — 코드별 안내 문구. */
const REDIRECT_ERRORS: Record<string, string> = {
  GOOGLE_NOT_CONFIGURED: "구글 로그인이 아직 준비되지 않았습니다.",
  OAUTH_STATE_MISMATCH: "로그인 요청이 만료되었습니다. 다시 시도해 주세요.",
  GOOGLE_LOGIN_FAILED: "구글 로그인을 마치지 못했습니다. 다시 시도해 주세요.",
  GOOGLE_EMAIL_UNVERIFIED: "구글에서 확인된 이메일이 아닙니다.",
  EMAIL_TAKEN: "이 이메일로 가입된 계정이 있습니다. 아이디와 비밀번호로 로그인하세요.",
  INVALID_CREDENTIALS: "이용이 정지된 계정입니다.",
};
const FALLBACK = "로그인하지 못했습니다. 다시 시도해 주세요.";

export function redirectErrorMessage(code: string | null): string | null {
  if (!code) return null;
  return REDIRECT_ERRORS[code] ?? FALLBACK;
}
