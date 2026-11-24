# -*- coding: utf-8 -*-
"""Assemble the exam: template (previous 원안) + body.hwp.
Steps: insert body -> tables flow with text -> 어절 line breaking + school character style (장평 95, 자간 -5)
-> exact hanging indents -> per-paragraph letter-spacing tuning measured on PDF exports (no loose lines,
no orphan words) -> keep every item inside one column -> header replacements.
usage: assemble.py TEMPLATE BODY OUT_HWP OUT_PDF CONFIG_JSON"""
import json, os, re, shutil, statistics, sys, tempfile
import win32com.client as win32

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdflines import lines as pdf_lines

sys.stdout.reconfigure(encoding="utf-8")
tpl, body, out_hwp, out_pdf, cfg_path = [os.path.normpath(a) for a in sys.argv[1:6]]  # backslash paths for Hancom
cfg = json.load(open(cfg_path, encoding="utf-8"))
shutil.copyfile(tpl, out_hwp)
hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
try:
    hwp.XHwpWindows.Item(0).Visible = False
except Exception:
    pass
hwp.Open(out_hwp, "HWP", "forceopen:true")

BASE_SP, RATIO, CONDENSE = -5, 95, 50          # school style (midterm): 자간 -5 %, 장평 95 %; 최소 공백 50 %
CANDIDATES = [-6, -7, -8, -9, -10, -11, -12, -4, -3, -2, -1, 0]   # letter spacings tried per paragraph
# (-11, -12 carry a heavy penalty in badness(): used only when nothing else removes an orphan word)
LANGS = ["Hangul", "Latin", "Hanja", "Japanese", "Other", "Symbol", "User"]
LABEL = re.compile(r"^(\d+\. |[ㄱ-ㅎ]\. |\([가-하]\) |학생 [A-Z]: |[㉠-㉻] |[①-⑤] )")
# label_len: (list, para) -> label length incl. the 묶음 빈칸 after it; set in 3b, reused after tuning
# label_len: (list, para) -> label length incl. the fixed-width space; set in 3b, reused after tuning


# ---------------------------------------------------------------- helpers
def find(text, from_start):
    if from_start:
        hwp.Run("MoveDocBegin")
    f = hwp.HParameterSet.HFindReplace
    hwp.HAction.GetDefault("RepeatFind", f.HSet)
    f.FindString = text; f.IgnoreMessage = 1; f.Direction = 0; f.FindType = 1
    return hwp.HAction.Execute("RepeatFind", f.HSet)


def loc():
    r = hwp.KeyIndicator()          # (ok, seccnt, secno, prnpageno, colno, line, pos, over, ctrlname)
    return r[3], r[4], r[5]


def list_ids(upto=1200):
    """All list ids that exist (0 = main text; others = table cells, header/footer, text boxes)."""
    ids = []
    for l in range(0, upto):
        hwp.SetPos(l, 0, 0)
        if hwp.GetPos()[0] == l:
            ids.append(l)
    return ids


def paras(l, start=0):
    p = start
    while True:
        hwp.SetPos(l, p, 0)
        if tuple(hwp.GetPos()[:2]) != (l, p):
            return
        yield p
        p += 1


def para_text(l, p):
    hwp.SetPos(l, p, 0); hwp.Run("MoveSelParaEnd")
    t = hwp.GetTextFile("TEXT", "saveblock") or ""
    hwp.Run("Cancel")
    return t.replace("\r\n", "\n").strip("\n")


def para_end(l, p):
    hwp.SetPos(l, p, 0); hwp.Run("MoveParaEnd")
    return hwp.GetPos()[2]


def set_para(**kw):
    ps = hwp.HParameterSet.HParaShape
    hwp.HAction.GetDefault("ParagraphShape", ps.HSet)
    for k, v in kw.items():
        setattr(ps, k, v)
    return hwp.HAction.Execute("ParagraphShape", ps.HSet)


def get_para(name):
    ps = hwp.HParameterSet.HParaShape
    hwp.HAction.GetDefault("ParagraphShape", ps.HSet)
    return getattr(ps, name)


def char_items(**kw):
    """Apply only the given CharShape items to the current selection (other attributes stay)."""
    act = hwp.CreateAction("CharShape"); s = act.CreateSet()
    for k, v in kw.items():
        s.SetItem(k, v)
    act.Execute(s)


def style_items(sp):
    d = {f"Spacing{x}": sp for x in LANGS}
    d.update({f"Ratio{x}": RATIO for x in LANGS})
    return d


def set_spacing(l, p, v):
    e = para_end(l, p)
    hwp.SetPos(l, p, 0); hwp.SelectText(p, 0, p, e)
    char_items(**{f"Spacing{x}": v for x in LANGS})
    hwp.Run("Cancel")


def norm(s):
    return re.sub(r"\s+", "", s)


def replace_all(a, b):
    hwp.Run("MoveDocBegin")
    f = hwp.HParameterSet.HFindReplace
    hwp.HAction.GetDefault("AllReplace", f.HSet)
    f.FindString = a; f.ReplaceString = b; f.IgnoreMessage = 1; f.Direction = 2; f.FindType = 1
    hwp.HAction.Execute("AllReplace", f.HSet)


# ---------------------------------------------------------------- 1) template body out
assert find(cfg["start"], True), "start not found"
assert hwp.GetPos()[0] == 0, "item 1 not in main text"
hwp.Run("Cancel"); hwp.Run("MoveParaBegin"); hwp.Run("Select"); hwp.Run("MoveDocEnd"); hwp.Run("Delete")
n_tpl, c = 0, hwp.HeadCtrl
while c is not None:
    if c.CtrlID == "tbl":
        n_tpl += 1
    c = c.Next
tpl_lists = list_ids()
print("template tables", n_tpl, "lists", len(tpl_lists))
hwp.SetPos(0, 0, 0); hwp.Run("MoveDocEnd")      # list_ids() moves the cursor: insert at the end

# ---------------------------------------------------------------- 2) insert body
ins = hwp.HParameterSet.HInsertFile
hwp.HAction.GetDefault("InsertFile", ins.HSet)
ins.filename = body; ins.KeepSection = 0; ins.KeepCharshape = 1; ins.KeepParashape = 1; ins.KeepStyle = 0
print("insert", hwp.HAction.Execute("InsertFile", ins.HSet))

# ---------------------------------------------------------------- 3) body tables: never split, flow with text
anchors, k, c = set(), 0, hwp.HeadCtrl
while c is not None:
    if c.CtrlID == "tbl":
        k += 1
        if k > n_tpl:
            p = c.Properties; p.SetItem("PageBreak", 0); p.SetItem("TreatAsChar", 1); c.Properties = p
            a = c.GetAnchorPos(0); anchors.add((a.Item("List"), a.Item("Para")))
    c = c.Next
print("body tables", k - n_tpl)

# ---------------------------------------------------------------- 3a) 어절 breaking, 최소 공백, 장평/자간 (body only)
assert find(cfg["items"][0], True), "item 1 not found"
hwp.Run("Cancel")
body_start = hwp.GetPos()[1]
assert body_start >= 1, "item 1 shares the template's first paragraph"
hwp.Run("MoveParaBegin"); hwp.Run("Select"); hwp.Run("MoveDocEnd")
set_para(BreakNonLatinWord=0, Condense=CONDENSE); char_items(**style_items(BASE_SP)); hwp.Run("Cancel")
body_lists = [l for l in list_ids() if l > max(tpl_lists)]
for l in body_lists:
    hwp.SetPos(l, 0, 0); hwp.Run("MoveListBegin"); hwp.Run("MoveSelListEnd")
    set_para(BreakNonLatinWord=0, Condense=CONDENSE); char_items(**style_items(BASE_SP)); hwp.Run("Cancel")
print("body cell lists", len(body_lists), "| first:", para_text(body_lists[0], 0)[:12])

# ---------------------------------------------------------------- 3b) exact hanging indents
BOX_MARGIN = 800                                  # 4 pt inner left/right margin of lines inside 보기/자료 boxes
BOX_LABEL = re.compile(r"^([ㄱ-ㅎ]\.|\([가-하]\)|학생 [A-Z]:|[㉠-㉻])\s")


def indent_at_label(l, p, text):
    """Label + 묶음 빈칸 (normal width, not squeezed by 최소 공백 like a plain space), then hang the
    following lines exactly under the text after the label. Box lines: hang first, then move the whole
    paragraph BOX_MARGIN inwards (hanging at caret does not account for a left margin inside cells)."""
    if (l, p) in label_len:
        n = label_len[(l, p)]
    else:
        m = LABEL.match(text)
        if not m or len(norm(text)) < 8:                           # short single-line cells stay as they are
            return None
        n = len(m.group(1))
        hwp.SetPos(l, p, n - 1); hwp.Run("Select"); hwp.Run("MoveRight"); hwp.Run("Delete")
        hwp.Run("InsertNonBreakingSpace")
        label_len[(l, p)] = n
    box = l in box_lists
    if box:
        hwp.SetPos(l, p, 0); set_para(LeftMargin=0, RightMargin=0)
    hwp.SetPos(l, p, n); hwp.Run("ParagraphShapeIndentAtCaret")
    if box:
        hwp.SetPos(l, p, 0); set_para(LeftMargin=BOX_MARGIN, RightMargin=BOX_MARGIN)
    return n


label_len, box_lists = {}, set()


item_paras = []                                   # (item no, first para, marker para)
for i, s in enumerate(cfg["items"]):
    assert find(s, True), f"item {i+1} not found"
    hwp.Run("Cancel"); p0 = hwp.GetPos()[1]
    assert find(cfg["marker"], False); hwp.Run("Cancel"); p1 = hwp.GetPos()[1]
    item_paras.append((i + 1, p0, p1))
for no, p0, p1 in item_paras:
    hwp.SetPos(0, p0, 0); set_para(LeftMargin=0)
    indent_at_label(0, p0, para_text(0, p0))
    hwp.SetPos(0, p0, 0); ind = -get_para("Indentation")          # where the stem text starts
    for p in range(p0 + 1, p1):
        hwp.SetPos(0, p, 0)
        if (0, p) in anchors:
            set_para(LeftMargin=ind, Indentation=0)
            continue
        t = para_text(0, p)
        if not t.strip():
            continue                                               # image / spacer paragraph
        set_para(LeftMargin=ind, Indentation=0)                    # question line or long choice
        indent_at_label(0, p, t)
    if no in (1, 10):
        print(f"item {no}: text indent {ind / 200:.1f} pt")
for l in body_lists:
    texts = {p: para_text(l, p) for p in paras(l)}
    if any(BOX_LABEL.match(t) and len(norm(t)) >= 8 for t in texts.values()):
        box_lists.add(l)
    for p, t in texts.items():
        if indent_at_label(l, p, t) is None and l in box_lists:
            hwp.SetPos(l, p, 0); set_para(LeftMargin=BOX_MARGIN, RightMargin=BOX_MARGIN)
print("box lists", len(box_lists))


# ---------------------------------------------------------------- 3c) letter-spacing tuning, measured on PDF
def tunable():
    out = []
    for p in range(body_start, max(p1 for _, _, p1 in item_paras)):
        if (0, p) not in anchors:
            out.append((0, p))
    for l in body_lists:
        out += [(l, p) for p in paras(l)]
    res = []
    for l, p in out:
        t = norm(para_text(l, p))
        if len(t) >= 8 and "§§" not in t:
            res.append(((l, p), t))
    return res


_round = 0


def measure(targets, debug=False):
    """Export a PDF and return {key: (n_lines, worst gap ratio of non-last lines, orphan?)}."""
    global _round
    _round += 1
    path = os.path.join(tempfile.gettempdir(), f"assemble_tune_{os.getpid()}_{_round}.pdf")   # new file every round
    hwp.SaveAs(path, "PDF", "")
    # body only: the running header ("2면", y 782) and the footer (school name, copyright, y < 75) would
    # otherwise sit between the two halves of a paragraph that runs over a page
    ls = [x for x in pdf_lines(path) if x["norm"] and 80 < x["y"] < 770]
    ls.sort(key=lambda x: (x["page"], x["col"], -x["y"]))
    stream, starts = "", []
    for x in ls:
        starts.append(len(stream)); stream += x["norm"]
    ends = [s + len(x["norm"]) for s, x in zip(starts, ls)]
    found = {}
    by_text = {}
    for key, t in targets:                                          # targets are in document order
        by_text.setdefault(t, []).append(key)
    for t, keys in by_text.items():
        occ, k0 = [], stream.find(t)
        while k0 >= 0:
            occ.append(k0); k0 = stream.find(t, k0 + len(t))
        if debug and len(occ) != len(keys):
            print(f"   [map] {t[:16]}: {len(keys)} paragraphs, {len(occ)} places in PDF")
        for key, k0 in zip(keys, occ):                              # same sentence: n-th paragraph = n-th place
            try:
                i0 = starts.index(k0); i1 = ends.index(k0 + len(t))
            except ValueError:
                if debug:
                    print(f"   [map] {t[:16]}: shares a PDF line with other text")
                continue
            found[key] = ls[i0:i1 + 1]
    # natural word gap per font size: last lines are not justified
    nat = {}
    for seg in found.values():
        g = seg[-1]["gaps"]
        if g:
            nat.setdefault(round(seg[-1]["size"]), []).append(sum(g) / len(g))
    nat = {s: statistics.median(v) for s, v in nat.items()}
    res = {}
    for key, seg in found.items():
        worst = 0.0
        for x in seg[:-1]:
            g = x["gaps"]; n = nat.get(round(x["size"]))
            if g and n:
                worst = max(worst, (sum(g) / len(g)) / n)
        last = seg[-1]["text"].strip()
        orphan = len(seg) > 1 and (len(last) <= 4 or re.fullmatch(r"\[\d+(\.\d+)?점\]", last) is not None)
        res[key] = (len(seg), worst, orphan)
    return res


def badness(m, base_lines, v):
    n, worst, orphan = m
    return (max(0.0, worst - 1.25) + (1.0 if orphan else 0.0) + 2.0 * max(0, n - base_lines)
            + abs(v - BASE_SP) * 0.02 + max(0, -10 - v) * 0.15)


targets = tunable()
base = measure(targets, debug=True)
print("paragraphs measured", len(base), "of", len(targets))
todo = {k: m for k, m in base.items() if m[0] > 1 and badness(m, m[0], BASE_SP) > 0.05}
print("paragraphs to tune", len(todo))
score = {k: {BASE_SP: badness(m, m[0], BASE_SP)} for k, m in todo.items()}
for v in CANDIDATES:
    for (l, p) in todo:
        set_spacing(l, p, v)
    mv = measure(targets)
    for k in todo:
        if k in mv:
            score[k][v] = badness(mv[k], todo[k][0], v)
if os.environ.get("EXAM_DEBUG"):
    for k in todo:
        print("   [score]", k, {v: round(b, 2) for v, b in sorted(score[k].items())})
choice = {}
for k in todo:
    best = min(score[k], key=lambda v: score[k][v])
    choice[k] = best
    set_spacing(k[0], k[1], best)
final = measure(targets)
reverted = [k for k in todo if k in final and choice[k] != BASE_SP
            and badness(final[k], todo[k][0], choice[k]) > badness(todo[k], todo[k][0], BASE_SP)]
for k in reverted:                                                  # never leave a paragraph worse than before
    set_spacing(k[0], k[1], BASE_SP); choice[k] = BASE_SP
for k in todo:                                                      # label width changed with the spacing:
    if choice[k] != BASE_SP and k in label_len:                     # re-align wrapped lines to the text
        indent_at_label(k[0], k[1], "")
final = measure(targets)
print("reverted", len(reverted))
left = [k for k in todo if k in final and (final[k][2] or final[k][1] > 1.45)]
print("still loose/orphan after re-indent", len(left))
text_of = dict(targets)
for k in todo:
    b0, f = todo[k], final.get(k)
    print(f"  {text_of[k][:14]:<14} 자간 {choice[k]:+d}%  gap {b0[1]:.2f}->{(f[1] if f else 0):.2f}"
          f"  orphan {b0[2]}->{f[2] if f else '?'}  lines {b0[0]}->{f[0] if f else '?'}")

# ---------------------------------------------------------------- 4) keep each item inside one column
# items are located by their end markers (the space after the item number is now a 묶음 빈칸)
def item_spans():
    """Marker paragraphs, read directly paragraph by paragraph (RepeatFind wraps around at the end)."""
    ends = []
    for p in paras(0, body_start):
        if norm(para_text(0, p)) == cfg["marker"]:
            ends.append(p)
    starts = [body_start] + [e + 1 for e in ends[:-1]]
    return list(zip(starts, ends))


spans = item_spans()
assert len(spans) == len(cfg["items"]), f"{len(spans)} item markers"
for i in range(len(spans)):
    p0, p1 = spans[i]
    hwp.SetPos(0, p0, 0); st = loc()
    hwp.SetPos(0, p1, 0); en = loc()
    if (st[0], st[1]) != (en[0], en[1]):
        if st[2] <= 2:
            print(f"item {i+1}: starts at column top but does not fit (p{st[0]} c{st[1]})"); continue
        hwp.SetPos(0, p0, 0); hwp.Run("BreakColumn")
        print(f"item {i+1}: moved to next column (was p{st[0]} c{st[1]} .. p{en[0]} c{en[1]})")
        spans = item_spans()                   # a column break may renumber paragraphs
final_pos = []
for p0, p1 in item_spans():
    hwp.SetPos(0, p0, 0); a = loc(); hwp.SetPos(0, p1, 0); b = loc()
    final_pos.append((a, b))

# ---------------------------------------------------------------- 5) markers -> spacer paragraphs; header
replace_all(cfg["marker"], "")
for r in cfg["replace"]:
    replace_all(r["find"], r["replace"])
check = measure(targets, debug=True)                    # final layout: report what is still not ideal
for k, (n, worst, orphan) in check.items():
    if orphan or worst > 1.45:
        print(f"CHECK {text_of[k][:20]}: lines {n} gap {worst:.2f} orphan {orphan}")
print("final check: measured", len(check), "of", len(targets))
hwp.SaveAs(out_hwp, "HWP", "")
hwp.SaveAs(out_pdf, "PDF", "")
print("pages", hwp.PageCount)
for i, (a, b) in enumerate(final_pos):
    print(f"  {i+1}: page {a[0]} col {a[1]}" + ("" if a[:2] == b[:2] else f"  !! ends on page {b[0]} col {b[1]}"))
hwp.Clear(1); hwp.Quit()
