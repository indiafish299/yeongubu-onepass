#!/bin/bash
# 연구부 원패스 한 줄 설치 (맥)
#   curl -fsSL https://raw.githubusercontent.com/indiafish299/yeongubu-onepass/main/install.sh | bash
# 하는 일: Claude 명령줄 도구 확인(없으면 공식 설치) → 원패스 플러그인 설치 → 파이썬·패키지 준비 → 점검.
# 시험용: ONEPASS_SOURCE 에 다른 저장소·폴더를 넣으면 거기서 설치한다.
set -e
SOURCE="${ONEPASS_SOURCE:-indiafish299/yeongubu-onepass}"
say() { echo "  $1"; }
echo; echo "연구부 원패스 설치를 시작합니다 (2~5분)"
find_claude() { for p in "$HOME/.local/bin/claude" "$(command -v claude 2>/dev/null)"; do [ -x "$p" ] && { echo "$p"; return; }; done; }
CLAUDE="$(find_claude)"
if [ -z "$CLAUDE" ]; then
  say "1/3 Claude 명령줄 도구 설치 중 (Anthropic 공식 설치 스크립트)"
  curl -fsSL https://claude.ai/install.sh | bash >/dev/null
  CLAUDE="$(find_claude)"; [ -n "$CLAUDE" ] || { echo "Claude 명령줄 도구를 설치하지 못했습니다."; exit 1; }
else say "1/3 Claude 명령줄 도구 있음"; fi
say "2/3 원패스 플러그인 설치 중"
"$CLAUDE" plugin marketplace update yeongubu >/dev/null 2>&1 || true
"$CLAUDE" plugin install onepass --marketplace "$SOURCE" --scope user >/dev/null 2>&1 || {
  "$CLAUDE" plugin list 2>/dev/null | grep -q onepass || { echo "원패스 플러그인을 설치하지 못했습니다."; exit 1; }; }
CFG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
BOOT="$(find "$CFG/plugins" -path '*onepass*' -path '*exam-setup*' -name bootstrap.sh 2>/dev/null | head -n 1)"
[ -n "$BOOT" ] || { echo "설치된 원패스에서 준비 스크립트를 찾지 못했습니다."; exit 1; }
say "3/3 파이썬과 검증 프로그램 준비 중"
bash "$BOOT" | grep -v '^@@JSON' | sed 's/^/    /'
echo; echo "다 됐습니다."
say "Claude 앱을 완전히 껐다가 다시 열고, Code 탭에서 「원패스 준비해 줘」라고 말해 주세요."
