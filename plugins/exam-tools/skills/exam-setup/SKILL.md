---
name: exam-setup
description: 시험지 제작·검증 도구(exam-tools)를 선생님 PC에 준비한다 — 파이썬·검증 코드·AI 명령줄 도구(claude·codex·agy)를 알아서 설치·업데이트하고, 로그인을 돕고, 선생님 요금제에서 실제로 되는 검토자 모델을 골라 저장한다. "시험지 검증 준비", "exam-tools 설치", "검증 도구 설정", "처음 설정", "로그인이 안 돼"가 나오거나, exam-verify·exam-paper를 쓰려는데 ~/.exam-tools/profile.json 이 없으면 먼저 쓴다.
---

# 처음 준비 (exam-setup)

대상은 컴퓨터를 잘 모르는 선생님이다. **설치는 묻지 않고 바로 하고**, 끝나면 무엇을 깔았는지 한 줄로 알린다.
묻는 것은 꼭 필요한 것만(아래 ❓ 하나). 쉬운 말로, 명령어 이름은 되도록 말하지 않는다.

집 폴더: `~/.exam-tools/` (`venv/` 파이썬, `profile.json` 검토자 구성, `work/` 시험지별 결과 — 이 PC에만 둔다)
이 스킬 폴더: `<SKILL_DIR>` (이 파일이 있는 곳). 아래 경로는 모두 그 기준.

## 순서

1. **기본 준비 (자동):**
   - 윈도우: `powershell -NoProfile -ExecutionPolicy Bypass -File "<SKILL_DIR>\scripts\bootstrap.ps1"`
   - 맥: `bash "<SKILL_DIR>/scripts/bootstrap.sh"`
   uv(파이썬 관리 도구) → 파이썬 3.12 가상환경 → 패키지 → 점검표. 마지막 줄 `PYTHON=…`이 앞으로 쓸 파이썬이다.
   점검표의 `@@JSON` 줄에 claude·codex·agy 설치·로그인 상태가 있다.

2. **어떤 AI 를 쓰는지 (❓ 필요할 때만 한 번):** Claude 는 지금 쓰고 있으니 늘 있다. codex(ChatGPT)·agy(Gemini)가 이미 로그인돼 있으면 묻지 않는다.
   둘 다 로그인돼 있지 않을 때만 AskUserQuestion(여러 개 선택): 「Claude 말고 쓰시는 AI 요금제가 있나요?」 — ChatGPT / Gemini / 없음.
   다른 회사 AI 가 있으면 검증이 더 믿을 만하다는 것을 한 줄로 덧붙인다.

3. **도구 설치·업데이트 (자동):** `<PYTHON> -B <SKILL_DIR>/scripts/doctor.py install anthropic[,openai][,google]`
   - claude 명령이 없으면 공식 설치 스크립트로 깐다. codex 는 늘 최신판으로 올린다(옛 판은 최신 모델을 거부한다). node 가 없으면 윈도우는 winget, 맥은 brew 로 깐다.
   - agy(Gemini)는 자동 설치하지 않는다. 없으면 「Google Antigravity 를 설치하면 들어온다」고 알리고 Gemini 없이 진행한다.

4. **로그인 (선생님이 직접):** 로그인이 필요한 도구마다 터미널 탭(`mcp__terminal__run_in_terminal`, 없으면 선생님께 명령 한 줄을 드림)에서
   `claude auth login` / `codex login` 을 실행한다. 브라우저가 열리면 선생님이 로그인하고 「됐어」라고 하신다.
   비밀번호는 절대 대신 넣지 않는다. agy 는 `agy`를 한 번 실행해 첫 화면에서 Google 계정으로 로그인한다.

5. **검토자 고르기 (자동):** `<PYTHON> -B <SKILL_DIR>/scripts/doctor.py probe`
   로그인된 회사마다 후보 모델을 「확인」 한 마디로 불러 보고(시험 내용 없음) 되는 것만 `profile.json` 에 적는다.
   요금제가 낮아 최상위 모델이 안 되면 다음 모델로 내려간다. 결과를 한 줄로: 「검토자 3명: 페이블 5.2, 오푸스 5.5, 솔 6.2」.
   한 회사뿐이면 「반박은 같은 회사의 다른 모델이 맡는다」고 알린다.

6. **가릴 이름 (선택):** 학교명·선생님 이름을 알면 `doctor.py names "○○고등학교" "홍길동"`. 몰라도 된다 — 가릴 칸 자동 찾기는 「…학교」, 출제자·결재란·저작권 줄을 스스로 찾는다.

끝나면 「준비됐습니다. 이제 시험지를 주시면 검증합니다」와 함께 설치한 것·검토자를 두세 줄로 알린다.

## 다시 쓸 때

- 검증 전에 `doctor.py check` 로 로그인이 풀렸는지만 본다(로그인 만료가 가장 흔한 실패). 풀렸으면 4번만 다시.
- 요금제를 바꿨거나 모델이 안 된다는 오류가 나면 `doctor.py probe` 를 다시.

## 알아 둘 것 (실제로 겪은 것)

- 윈도우의 codex 는 `codex.cmd` 를 거치면 여러 줄 프롬프트가 첫 줄에서 잘린다 → 검증 코드가 node 로 직접 부른다(고쳐 둠).
- 옛 codex(0.149)는 `gpt-6.2-sol` 을 「ChatGPT 계정에서 지원 안 함」으로 거부했다 → install 이 최신판으로 올린다.
- 맥에서는 Claude 앱의 셸에서 `claude` 가 로그인 안 됨으로 보일 수 있다 → 검증 `run` 은 터미널 탭에서 돌린다.
- PowerShell 5.1 은 BOM 없는 한글 .ps1 을 깨뜨린다(이 폴더의 .ps1 은 BOM 붙은 UTF-8).
