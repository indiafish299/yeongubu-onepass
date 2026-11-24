param([string]$Html, [string]$OutHwp, [string]$OutPdf)
# Opens an HTML file in Hancom and saves it as HWP and PDF (all paths must be outside synced folders).
$hwp = New-Object -ComObject HWPFrame.HwpObject
try { $hwp.XHwpWindows.Item(0).Visible = $false } catch {}
$ok = $hwp.Open($Html, "HTML", "code:utf8")
"open=$ok"
$a = $hwp.SaveAs($OutHwp, "HWP", "")
$b = $hwp.SaveAs($OutPdf, "PDF", "")
"hwp=$a pdf=$b"
$hwp.Clear(1); $hwp.Quit()
