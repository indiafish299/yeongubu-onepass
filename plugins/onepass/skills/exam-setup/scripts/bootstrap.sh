#!/bin/bash
# exam-tools 처음 준비 (맥·리눅스): uv → 파이썬 가상환경(~/.exam-tools/venv) → 패키지 → rhwp(한글 파일 읽기) → 점검.
# 사람에게 묻지 않고 바로 설치한다. 몇 번 돌려도 같다(이미 있으면 건너뜀).
set -e
HOME2="${EXAM_TOOLS_HOME:-$HOME/.exam-tools}"
VENV="$HOME2/venv"
HERE="$(cd "$(dirname "$0")" && pwd)"
ENGINE="$HERE/../../exam-verify/engine"
find_uv() { for p in "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv" "$(command -v uv 2>/dev/null)"; do [ -x "$p" ] && { echo "$p"; return; }; done; }
UV="$(find_uv)"
if [ -z "$UV" ]; then
  echo "uv 설치 중 (파이썬 관리 도구, astral.sh 공식 설치 스크립트)"
  curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null
  UV="$(find_uv)"; [ -n "$UV" ] || { echo "uv 설치 실패"; exit 1; }
fi
mkdir -p "$HOME2"
[ -x "$VENV/bin/python" ] || { echo "파이썬 3.12 가상환경 만드는 중: $VENV"; "$UV" venv --quiet --python 3.12 "$VENV"; }
echo "패키지 설치 중"
"$UV" pip install --quiet --python "$VENV/bin/python" -r "$ENGINE/requirements.txt" matplotlib numpy
"$VENV/bin/python" -B "$HERE/doctor.py" rhwp || true
"$VENV/bin/python" -B "$HERE/doctor.py" check
echo "PYTHON=$VENV/bin/python"
