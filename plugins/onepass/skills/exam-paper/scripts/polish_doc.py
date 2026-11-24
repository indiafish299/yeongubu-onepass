# -*- coding: utf-8 -*-
"""Tidy a generated HWP document (이원목적분류표 등 표 문서):
어절 줄 나눔·최소 공백 everywhere (main text and every cell), tables start at the left margin,
long tables split only between rows and repeat their header row, page margins 15 mm.
usage: polish_doc.py SRC OUT_HWP OUT_PDF   (backslash paths, copies outside the synced Drive folder)"""
import os, shutil, sys
import win32com.client as win32

sys.stdout.reconfigure(encoding="utf-8")
src, out_hwp, out_pdf = [os.path.normpath(a) for a in sys.argv[1:4]]
shutil.copyfile(src, out_hwp)
hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
try:
    hwp.XHwpWindows.Item(0).Visible = False
except Exception:
    pass
hwp.Open(out_hwp, "HWP", "forceopen:true")


def set_para(**kw):
    ps = hwp.HParameterSet.HParaShape
    hwp.HAction.GetDefault("ParagraphShape", ps.HSet)
    for k, v in kw.items():
        setattr(ps, k, v)
    hwp.HAction.Execute("ParagraphShape", ps.HSet)


n = 0
for l in range(0, 1500):
    hwp.SetPos(l, 0, 0)
    if hwp.GetPos()[0] != l:
        continue
    hwp.Run("MoveListBegin"); hwp.Run("MoveSelListEnd"); set_para(BreakNonLatinWord=0, Condense=50); hwp.Run("Cancel")
    n += 1
print("lists", n)
k, c = 0, hwp.HeadCtrl
while c is not None:
    if c.CtrlID == "tbl":
        k += 1
        p = c.Properties
        p.SetItem("PageBreak", 1)          # split only between rows (셀 단위로 나눔)
        p.SetItem("RepeatHeader", 1)
        p.SetItem("HorzRelTo", 3); p.SetItem("HorzAlign", 0); p.SetItem("HorzOffset", 0)   # start at the left margin
        c.Properties = p
        a = c.GetAnchorPos(0)
        hwp.SetPos(a.Item("List"), a.Item("Para"), 0); set_para(LeftMargin=0, Indentation=0)
    c = c.Next
print("tables", k)
sd = hwp.HParameterSet.HSecDef
hwp.HAction.GetDefault("PageSetup", sd.HSet)
for key in ("LeftMargin", "RightMargin", "TopMargin", "BottomMargin"):
    setattr(sd.PageDef, key, hwp.MiliToHwpUnit(15))
sd.HSet.SetItem("ApplyTo", 3)
hwp.HAction.Execute("PageSetup", sd.HSet)
hwp.SaveAs(out_hwp, "HWP", ""); hwp.SaveAs(out_pdf, "PDF", "")
print("pages", hwp.PageCount)
hwp.Clear(1); hwp.Quit()
