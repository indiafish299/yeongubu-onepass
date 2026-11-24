# -*- coding: utf-8 -*-
"""Export every page of an HWP file as PNG using Hancom's own renderer.
usage: pageimg.py HWP OUTDIR [DPI]"""
import os, sys, shutil, tempfile
import win32com.client as win32

src, outdir = sys.argv[1], sys.argv[2]
dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 150
os.makedirs(outdir, exist_ok=True)
tmp = os.path.join(tempfile.gettempdir(), "pageimg_src.hwp")
shutil.copyfile(src, tmp)
hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
try:
    hwp.XHwpWindows.Item(0).Visible = False
except Exception:
    pass
hwp.Open(tmp, "HWP", "forceopen:true")
n = hwp.PageCount
stem = os.path.splitext(os.path.basename(src))[0]
for p in range(n):
    out = os.path.join(outdir, f"{stem}_p{p+1}.png")
    r = hwp.CreatePageImage(out, p, dpi, 24, "png")
    print(p + 1, r, os.path.exists(out))
hwp.Clear(1); hwp.Quit()
