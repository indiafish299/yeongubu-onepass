#!/bin/bash
# 채점 기준 단계 시험: 서답형 가짜 시험지 + 흠을 심은 채점 기준표(make_fake_essay.py). 터미널 탭에서 돌린다.
HOME2="${EXAM_TOOLS_HOME:-$HOME/.exam-tools}"; PY="$HOME2/venv/bin/python"
HERE="$(cd "$(dirname "$0")" && pwd)"; CLI="$HERE/../exam_verify/cli.py"
W="$("$PY" -c "import sys; sys.path.insert(0,'$HERE/..'); from exam_verify import home; print(home.WORK)")/fake-essay"
mkdir -p "$W"
"$PY" -B "$HERE/make_fake_essay.py" "$W/fake.pdf" "$W/rubric.md" "$W/answers.json" >/dev/null
"$PY" -B "$CLI" prepare fake-essay "$W/fake.pdf" && "$PY" -B "$CLI" approve fake-essay
"$PY" -B "$CLI" run fake-essay --answers "$W/answers.json" --rubric "$W/rubric.md" --scope "고등학교 1학년 통합과학" --quiet "$@"
echo "RUN_FAKE_ESSAY_DONE rc=$?"