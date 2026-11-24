# 원안 제작 환경 점검: 무엇이 되고 무엇이 안 되는지 표로 보여 준다 (아무것도 설치하거나 바꾸지 않음).
# usage: powershell -ExecutionPolicy Bypass -File check_env.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$rows = @()
function Add($item, $ok, $note) { $script:rows += [pscustomobject]@{ 항목 = $item; 상태 = $(if ($ok) { "OK" } else { "없음" }); 비고 = $note } }

# OS
Add "Windows" ($env:OS -eq "Windows_NT") "한글 자동화(COM)는 Windows 전용"

# Hancom Office (HWP COM)
$hwpOk = $false
try { $h = New-Object -ComObject HWPFrame.HwpObject; $h.Quit(); $hwpOk = $true } catch {}
Add "한글(HWP) 자동화" $hwpOk "없으면 HTML/PDF 초안까지만 만들고 한글 PC에서 조립"

# Python launcher
$py = $null
# exam-setup 이 만든 가상환경(pywin32·pypdfium2·pillow·matplotlib 포함)을 먼저 쓴다
$ev = Join-Path $(if ($env:EXAM_TOOLS_HOME) { $env:EXAM_TOOLS_HOME } else { Join-Path $HOME ".exam-tools" }) "venv\Scripts\python.exe"
$cands = @("py -3", "python", "python3"); if (Test-Path $ev) { $cands = @($ev) + $cands }
foreach ($c in $cands) {
  if (Test-Path $c) { $exe = $c; $arg = $null } else { $exe, $arg = $c.Split(" ", 2) }
  if (Get-Command $exe -ErrorAction SilentlyContinue) {
    $v = if ($arg) { & $exe $arg --version 2>&1 } else { & $exe --version 2>&1 }
    if ("$v" -match "Python 3\.(\d+)" -and [int]$Matches[1] -ge 9) { $py = $c; break }
  }
}
$uv = [bool](Get-Command uv -ErrorAction SilentlyContinue)
Add "Python 3.9+" ([bool]$py) $(if ($py) { "실행 명령: $py" } elseif ($uv) { "uv로 대체 가능" } else { "Python 설치 필요" })
if ($py) {
  if (Test-Path $py) { $exe = $py; $arg = $null } else { $exe, $arg = $py.Split(" ", 2) }
  foreach ($m in @("win32com", "pypdfium2", "PIL", "matplotlib", "numpy")) {
    $code = "import $m"
    $r = if ($arg) { & $exe $arg -c $code 2>&1 } else { & $exe -c $code 2>&1 }
    Add "  python 모듈 $m" ($LASTEXITCODE -eq 0) $(if ($LASTEXITCODE -ne 0) { "pip install " + @{win32com="pywin32"; PIL="pillow"}[$m] + $(if (@("win32com","PIL") -notcontains $m) { $m }) } else { "" })
  }
}
Add "uv" $uv "Python 모듈이 없을 때 uv run --with ... 로 대체"

# Optional tools
Add "agy (Antigravity CLI, Gemini 검토)" ([bool](Get-Command agy -ErrorAction SilentlyContinue)) "없으면 다른 검토자만 사용"
Add "ego-browser" ([bool](Get-Command ego-browser -ErrorAction SilentlyContinue)) "교과서 사이트 자료 받기 — 없으면 Claude in Chrome/내장 브라우저, 또는 선생님이 직접 내려받기"


$rows | Format-Table -AutoSize | Out-String -Width 200
if ($py) { "PYTHON=$py" } elseif ($uv) { "PYTHON=uv run --quiet --with pywin32 --with pypdfium2 --with pillow --with matplotlib python" }
