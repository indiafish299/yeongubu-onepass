# -*- coding: utf-8 -*-
"""Item data -> exam body for Hancom import, plus the blind review paper and the assembly config.

usage: build_body.py ITEMS.py PROFILE.json OUTDIR
  ITEMS.py      defines ITEMS (list of dict) and choice_list(it)  — see items_example.py
  PROFILE.json  school style + template facts                    — see profile_example.json
writes OUTDIR/body.html   (answer number highlighted, as the 원안 format wants)
       OUTDIR/solver.md   (review paper WITHOUT answers; 부정 발문 keeps <u>…</u>)
       OUTDIR/assemble_cfg.json (for assemble.py)

Hancom HTML import notes (learned the hard way):
- td `padding` is (partly) honoured, `cellpadding` is ignored.
- 장평/자간/어절 줄나눔/exact hanging indents cannot be set from CSS: assemble.py sets them afterwards.
- A table's anchor paragraph inherits the previous paragraph's margins: assemble.py re-indents anchors.
"""
import html, importlib.util, json, pathlib, sys

items_py, profile_path, outdir = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
spec = importlib.util.spec_from_file_location("items", items_py)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
ITEMS, choice_list = mod.ITEMS, mod.choice_list
P = json.load(open(profile_path, encoding="utf-8"))
outdir.mkdir(parents=True, exist_ok=True)

NUM = "①②③④⑤"
FONT = f"font-family:'{P['font']}';font-size:{P['font_size']}pt;line-height:{P['line_height']}%"
BFONT = f"font-family:'{P['box_font']}';font-size:{P['box_size']}pt;line-height:{P['line_height']}%"
TFONT = f"font-family:'{P['box_font']}';font-size:{P['box_size']}pt;line-height:{P.get('table_line_height', 150)}%"
W = P.get("box_width_px", 360)              # column (~385 px for 2-col B4) minus the item-text indent
BOX_PAD = "padding:3px 7px 4px 7px"         # inner line margins are added in assemble.py (BOX_MARGIN)
CELL_PAD = "padding:3px 5px"


def esc(s):
    # 부정 발문은 밑줄 + 굵게(옳지 <u>않은</u> -> '않은'만). 정답 번호의 노란 배경은 한글로 가져오면
    # 글자 '음영색'(인쇄됨)이 되므로 rebuild.ps1 끝에서 markpen.py가 형광펜(인쇄 안 됨)으로 바꾼다.
    return html.escape(s).replace("&lt;u&gt;", "<u><b>").replace("&lt;/u&gt;", "</b></u>")


def pts(p):
    return f"[{p:g}점]"


# ---------- solver.md (blind review paper) ----------
md = [f"# {P.get('title', '원안')} — 검토용 문제지 (정답 없음)\n"]
for it in ITEMS:
    md.append(f"\n## {it['no']}.  {pts(it['pts'])}\n")
    if it.get("stem"):
        md.append(it["stem"] + "\n")
    if it.get("box"):
        md.append("\n" + "\n".join(f"> {b}" for b in it["box"]) + "\n")
    if it.get("table"):
        t = it["table"]
        md.append("\n| " + " | ".join(t[0]) + " |\n|" + "---|" * len(t[0]) + "\n")
        md += ["| " + " | ".join(r) + " |\n" for r in t[1:]]
    if it.get("img"):
        md.append(f"\n[그림: {pathlib.Path(it['img']).name} — 이 폴더의 그림 파일을 직접 열어 볼 것]\n")
    md.append("\n" + it["q"] + "\n")                      # keeps <u>…</u> so reviewers see the underline
    if it.get("bogi"):
        md.append("\n[보기]\n" + "\n".join(it["bogi"]) + "\n")
    ch = choice_list(it)
    if it.get("header"):
        md.append("\n| | " + " | ".join(it["header"]) + " |\n|" + "---|" * (len(it["header"]) + 1) + "\n")
        md += [f"| {NUM[k]} | " + " | ".join(row) + " |\n" for k, row in enumerate(ch)]
    else:
        md.append("\n" + "\n".join(f"{NUM[k]} {c}" for k, c in enumerate(ch)) + "\n")
(outdir / "solver.md").write_text("".join(md), encoding="utf-8")


# ---------- body.html ----------
def hang(text, em=1.4, extra="", font=None):
    return f"<p style='{font or FONT};margin:0;margin-left:{em}em;text-indent:-{em}em;{extra}'>{text}</p>"


def box_table(lines, center_title=None):
    rows = [hang(esc(l), 2.6 if l.startswith("(") else (3.4 if l.startswith("학생") else 1.4), font=BFONT) for l in lines]
    title = f"<p style='margin:0;text-align:center;{BFONT}'>{center_title}</p>" if center_title else ""
    return (f"<table width='{W}' border='1' cellspacing='0' cellpadding='0' style='border-collapse:collapse;width:{W}px'>"
            f"<tr><td style='{BOX_PAD}'>{title}{''.join(rows)}</td></tr></table>")


def data_table(t, widths=None):
    n = len(t[0])
    widths = widths or [W // n] * n
    widths = [round(w * W / sum(widths)) for w in widths]
    widths[-1] += W - sum(widths)
    out = [f"<table width='{W}' border='1' cellspacing='0' cellpadding='0' style='border-collapse:collapse;width:{W}px'>",
           "<colgroup>" + "".join(f"<col width='{w}'>" for w in widths) + "</colgroup>"]
    for i, r in enumerate(t):
        out.append("<tr>" + "".join(
            f"<td width='{widths[j]}' align='center' style='width:{widths[j]}px;{CELL_PAD};{TFONT};"
            f"{'background-color:#e8e8e8;' if i == 0 else ''}'>{esc(c).replace(chr(10), '<br>')}</td>"
            for j, c in enumerate(r)) + "</tr>")
    out.append("</table>")
    return "".join(out)


def mark(k, ans):
    return f"<span style='background-color:yellow'>{NUM[k]}</span>" if k + 1 == ans else NUM[k]


def choices_html(it):
    ch, ans = choice_list(it), it["ans"]
    if it.get("header"):                                   # 연결형 (가)(나)(다) table
        cw = [32] + [round((W - 32) / len(it["header"]))] * len(it["header"])
        cg = "<colgroup>" + "".join(f"<col width='{w}'>" for w in cw) + "</colgroup>"
        td = lambda j, s, a="center": f"<td width='{cw[j]}' align='{a}' style='width:{cw[j]}px;{FONT}'>{s}</td>"
        rows = ["<tr>" + td(0, "") + "".join(td(j + 1, h) for j, h in enumerate(it["header"])) + "</tr>"]
        rows += ["<tr>" + td(0, mark(k, ans), "left") + "".join(td(j + 1, esc(c)) for j, c in enumerate(row)) + "</tr>"
                 for k, row in enumerate(ch)]
        return f"<table width='{sum(cw)}' border='0' cellspacing='0' cellpadding='1' style='width:{sum(cw)}px'>{cg}{''.join(rows)}</table>"
    if it.get("long") or max(len(c) for c in ch) > 12:      # one choice per line
        return "".join(f"<p style='{FONT};margin:0;margin-left:3.0em;text-indent:-1.4em'>{mark(k, ans)} {esc(c)}</p>"
                       for k, c in enumerate(ch))
    cw = W // 3                                             # 3 + 2 layout
    cells = [f"{mark(k, ans)} {esc(c)}" for k, c in enumerate(ch)]
    r1 = "".join(f"<td width='{cw}' style='{FONT}'>{c}</td>" for c in cells[:3])
    r2 = "".join(f"<td width='{cw}' style='{FONT}'>{c}</td>" for c in cells[3:]) + "<td></td>"
    return f"<table width='{W}' border='0' cellspacing='0' cellpadding='1' style='width:{W}px'><tr>{r1}</tr><tr>{r2}</tr></table>"


parts = []
for it in ITEMS:
    first = esc(it["stem"]) if it.get("stem") else esc(it["q"]) + f" {pts(it['pts'])}"
    p = [hang(f"{it['no']}. {first}", 1.6, "margin-top:8pt;margin-bottom:3pt;")]
    if it.get("box"):
        p.append(box_table(it["box"]))
    if it.get("table"):
        p.append(data_table(it["table"], it.get("widths")))
    if it.get("img"):
        p.append(f"<p style='margin:2px 0;text-align:center'><img src='{it['img']}' width='{it.get('img_width', 270)}'></p>")
    if it.get("stem"):
        p.append(f"<p style='{FONT};margin-top:4pt;margin-bottom:3pt;margin-left:1.6em;margin-right:0'>{esc(it['q'])} {pts(it['pts'])}</p>")
    if it.get("bogi"):
        p.append(box_table(it["bogi"], center_title="[보기]"))
    p.append(choices_html(it))
    p.append("<p style='font-family:\"함초롬바탕\";font-size:6pt;line-height:100%;margin:0'>§§</p>")  # item end marker
    parts.append("".join(p))
(outdir / "body.html").write_text("<html><head><meta charset='utf-8'></head><body>" + "".join(parts) + "</body></html>",
                                  encoding="utf-8")

# ---------- assembly config ----------
starts = []
for it in ITEMS:
    first = (it.get("stem") or it["q"]).replace("<u>", "").replace("</u>", "")
    starts.append(f"{it['no']}. {first[:10]}")
cfg = {"start": P["template_first_item_text"], "marker": "§§", "items": starts, "replace": P.get("replace", [])}
(outdir / "assemble_cfg.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
print("ok", len(ITEMS), "items ->", outdir)
