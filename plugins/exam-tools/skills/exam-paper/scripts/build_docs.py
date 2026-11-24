# -*- coding: utf-8 -*-
"""정답·배점표(md), 이원목적분류표(html -> 한글은 html2hwp.ps1 + polish_doc.py), 문항정보표(나이스 입력용 md·csv).

usage: build_docs.py ITEMS.py PROFILE.json OUTDIR
PROFILE.json 에 필요한 값 (profile_example.json 참고):
  school, subject, subject_code, grade, author, exam_title(예: "2026학년도 2학기 제2회 정기시험"), exam_date(예: "12월 3일 3교시"),
  units: {성취기준코드: [대단원, 중단원]}, standards: {성취기준코드: 성취기준 문장}, scope_note(이원목적분류표 아래 주석, 선택)
"""
import csv, html, importlib.util, json, pathlib, sys
from collections import Counter, defaultdict

items_py, profile_path, outdir = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
spec = importlib.util.spec_from_file_location("items", items_py)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
ITEMS, choice_list = mod.ITEMS, mod.choice_list
P = json.load(open(profile_path, encoding="utf-8"))
outdir.mkdir(parents=True, exist_ok=True)
NUM = "①②③④⑤"
CATS = ["지식·이해", "과정·기능", "가치·태도"]
UNIT = P.get("units", {})
STD = P.get("standards", {})
total = sum(i["pts"] for i in ITEMS)
pts_kinds = sorted({i["pts"] for i in ITEMS})
title = f"{P['exam_title']} — {P['grade']}학년 {P['subject']}"


def ans_text(it):
    ch = choice_list(it)[it["ans"] - 1]
    if isinstance(ch, list):
        ch = " / ".join(ch)
    return f"{NUM[it['ans'] - 1]} {ch}"


byc = Counter(i["cat"] for i in ITEMS)
byd = {d: [sum(1 for i in ITEMS if i["diff"] == d), sum(i["pts"] for i in ITEMS if i["diff"] == d)] for d in "상중하"}
bys = defaultdict(lambda: [0, 0])
for i in ITEMS:
    bys[i["std"]][0] += 1; bys[i["std"]][1] += i["pts"]
bya = Counter(i["ans"] for i in ITEMS)

# ---------- 정답·배점표 ----------
L = [f"# {title} 정답 및 배점표\n",
     f"- 형식: 선택형 {len(ITEMS)}문항, {total:g}점 (배점 {' / '.join(f'{p:g}' for p in pts_kinds)})", "",
     "| 번호 | 정답 | 배점 | 성취기준 | 난이도 | 평가 범주 | 교과서 | 학습지 연계 |", "|---:|---|---:|---|:---:|---|---|---|"]
L += [f"| {i['no']} | {ans_text(i)} | {i['pts']:g} | [{i['std']}] | {i['diff']} | {i['cat']} | {i.get('pages', '')}쪽 | {i.get('ws', '')} |" for i in ITEMS]
L += [f"| 계 | | {total:g} | | | | | |", "", "## 정답 분포", "| " + " | ".join(NUM) + " |", "|---|---|---|---|---|",
      "| " + " | ".join(str(bya[k]) for k in range(1, 6)) + " |", "", "## 해설"]
L += [f"**{i['no']}번 — {ans_text(i)} ({i['pts']:g}점)** {i.get('expl', '')}\n" for i in ITEMS]
(outdir / "정답_배점표.md").write_text("\n".join(L), encoding="utf-8")

# ---------- 이원목적분류표 html ----------
F = "font-family:'함초롬바탕';font-size:8.5pt"
td = lambda s, w=None, extra="": f"<td align='center'{f' width={w}' if w else ''} style='{F};{extra}'>{s}</td>"
rs = lambda s, w: f"<td rowspan='2' align='center' width={w} style='{F}'>{s}</td>"
hdr1 = ("<tr>" + rs("번호", 26) + rs("대단원", 72) + rs("중단원", 78) + rs("성취기준", 64) + rs("평가 요소", 122)
        + f"<td colspan='3' align='center' style='{F}'>평가 범주</td><td colspan='3' align='center' style='{F}'>난이도</td>"
        + rs("문항<br>형식", 44) + rs("배점", 30) + rs("정답", 30) + "</tr>")
hdr2 = "<tr>" + td("지식·<br>이해", 34) + td("과정·<br>기능", 34) + td("가치·<br>태도", 34) + td("상", 22) + td("중", 22) + td("하", 22) + "</tr>"
rows = []
for it in ITEMS:
    u = UNIT.get(it["std"], ["", ""])
    rows.append("<tr>" + td(it["no"]) + td(u[0]) + td(u[1]) + td(it["std"]) + td(html.escape(it.get("elem", "")), extra="text-align:left")
                + "".join(td("○" if it["cat"] == c else "") for c in CATS) + "".join(td("○" if it["diff"] == d else "") for d in "상중하")
                + td("선택형") + td(f"{it['pts']:g}") + td(NUM[it["ans"] - 1]) + "</tr>")
tot = ("<tr>" + td("계") + td("") * 4 + "".join(td(byc[c]) for c in CATS) + "".join(td(byd[d][0]) for d in "상중하")
       + td(len(ITEMS)) + td(f"{total:g}") + td("") + "</tr>")
info = ("<table border='1' cellspacing='0' cellpadding='3' width='634' style='border-collapse:collapse'><tr>"
        + td("학교", 56) + td(P["school"], 206) + td("과목", 50) + td(P["subject"], 84) + td("학년", 62) + td(P["grade"], 30)
        + td("출제자", 56) + td(P["author"], 90) + "</tr><tr>" + td("문항 수") + td(f"선택형 {len(ITEMS)}") + td("총점") + td(f"{total:g}점")
        + td("실시일자") + f"<td colspan='3' align='center' style='{F}'>{P.get('exam_date', '')}</td></tr></table>")
std_rows = "".join("<tr>" + td(s) + f"<td style='{F}'>{html.escape(STD.get(s, ''))}</td>"
                   + td(", ".join(str(i["no"]) for i in ITEMS if i["std"] == s)) + td(v[0]) + td(f"{v[1]:g}") + "</tr>"
                   for s, v in sorted(bys.items()))
doc = f"""<html><head><meta charset='utf-8'></head><body>
<p style="font-family:'함초롬바탕';font-size:15pt;font-weight:bold;text-align:center">{P['exam_title']} 이원목적분류표</p>
{info}<p style='{F}'>&nbsp;</p>
<table border='1' cellspacing='0' cellpadding='2' width='634' style='border-collapse:collapse'>{hdr1}{hdr2}{''.join(rows)}{tot}</table>
<p style='{F}'>{html.escape(P.get('scope_note', '※ 평가 범주는 2022 개정 교육과정의 범주(지식·이해, 과정·기능, 가치·태도)를 따름.'))}</p>
<p style="font-family:'함초롬바탕';font-size:11pt;font-weight:bold">1. 성취기준별 문항 수와 배점</p>
<table border='1' cellspacing='0' cellpadding='3' width='634' style='border-collapse:collapse'><tr>{td('성취기준',122)}{td('성취기준 내용',322)}{td('문항 번호',90)}{td('문항 수',50)}{td('배점',50)}</tr>{std_rows}
<tr>{td('계')}{td('')}{td('')}{td(len(ITEMS))}{td(f'{total:g}')}</tr></table>
<p style="font-family:'함초롬바탕';font-size:11pt;font-weight:bold">2. 정답 분포</p>
<table border='1' cellspacing='0' cellpadding='3' width='634' style='border-collapse:collapse'><tr>{td('정답 번호')}{''.join(td(n) for n in NUM)}{td('계')}</tr>
<tr>{td('문항 수')}{''.join(td(bya[k]) for k in range(1, 6))}{td(len(ITEMS))}</tr>
<tr>{td('문항 번호')}{''.join(td(', '.join(str(i['no']) for i in ITEMS if i['ans'] == k)) for k in range(1, 6))}{td('')}</tr></table>
</body></html>"""
(outdir / "twoway.html").write_text(doc, encoding="utf-8")

# ---------- 문항정보표 (나이스 입력용) ----------
M = [f"# {title} 문항정보표 (나이스 입력용)\n", "| 번호 | 유형 | 배점 | 정답 | 성취기준 | 난이도 | 평가 범주 | 평가 요소 |", "|---:|---|---:|:---:|---|:---:|---|---|"]
M += [f"| {i['no']} | 선택형 | {i['pts']:g} | {i['ans']} | {i['std']} | {i['diff']} | {i['cat']} | {i.get('elem', '')} |" for i in ITEMS]
(outdir / "문항정보표_나이스입력용.md").write_text("\n".join(M), encoding="utf-8")
with open(outdir / "문항정보표_나이스입력용.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["번호", "유형", "배점", "정답", "성취기준", "성취기준 내용", "난이도", "평가 범주", "평가 요소"])
    for i in ITEMS:
        w.writerow([i["no"], "선택형", f"{i['pts']:g}", i["ans"], i["std"], STD.get(i["std"], ""), i["diff"], i["cat"], i.get("elem", "")])
print("ok ->", outdir, "| total", total, "| answers", dict(sorted(bya.items())))
