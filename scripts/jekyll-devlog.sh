#!/bin/bash
# 매일 23:55 실행 — cloud.beyondfacade 당일 개발 이력을 docs/jekyll.md에 기록하고
# metabole.beyondfacade.cloud(블로그)로 복사.
# 등록: crontab "55 23 * * * /home/kimchungsik/projects/cloud.beyondfacade/scripts/jekyll-devlog.sh"
# git 커밋/푸시는 사용자가 직접 수행. (23:59 lifetutorial용 크론과 시간 분리)

set -u
PROJECT=/home/kimchungsik/projects/cloud.beyondfacade
BLOG=/home/kimchungsik/projects/metabole.beyondfacade.cloud
LOG=/home/kimchungsik/.claude/jekyll-devlog-beyondfacade-cron.log
export PATH="/home/kimchungsik/.local/bin:$PATH"

TODAY=$(date +%Y-%m-%d)

cd "$PROJECT" || exit 1

{
  echo "=== jekyll-devlog-beyondfacade run $TODAY $(date +%H:%M:%S) ==="

  claude -p --permission-mode acceptEdits --allowedTools "Bash(git log:*)" <<EOF
오늘($TODAY) 하루 동안 개발된 내용을 개발 일지에 기록해줘.

1. 근거 수집: backend/docs/backend_ver_log.md 와 frontend/docs/frontend_ver_log.md 에서 오늘 날짜($TODAY) 항목을 확인하고, docs/ 아래 오늘 수정된 문서(api.md 등)가 있으면 함께 반영해.
2. docs/jekyll.md 에 "## $TODAY" 일자별 섹션을 추가하거나 이미 있으면 갱신해. 기존 형식(일자별 ## 섹션, 그 아래 ### 소제목, 한국어, 버전 번호와 핵심 수치 포함)을 그대로 따라. front matter의 date: 도 $TODAY 로 갱신해.
3. 오늘 개발된 내용이 전혀 없으면 파일을 수정하지 말고 "변경 없음"이라고만 답해.
4. git commit/push는 절대 하지 마. docs/jekyll.md 외의 파일도 수정하지 마.
EOF

  cp "$PROJECT/docs/jekyll.md" "$BLOG/jekyll.md" && echo "copied to $BLOG/jekyll.md"

  echo "=== done $(date +%H:%M:%S) ==="
} >> "$LOG" 2>&1
