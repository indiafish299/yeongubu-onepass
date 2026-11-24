# -*- coding: utf-8 -*-
"""Diagnose an assembled exam: paragraph break unit per list, control anchors in main para 0..2,
and ParaShape items available (Condense etc.). Writes a UTF-8 report."""
import sys, collections
import win32com.client as win32

src, rep = sys.argv[1], sys.argv[2]
out = open(rep, "w", encoding="utf-8")
hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
try:
    hwp.XHwpWindows.Item(0).Visible = False
except Exception:
    pass
hwp.Open(src, "HWP", "forceopen:true")

c = hwp.HeadCtrl; k = 0
while c is not None:
    if c.CtrlID == "tbl":
        k += 1
        a = c.GetAnchorPos(0)
        if k <= 4:
            out.write(f"table {k} anchor list {a.Item('List')} para {a.Item('Para')} pos {a.Item('Pos')} treat {c.Properties.Item('TreatAsChar')}\n")
    c = c.Next

ps = hwp.HParameterSet.HParaShape


def info():
    hwp.HAction.GetDefault("ParagraphShape", ps.HSet)
    return ps.BreakNonLatinWord, ps.Condense, ps.LeftMargin, ps.Indentation, ps.AlignType


stat = collections.Counter()
for l in range(0, 400):
    hwp.SetPos(l, 0, 0)
    if hwp.GetPos()[0] != l:
        continue
    p = 0
    while True:
        hwp.SetPos(l, p, 0)
        if tuple(hwp.GetPos()[:2]) != (l, p):
            break
        b = info()
        stat[(l == 0, b[0])] += 1
        if b[0] == 1 or (l == 0 and p < 4) or l in (34, 35, 36):
            hwp.Run("MoveSelParaEnd")
            t = (hwp.GetTextFile("TEXT", "saveblock") or "").strip().replace("\r\n", " / ")[:40]
            hwp.Run("Cancel")
            out.write(f"list {l} para {p} break {b[0]} condense {b[1]} left {b[2]} indent {b[3]} align {b[4]} | {t}\n")
        p += 1
out.write(f"stat (main?, break): {dict(stat)}\n")
hwp.Clear(1); hwp.Quit(); out.close()
