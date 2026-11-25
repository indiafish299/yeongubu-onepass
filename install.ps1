# 연구부 원패스 한 줄 설치 (윈도우)
#   irm https://raw.githubusercontent.com/indiafish299/yeongubu-onepass/main/install.ps1 | iex
# 하는 일: Claude 명령줄 도구 확인(없으면 공식 설치) → 원패스 플러그인 설치 → 파이썬·패키지 준비 → 점검.
# 묻지 않고 진행한다. 몇 번 돌려도 같다(이미 있으면 건너뛰거나 최신으로 올린다).
# 시험용: $env:ONEPASS_SOURCE 에 다른 저장소·폴더를 넣으면 거기서 설치한다.
# 이 파일은 BOM 없는 UTF-8 이다(irm | iex 로 받을 때 BOM 이 첫 줄을 깨뜨린다). 로컬 시험은 Get-Content -Raw -Encoding UTF8 install.ps1 | iex
# PowerShell 5.1 은 Stop 이면 프로그램이 stderr 에 쓰기만 해도 멈춘다 → Continue 로 두고 결과를 직접 확인한다
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Source = if ($env:ONEPASS_SOURCE) { $env:ONEPASS_SOURCE } else { "indiafish299/yeongubu-onepass" }
function Say($t) { Write-Host "  $t" }
Write-Host ""
Write-Host "연구부 원패스 설치를 시작합니다 (2~5분)" -ForegroundColor Yellow

# 1) Claude 명령줄 도구
function Find-Claude {
  foreach ($p in @("$HOME\.local\bin\claude.exe")) { if (Test-Path $p) { return $p } }
  $c = Get-Command claude -ErrorAction SilentlyContinue
  if ($c) { return $c.Source }
  return $null
}
$claude = Find-Claude
if (-not $claude) {
  Say "1/3 Claude 명령줄 도구 설치 중 (Anthropic 공식 설치 스크립트)"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://claude.ai/install.ps1 | iex" | Out-Null
  $claude = Find-Claude
  if (-not $claude) { throw "Claude 명령줄 도구를 설치하지 못했습니다. 인터넷 연결을 확인하고 다시 실행해 주세요." }
} else { Say "1/3 Claude 명령줄 도구 있음" }

# 2) 원패스 플러그인 (마켓플레이스 등록 + 설치를 한 번에, 이미 있으면 최신으로)
Say "2/3 원패스 플러그인 설치 중"
$known = (& $claude plugin marketplace list 2>&1 | Out-String) -match "yeongubu"
if ($known) { & $claude plugin marketplace update yeongubu 2>&1 | Out-Null }
$out = & $claude plugin install onepass --marketplace $Source --scope user 2>&1 | Out-String
$ok = $LASTEXITCODE -eq 0
if (-not $ok) { $ok = (& $claude plugin list 2>&1 | Out-String) -match "onepass" }
if (-not $ok) { Write-Host $out; throw "원패스 플러그인을 설치하지 못했습니다." }
if ($known) { & $claude plugin update onepass@yeongubu 2>&1 | Out-Null }

# 3) 파이썬·패키지 (설치된 플러그인의 exam-setup 부트스트랩)
$cfg = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $HOME ".claude" }
$boot = Get-ChildItem -Path (Join-Path $cfg "plugins") -Recurse -Filter bootstrap.ps1 -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -match "onepass" -and $_.FullName -match "exam-setup" } |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $boot) { throw "설치된 원패스에서 준비 스크립트를 찾지 못했습니다." }
Say "3/3 파이썬과 검증 프로그램 준비 중"
powershell -NoProfile -ExecutionPolicy Bypass -File $boot.FullName | ForEach-Object { "    $_" } | Where-Object { $_ -notmatch "@@JSON" }

Write-Host ""
$skill = Split-Path (Split-Path $boot.FullName)
$eth = if ($env:EXAM_TOOLS_HOME) { $env:EXAM_TOOLS_HOME } else { Join-Path $HOME ".exam-tools" }
Write-Host "다 됐습니다. 앱을 끄거나 다시 켤 필요는 없습니다." -ForegroundColor Green
Say "Claude에게서 설치했다면: 이 대화에서 Claude가 바로 이어서 AI 로그인과 검토자 고르기를 안내합니다."
Say "PowerShell에서 직접 설치했다면: Claude 앱 Code 탭에서 새 세션을 열고 「원패스 준비해 줘」라고 말해 주세요."
Say "다음부터는 Code 탭에서 새 세션을 열면 원패스가 들어 있습니다."
Write-Host ""
Write-Host "[Claude에게] 이 대화에서 바로 이어서 준비를 진행하세요. $skill\SKILL.md 를 읽고 「순서」 2번부터 따르세요(1번 기본 준비는 끝났습니다. <SKILL_DIR>=$skill, <PYTHON>=$(Join-Path $eth 'venv\Scripts\python.exe')). 선생님께 앱을 끄거나 다시 켜라고 하지 마세요."
