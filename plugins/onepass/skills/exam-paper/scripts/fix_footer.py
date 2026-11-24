# -*- coding: utf-8 -*-
"""Replace the total page count in the footer (e.g. "○○학교 (과목) 2학년 (4) - n") of an assembled 원안.
AllReplace does not reach this footer, so walk every list (header/footer lists included) paragraph by paragraph.
usage: <python> fix_footer.py HWP PDF OLD NEW   (e.g. "(4)" "(5)"; paths with backslashes)"""
import os, sys
import win32com.client as win32
sys.stdout.reconfigure(encoding="utf-8")
src, pdf, old, new = os.path.normpath(sys.argv[1]), os.path.normpath(sys.argv[2]), sys.argv[3], sys.argv[4]
hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
try:
    hwp.XHwpWindows.Item(0).Visible = False
except Exception:
    pass
hwp.Open(src, "HWP", "forceopen:true")


def para_text(l, p):
    hwp.SetPos(l, p, 0); hwp.Run("MoveSelParaEnd")
    t = hwp.GetTextFile("TEXT", "saveblock") or ""
    hwp.Run("Cancel")
    return t.replace("\r\n", "\n").strip("\n")


done = 0
for l in range(1, 1500):
    hwp.SetPos(l, 0, 0)
    if hwp.GetPos()[0] != l:
        continue
    p = 0
    while True:
        hwp.SetPos(l, p, 0)
        if tuple(hwp.GetPos()[:2]) != (l, p):
            break
        t = para_text(l, p)
        if "학년" in t and old in t:
            k = t.index(old)
            hwp.SetPos(l, p, k); hwp.Run("Select")
            for _ in range(len(old)):
                hwp.Run("MoveRight")
            act = hwp.CreateAction("InsertText"); s = act.CreateSet(); s.SetItem("Text", new); act.Execute(s)
            hwp.Run("Cancel")
            print("list", l, "para", p, repr(t), "->", repr(para_text(l, p)))
            done += 1
        p += 1
hwp.SaveAs(src, "HWP", ""); hwp.SaveAs(pdf, "PDF", "")
print("replaced", done, "pages", hwp.PageCount)
hwp.Clear(1); hwp.Quit()
