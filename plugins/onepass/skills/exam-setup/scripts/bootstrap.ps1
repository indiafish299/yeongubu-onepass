# exam-tools 처음 준비 (윈도우): uv → 파이썬 가상환경(~/.exam-tools/venv) → 패키지 → rhwp(한글 파일 읽기) → 점검.
# 사람에게 묻지 않고 바로 설치한다. 몇 번 돌려도 같다(이미 있으면 건너뜀).
# usage: powershell -ExecutionPolicy Bypass -File bootstrap.ps1
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
$Home2 = if ($env:EXAM_TOOLS_HOME) { $env:EXAM_TOOLS_HOME } else { Join-Path $HOME ".exam-tools" }
$Venv = Join-Path $Home2 "venv"
$Engine = Join-Path (Split-Path (Split-Path $PSScriptRoot)) "exam-verify\engine"

function Find-Uv {
  foreach ($p in @("$HOME\.local\bin\uv.exe", "$HOME\.cargo\bin\uv.exe")) { if (Test-Path $p) { return $p } }
  $c = Get-Command uv -ErrorAction SilentlyContinue
  if ($c) { return $c.Source }
  return $null
}

$uv = Find-Uv
if (-not $uv) {
  Write-Output "uv 설치 중 (파이썬 관리 도구, astral.sh 공식 설치 스크립트)"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex" | Out-Null
  $uv = Find-Uv
  if (-not $uv) { throw "uv 설치 실패" }
}
New-Item -ItemType Directory -Force $Home2 | Out-Null
if (-not (Test-Path "$Venv\Scripts\python.exe")) {
  Write-Output "파이썬 3.12 가상환경 만드는 중: $Venv"
  & $uv venv --quiet --python 3.12 $Venv
}
Write-Output "패키지 설치 중"
& $uv pip install --quiet --python "$Venv\Scripts\python.exe" -r "$Engine\requirements.txt" pywin32 matplotlib numpy
& "$Venv\Scripts\python.exe" -B (Join-Path $PSScriptRoot "doctor.py") rhwp
& "$Venv\Scripts\python.exe" -B (Join-Path $PSScriptRoot "doctor.py") check
Write-Output "PYTHON=$Venv\Scripts\python.exe"
