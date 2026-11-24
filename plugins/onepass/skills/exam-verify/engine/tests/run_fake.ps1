# 가짜 시험지로 처음부터 끝까지(윈도우): PDF 만들기 → prepare(가릴 칸 자동) → approve → 정답표(md) → plan → run --fast
# usage: powershell -ExecutionPolicy Bypass -File run_fake.ps1 [-Name fake-probe] [-Models sol,neon]
param([string]$Name = "fake-probe", [string]$Models = "")
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Home2 = if ($env:EXAM_TOOLS_HOME) { $env:EXAM_TOOLS_HOME } else { Join-Path $HOME ".exam-tools" }
$Py = Join-Path $Home2 "venv\Scripts\python.exe"
$Eng = Split-Path $PSScriptRoot
$Cli = Join-Path $Eng "exam_verify\cli.py"
$Pdf = Join-Path $env:TEMP "exam_fake_page.pdf"
& $Py -B (Join-Path $PSScriptRoot "make_fake_page.py") $Pdf | Out-Null
& $Py -B $Cli prepare $Name $Pdf
& $Py -B $Cli approve $Name
& $Py -B $Cli answers $Name (Join-Path $PSScriptRoot "fake_answers.md")
& $Py -B $Cli answers $Name --confirm
$m = @(); if ($Models) { $m = @("--models", $Models) }
& $Py -B $Cli plan $Name @m
& $Py -B $Cli run $Name --fast --quiet @m
"RUN_FAKE_DONE rc=$LASTEXITCODE"
