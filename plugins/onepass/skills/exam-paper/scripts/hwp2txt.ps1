param([string]$SrcDir, [string]$OutDir, [string]$Pattern = '*.hwp', [string]$Exclude = '^$', [switch]$Pdf)
# Converts HWP files to UTF-8 text (and optionally PDF) using Hancom COM. Works on copies.
New-Item -ItemType Directory -Force $OutDir | Out-Null
$hwp = New-Object -ComObject HWPFrame.HwpObject
try { $hwp.XHwpWindows.Item(0).Visible = $false } catch {}
Get-ChildItem $SrcDir -Filter $Pattern | Where-Object { $_.Name -notmatch $Exclude } | ForEach-Object {
  $base = [IO.Path]::GetFileNameWithoutExtension($_.Name)
  $tmp = Join-Path $OutDir ("_tmp_" + [guid]::NewGuid().ToString('N') + ".hwp")
  Copy-Item -LiteralPath $_.FullName -Destination $tmp -Force
  $ok = $hwp.Open($tmp, "HWP", "forceopen:true")
  $txt = Join-Path $OutDir "$base.cp949.txt"
  $null = $hwp.SaveAs($txt, "TEXT", "")
  if ($Pdf) { $null = $hwp.SaveAs((Join-Path $OutDir "$base.pdf"), "PDF", "") }
  $hwp.Clear(1)
  $t = [IO.File]::ReadAllText($txt, [Text.Encoding]::GetEncoding(949))
  [IO.File]::WriteAllText((Join-Path $OutDir "$base.txt"), $t, [Text.Encoding]::UTF8)
  Remove-Item -LiteralPath $txt, $tmp -Force
  "converted $base ($($t.Length) chars)"
}
$hwp.Quit()
