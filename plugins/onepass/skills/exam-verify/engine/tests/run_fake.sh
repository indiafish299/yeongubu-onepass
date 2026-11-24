#!/bin/bash
# 가짜 시험지로 처음부터 끝까지(맥): PDF 만들기 → prepare(가릴 칸 자동) → approve → 정답표(md) → plan → run --fast
# 터미널 탭에서 돌린다(앱 셸에서는 claude 가 로그인 안 됨으로 보일 수 있다). usage: bash run_fake.sh [이름] [--models a,b]
HOME2="${EXAM_TOOLS_HOME:-$HOME/.exam-tools}"; PY="$HOME2/venv/bin/python"
HERE="$(cd "$(dirname "$0")" && pwd)"; CLI="$HERE/../exam_verify/cli.py"
NAME="${1:-fake-probe}"; shift
PDF="${TMPDIR:-/tmp}/exam_fake_page.pdf"
"$PY" -B "$HERE/make_fake_page.py" "$PDF" >/dev/null
"$PY" -B "$CLI" prepare "$NAME" "$PDF"
"$PY" -B "$CLI" approve "$NAME"
"$PY" -B "$CLI" answers "$NAME" "$HERE/fake_answers.md"
"$PY" -B "$CLI" answers "$NAME" --confirm
"$PY" -B "$CLI" plan "$NAME" "$@"
"$PY" -B "$CLI" run "$NAME" --fast --quiet "$@"
echo "RUN_FAKE_DONE rc=$?"