# -*- coding: utf-8 -*-
"""Report font, size, letter spacing, line spacing and alignment of the first body paragraphs of an HWP file."""
import sys
import win32com.client as win32

src, rep, start, n = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
out = open(rep, "w", encoding="utf-8")
hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
try:
    hwp.XHwpWindows.Item(0).Visible = False
except Exception:
    pass
hwp.Open(src, "HWP", "forceopen:true")
ps, cs = hwp.HParameterSet.HParaShape, hwp.HParameterSet.HCharShape
for p in range(start, start + n):
    hwp.SetPos(0, p, 0)
    if hwp.GetPos()[1] != p:
        break
    hwp.HAction.GetDefault("ParagraphShape", ps.HSet)
    hwp.Run("MoveRight")
    hwp.HAction.GetDefault("CharShape", cs.HSet)
    hwp.SetPos(0, p, 0); hwp.Run("MoveSelParaEnd")
    t = (hwp.GetTextFile("TEXT", "saveblock") or "").strip()[:30]
    hwp.Run("Cancel")
    out.write(f"para {p}: line {ps.LineSpacingType}/{ps.LineSpacing} align {ps.AlignType} break {ps.BreakNonLatinWord} "
              f"condense {ps.Condense} prev {ps.PrevSpacing} next {ps.NextSpacing} | font {cs.FaceNameHangul} "
              f"{cs.Height/100}pt spacing {cs.SpacingHangul} ratio {cs.RatioHangul} | {t}\n")
hwp.Clear(1); hwp.Quit(); out.close()
