# 연구부 원패스

시험지 원안을 만들고, 여러 AI가 정답을 모른 채 직접 풀어 보며 검증하는 일까지 한 번에 해 주는 Claude Code 플러그인입니다.
컴퓨터와 인공지능이 서툰 선생님도 Claude에게 말로 부탁만 하면 됩니다.

- 안내 페이지(설치·사용법·그림): `docs/onepass-guide.html` — 공유용 링크는 연구부에 문의
- 소개 영상 대본(클로드 모션): `docs/claude-motion-대본.md`

## 설치 (선생님) — 한 줄

1. Claude 앱(claude.ai/download)을 설치하고 유료 요금제로 로그인, **Code** 탭을 엽니다.
2. 아래 한 줄을 Claude에게 붙여 넣습니다. 나머지는 Claude가 설치합니다(「실행해도 될까요?」에는 허용).

        연구부 원패스 설치해 줘. 윈도우는 irm https://raw.githubusercontent.com/indiafish299/yeongubu-onepass/main/install.ps1 | iex , 맥은 curl -fsSL https://raw.githubusercontent.com/indiafish299/yeongubu-onepass/main/install.sh | bash 를 실행하면 돼.

3. 앱을 껐다 켜고 「원패스 준비해 줘」라고 말합니다(AI 로그인·검토자 고르기).

설치 스크립트(`install.ps1`, `install.sh`)가 하는 일: Claude 명령줄 도구 확인(없으면 공식 설치) → `claude plugin install onepass --marketplace indiafish299/yeongubu-onepass` → 파이썬·패키지 준비(`exam-setup/scripts/bootstrap`). 다시 실행하면 최신판으로 올린다.

| 스킬 | 하는 일 |
|---|---|
| `exam-setup` 처음 준비 | 파이썬·검증 코드·AI 명령줄 도구 자동 설치·업데이트, 로그인 안내, 요금제에서 되는 검토자 모델 고르기 |
| `exam-paper` 원안 제작 | 출제 설계 → 문항 → 학교 원안 양식(한글) 조립. 정답 형광펜, '않은' 밑줄+굵게, 선지 줄 간격 5.6mm → 정답·배점표, 이원목적분류표, 문항정보표 |
| `exam-verify` 시험지 검증 | 여러 AI가 정답 없이 따로 풀기·흠잡기·범위·오탈자·반박 → 정답표 대조 → 「한눈에」 요약 보고서 |

## 요금제별 검토자

| 가진 요금제 | 검토자 |
|---|---|
| Claude 만 | Claude 모델 둘(반박은 같은 회사 다른 모델) |
| Claude + ChatGPT 또는 Gemini | 셋 |
| 셋 다 | 넷 |

## 지켜지는 원칙

- 시험지·정답·보고서는 선생님 PC(`~/.exam-tools/work/`)에만 둡니다. 이 저장소에는 시험 내용을 넣지 않습니다(`.gitignore`).
- AI에게 보내기 전에 학교명·출제자·결재란을 자동으로 가리고, 가린 그림을 보여 드린 뒤 확인받습니다.
- AI는 정답을 끝까지 보지 못합니다. 정답 대조는 스크립트가 합니다.
- 비밀번호를 대신 입력하지 않습니다. 보고서는 통과 도장이 아니고, 최종 판단은 선생님이 합니다.

## 개발

- 검증 코드: `plugins/onepass/skills/exam-verify/engine/` (`exam_verify/cli.py`)
- 가짜 시험지로 처음부터 끝까지: 윈도우 `engine/tests/run_fake.ps1`, 맥 `engine/tests/run_fake.sh`
- 새 PC 처럼 시험: `EXAM_TOOLS_HOME=<임시 폴더>`
