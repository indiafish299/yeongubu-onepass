param(
  [Parameter(Mandatory)][string]$Work,       # scratch work folder (NOT the Drive folder): items.py, profile.json, template.hwp, images
  [Parameter(Mandatory)][string]$Ver,        # version tag, e.g. v3
  [string]$Py = ""                           # Python with pywin32 + pypdfium2 + pillow; empty = auto (check_env.ps1 prints the right one)
)
# items.py + profile.json -> body.html -> body.hwp -> assemble into template.hwp -> PDF + Hancom page images.
# Every path given to Hancom is a backslash path (forward slashes trigger its hidden access prompt).
$s = $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Work = (Resolve-Path $Work).Path
Set-Location $Work
if (-not $Py) {
  $Py = ((& "$s\check_env.ps1") | Select-String -Pattern '^PYTHON=(.*)$').Matches.Groups[1].Value
  if (-not $Py) { throw "Python을 찾지 못했습니다. check_env.ps1 결과를 확인하세요." }
}
if (Test-Path $Py) { $pyexe = $Py; $pyargs = $null } else { $pyexe, $pyargs = $Py.Split(" ", 2) }
function RunPy { param([string[]]$a) if ($pyargs) { & $pyexe ($pyargs.Split(" ") + $a) } else { & $pyexe $a } }
RunPy @("-u", "$s\build_body.py", "$Work\items.py", "$Work\profile.json", "$Work")
& "$s\html2hwp.ps1" -Html "$Work\body.html" -OutHwp "$Work\body.hwp" -OutPdf "$Work\body.pdf"
RunPy @("-u", "$s\assemble.py", "$Work\template.hwp", "$Work\body.hwp", "$Work\final_$Ver.hwp", "$Work\final_$Ver.pdf", "$Work\assemble_cfg.json")
# answer marks: yellow char shade (prints) -> Hancom markpen (screen only); negative-stem underline -> underline + bold
RunPy @("-u", "$s\markpen.py", "$Work\final_$Ver.hwp", "$Work\final_$Ver.hwp", "$Work\final_$Ver.pdf")
RunPy @("-u", "$s\pageimg.py", "$Work\final_$Ver.hwp", "$Work\img_$Ver", "150") | Out-Null
Set-Location "$Work\img_$Ver"
RunPy @("-c", "import glob,os; from PIL import Image; [ (Image.open(f).save(f[:-4]+'.png'), os.remove(f)) for f in glob.glob('*.bmp') ]")
Get-ChildItem -Name
