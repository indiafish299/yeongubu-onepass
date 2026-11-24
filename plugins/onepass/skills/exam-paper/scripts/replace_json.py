# -*- coding: utf-8 -*-
"""Replace text in HWP files using a UTF-8 JSON job list (Korean never passes through the command line).
JSON: [{"src": "...hwp", "out": "...hwp", "pdf": "...pdf", "pairs": [["find", "repl"], ...]}, ...]
Paths must be Windows paths with backslashes (forward slashes trigger Hancom's access prompt).
usage: <python> replace_json.py JOBS.json"""
import json, os, shutil, sys
import win32com.client as win32
sys.stdout.reconfigure(encoding="utf-8")
jobs = json.load(open(sys.argv[1], encoding="utf-8"))
hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
try:
    hwp.XHwpWindows.Item(0).Visible = False
except Exception:
    pass
for j in jobs:
    src, out = os.path.normpath(j["src"]), os.path.normpath(j["out"])
    shutil.copyfile(src, out)
    hwp.Open(out, "HWP", "forceopen:true")
    for a, b in j["pairs"]:
        hwp.Run("MoveDocBegin")
        f = hwp.HParameterSet.HFindReplace
        hwp.HAction.GetDefault("AllReplace", f.HSet)
        f.FindString = a; f.ReplaceString = b; f.IgnoreMessage = 1; f.Direction = 2; f.FindType = 1
        print(os.path.basename(out), repr(a), "->", repr(b), hwp.HAction.Execute("AllReplace", f.HSet))
    hwp.SaveAs(out, "HWP", "")
    if j.get("pdf"):
        hwp.SaveAs(os.path.normpath(j["pdf"]), "PDF", "")
    hwp.Clear(1)
hwp.Quit()
print("done")
