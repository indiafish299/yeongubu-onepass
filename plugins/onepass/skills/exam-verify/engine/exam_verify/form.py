"""양식 점검: 시험지 PDF 의 글자와 위치만으로 문서 형식을 본다. AI 를 부르지 않고, 시험지는 이 PC 밖으로 나가지 않는다.
고치지는 않고 알리기만 한다(선지 순서를 바꾸면 정답 번호도 바뀐다).

  - 문항 번호가 1부터 빠짐·겹침 없이 이어지는지, 「총(N)문항」과 맞는지
  - 보기 번호 ①~⑤ 가 다 있고 차례대로인지
  - <보기>의 ㄱ·ㄴ·ㄷ, 자료의 (가)·(나)·(다) 가 차례대로인지, 합답형 선지에 없는 기호가 있는지
  - 선지 배열: 합답형은 관례 순서(ㄱ / ㄴ / ㄷ / ㄱ,ㄴ / ㄱ,ㄷ / ㄴ,ㄷ / ㄱ,ㄴ,ㄷ), 수치는 작은 값부터, 글은 짧은 것부터
  - 배치: 문항이 단·쪽에 걸침, 「[5점]」만 혼자 남은 줄, 선지 줄 간격이 본문보다 좁거나 문항마다 다름
  - 참고: 배점 합계, 정답 번호 분포(확인된 정답표가 있을 때)

usage: python form.py <시험지.pdf> [answers.json]
"""
import sys

sys.dont_write_bytecode = True
import json
import re
import statistics
from pathlib import Path

MM = 25.4 / 72  # pt → mm
CIRC = "①②③④⑤"
JAMO = "ㄱㄴㄷㄹㅁㅂㅅㅇ"
GANA = "가나다라마바사"
LEVELS = ("고칠 것", "확인", "참고")

ITEM_RE = re.compile(r"^(\d{1,2})\s*\.\s*\S")
ESSAY_RE = re.compile(r"^[\[<(【]?\s*(서답형|서술형|논술형)\s*(\d+)")
PTS_RE = re.compile(r"\[\s*(\d+(?:\s*\.\s*\d+)?)\s*점\s*\]")


# ---------- PDF → 줄 ----------

def read_lines(pdf: Path):
    """쪽마다 글자를 문서 순서대로 읽어 줄로 묶는다. 줄 = {page, col, cy, h, x0, x1, chars:[(ch,x0,x1,cy)], text}"""
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf))
    pages = []
    for pn, page in enumerate(doc, 1):
        W, H = page.get_size()
        tp = page.get_textpage()
        lines, cur, space = [], None, False
        for i in range(tp.count_chars()):
            ch = tp.get_text_range(i, 1)
            if not ch or not ch.strip():
                space = True
                continue
            l, b, r, t = tp.get_charbox(i)
            h = max(t - b, 1.0)
            cy = H - (b + t) / 2
            if cur is None or abs(cy - cur["cy"]) > 0.6 * max(h, cur["h"]) or l < cur["x1"] - 3 * max(h, cur["h"]):
                cur = {"page": pn, "cy": cy, "h": h, "x0": l, "x1": r, "chars": [], "W": W, "H": H}
                lines.append(cur)
                space = False
            prev = cur["chars"][-1][0] if cur["chars"] else ""
            tight = (prev.isdigit() and (ch.isdigit() or ch == ".")) or (prev == "." and ch.isdigit())  # 「11」「4.5」
            if cur["chars"] and (space or (l - cur["x1"] > 0.35 * h and not tight)):
                cur["chars"].append((" ", cur["x1"], l, cy))
            space = False
            cur["chars"].append((ch, l, r, cy))
            cur["x1"] = max(cur["x1"], r)
            cur["x0"] = min(cur["x0"], l)
        for ln in lines:
            ln["text"] = "".join(c[0] for c in ln["chars"]).strip()
        pages.append((W, H, lines))

    # 머리말·꼬리말: 쪽 위·아래 10% 안에서 여러 쪽에 되풀이되는 줄(숫자·띄어쓰기만 다른 것)이나 쪽 번호 꼴
    def edge(ln, H):
        return ln["cy"] / H > 0.9 or ln["cy"] / H < 0.1

    def norm(t):
        return re.sub(r"\s+", "", re.sub(r"\d+", "#", t))

    rep = {}
    for W, H, lines in pages:
        for ln in lines:
            if edge(ln, H):
                rep.setdefault(norm(ln["text"]), set()).add(ln["page"])
    out = []
    for W, H, lines in pages:
        body = [ln for ln in lines if not (edge(ln, H) and (
            len(rep.get(norm(ln["text"]), ())) > 1 or re.fullmatch(r"[\-–()#/·.면쪽]*", norm(ln["text"]))))]
        cross = sum(1 for ln in body if ln["x0"] / W < 0.47 and ln["x1"] / W > 0.53)
        two = len(body) > 8 and cross / len(body) < 0.2
        for ln in body:
            ln["col"] = (1 if (ln["x0"] + ln["x1"]) / 2 / W > 0.5 else 0) if two else 0
            ln["two"] = two
        out += body
    return out


def where(ln) -> str:
    side = ("왼쪽 단" if ln["col"] == 0 else "오른쪽 단") if ln["two"] else ""
    return f"{ln['page']}쪽 {side}".strip()


# ---------- 문항 나누기 ----------

def split_items(lines):
    # 단마다 왼쪽 끝: 번호 꼴(「3.」, 「서답형 1」)로 시작하는 줄들의 왼쪽 끝. 머리 표·결재란 글자는 섞지 않는다.
    margin = {}
    for ln in lines:
        if ITEM_RE.match(ln["text"]) or ESSAY_RE.match(ln["text"]):
            k = (ln["page"], ln["col"])
            margin[k] = min(margin.get(k, 1e9), ln["x0"])
    items, cur, intro, notes = [], None, [], []
    last = 0
    one = next((ln for ln in lines if (m1 := ITEM_RE.match(ln["text"])) and m1.group(1) == "1"), None)
    if one is not None:
        # 머리 표: 1번이 있는 쪽에서 첫 「<배점안내>」·문항 번호 줄보다 위(문서 순서와 상관없이 앞글).
        # 배점안내: 1번과 같은 단에서 1번보다 위. 다른 단은 머리 표 아래부터 본문이다(3번이 1번보다 위에 올 수 있다).
        pg = [ln for ln in lines if ln["page"] == one["page"]]
        hb = min(ln["cy"] for ln in pg if "배점" in ln["text"] or ITEM_RE.match(ln["text"]) or ESSAY_RE.match(ln["text"]))
        intro = [ln for ln in pg if ln["cy"] < hb - 1 or (ln["col"] == one["col"] and ln["cy"] < one["cy"] - 1)]
        ids = {id(x) for x in intro}
        lines = [ln for ln in lines if id(ln) not in ids]
    for ln in lines:
        m = ITEM_RE.match(ln["text"])
        e = ESSAY_RE.match(ln["text"])
        at_margin = ln["x0"] - margin.get((ln["page"], ln["col"]), ln["x0"]) < 0.025 * ln["W"]
        if e and at_margin:
            cur = {"q": f"서답{e.group(2)}", "n": None, "lines": [ln], "essay": True}
            items.append(cur)
            continue
        if m and at_margin and (cur is None or not cur.get("essay")):
            n = int(m.group(1))
            if last < n <= last + 3:
                if n != last + 1:
                    notes.append(("고칠 것", f"{last + 1}" if n == last + 2 else f"{last + 1}~{n - 1}",
                                  "문항 번호", f"{last}번 다음이 {n}번이다(번호가 빠짐)"))
                cur = {"q": str(n), "n": n, "lines": [ln], "essay": False}
                items.append(cur)
                last = n
                continue
            if n == last and n > 0:
                notes.append(("고칠 것", str(n), "문항 번호", f"{n}번이 두 번 나온다({where(ln)})"))
        if cur is None:
            intro.append(ln)
        else:
            cur["lines"].append(ln)
    return intro, items, notes


# ---------- 선지 ----------

def flat(item):
    """문항 글자를 한 줄로: [(ch, 줄 번호, x0, x1, cy)]"""
    out = []
    for li, ln in enumerate(item["lines"]):
        if out:
            out.append((" ", li, 0, 0, 0))
        out += [(c[0], li, c[1], c[2], c[3]) for c in ln["chars"]]
    return out


def choices(item):
    """마지막 ⑤ 에서 거슬러 올라가 ①~⑤ 한 벌을 찾는다. (번호들, 위치들), 빠진 번호 — 본문 속 ①② 언급은 건너뛴다."""
    fc = flat(item)
    idx = [i for i, c in enumerate(fc) if c[0] in CIRC]
    if not idx:
        return fc, None, []
    found, end = {}, len(fc)
    for k in range(4, -1, -1):
        cands = [i for i in idx if fc[i][0] == CIRC[k] and i < end]
        if cands:
            found[k] = cands[-1]
            end = cands[-1]
    have = sorted(found)
    missing = [CIRC[k] for k in range(5) if k not in found]
    if len(have) < 2:
        return fc, None, missing
    return fc, (have, [found[k] for k in have]), missing


def choice_texts(fc, have, pos):
    out = []
    for j, (k, p) in enumerate(zip(have, pos)):
        q = pos[j + 1] if j + 1 < len(pos) else len(fc)
        seg = fc[p + 1:q]
        txt = re.sub(r"\s+", " ", "".join(c[0] for c in seg)).strip()
        txt = re.sub(r"(?<=\d) ?\. ?(?=\d)", ".", re.sub(r" ([.,?!)])", r"\1", txt))  # 글자 층의 「19 .6」 → 「19.6」
        ink = [c for c in seg if c[0].strip()]
        by_line = {}  # 인쇄된 길이(mm): 줄마다 처음 글자 왼쪽 ~ 마지막 글자 오른쪽
        for c in ink:
            a = by_line.setdefault(c[1], [c[2], c[3]])
            a[0], a[1] = min(a[0], c[2]), max(a[1], c[3])
        width = sum(b - a for a, b in by_line.values()) * MM
        cells = 1 + sum(1 for a, b in zip(ink, ink[1:]) if a[1] == b[1] and (b[2] - a[3]) * MM > 4.0)
        out.append({"k": k, "text": txt, "chars": len(re.sub(r"\s", "", txt)), "mm": round(width, 1),
                    "cells": cells, "cy": fc[p][4], "line": fc[p][1]})
    return out


def combo(t):
    toks = [x.strip() for x in re.split(r"\s*,\s*", t.strip()) if x.strip()]
    if not toks:
        return None
    if all(len(x) == 1 and x in JAMO for x in toks):
        return "jamo", [JAMO.index(x) for x in toks]
    if all(re.fullmatch(r"\(\s*[가-사]\s*\)", x) for x in toks):
        return "gana", [GANA.index(re.sub(r"[\s()]", "", x)) for x in toks]
    if all(re.fullmatch(r"[A-F]", x) for x in toks):
        return "abc", [ord(x) - 65 for x in toks]
    return None


def number(t):
    m = re.fullmatch(r"([-+]?\d+(?:\.\d+)?)\s*([^\d\s]{0,6})", re.sub(r"(?<=\d)\s*([.,])\s*(?=\d)", r"\1", t).replace(",", ""))
    return (float(m.group(1)), m.group(2)) if m else None


def name(kind, ix):
    return ", ".join({"jamo": JAMO, "gana": [f"({g})" for g in GANA], "abc": "ABCDEF"}[kind][i] for i in ix)


# ---------- 점검 ----------

def check(pdf: Path, answers: dict | None = None) -> dict:
    lines = read_lines(pdf)
    intro, items, notes = split_items(lines)
    F = [{"level": lv, "q": q, "kind": kind, "msg": msg} for lv, q, kind, msg in notes]

    def add(level, q, kind, msg):
        F.append({"level": level, "q": q, "kind": kind, "msg": msg})

    if not items:
        return {"ok": False, "why": "문항을 찾지 못했다(글자 층이 없는 PDF 이거나 「1.」 꼴 번호가 아님)", "findings": [],
                "stats": {}}

    stats = {"items": len([i for i in items if not i["essay"]]), "essays": len([i for i in items if i["essay"]])}
    intro_t = re.sub(r"\s+", "", " ".join(ln["text"] for ln in intro))
    m = re.search(r"총\(?(\d+)\)?문항", intro_t)
    if m:
        total = int(m.group(1))
        stats["total_said"] = total
        if total != len(items):
            add("확인", "", "문항 수", f"배점안내는 총 {total}문항인데 찾은 문항은 {len(items)}개"
                + (f"(선택형 {stats['items']} · 서답형 {stats['essays']})" if stats["essays"] else ""))

    body_gaps, choice_rows = [], []
    pts = {}
    for it in items:
        q = it["q"]
        lns = it["lines"]
        # 배치: 단·쪽 걸침
        spots = []
        for ln in lns:
            s = (ln["page"], ln["col"])
            if s not in spots:
                spots.append(s)
        if len(spots) > 1:
            first = next(ln for ln in lns if (ln["page"], ln["col"]) == spots[0])
            nxt = next(ln for ln in lns if (ln["page"], ln["col"]) == spots[1])
            add("확인", q, "배치", f"문항이 {where(first)}에서 {where(nxt)}으로 넘어간다")
        for ln in lns:
            if re.fullmatch(r"\[\s*\d+(?:\s*\.\s*\d+)?\s*점\s*\]", ln["text"]):
                add("확인", q, "배치", f"「{re.sub(chr(32), '', ln['text'])}」만 혼자 한 줄에 남았다({where(ln)})")
        p = PTS_RE.findall(" ".join(ln["text"] for ln in lns))
        if p:
            pts[q] = float(re.sub(r"\s", "", p[0]))
        if it["essay"]:
            continue

        fc, ch, missing = choices(it)
        if missing and ch is not None:
            add("고칠 것", q, "보기 번호", f"{''.join(missing)} 이(가) 없다")
        if ch is None:
            if any(c[0] in CIRC for c in fc):
                add("고칠 것", q, "보기 번호", "①~⑤ 가 차례대로 나오지 않는다")
            else:
                add("확인", q, "보기 번호", "①~⑤ 를 찾지 못했다(선택형이 아니면 무시)")
            continue
        have, pos = ch
        cs = choice_texts(fc, have, pos)
        stem = "".join(c[0] for c in fc[:pos[0]])
        table = len(cs) >= 2 and len({c["cells"] for c in cs}) == 1 and cs[0]["cells"] >= 2

        # <보기> ㄱ·ㄴ·ㄷ 와 (가)·(나)·(다)
        labels = {}
        # ㄱ. ㄴ. 은 글 어디서나(점이 붙으면 머리 기호), (가)(나) 는 줄 머리에 올 때만 머리 기호로 본다(「(가)에서」 같은 언급은 뺌)
        heads = " ".join(ln["text"][:6] for ln in it["lines"][:cs[0]["line"] + 1])
        for kind, rx, src, alpha in (("jamo", r"(?<![가-힣ㄱ-ㅎA-Za-z])([ㄱ-ㅇ])\s*\.", stem, JAMO),
                                     ("gana", r"(?:^|\s)\(\s*([가-사])\s*\)", heads, GANA)):
            seen = []
            for mm in re.finditer(rx, src):
                if mm.group(1) in alpha and mm.group(1) not in seen:
                    seen.append(mm.group(1))
            labels[kind] = seen
            if len(seen) >= 2:
                want = list(alpha[:len(seen)])
                if seen != want:
                    fmt = (lambda xs: "·".join(xs)) if kind == "jamo" else (lambda xs: "·".join(f"({x})" for x in xs))
                    add("고칠 것", q, "기호 순서", f"{'<보기>' if kind == 'jamo' else '자료'} 기호가 {fmt(seen)} 차례로 나온다"
                        f"({fmt(want)} 차례여야 함)")

        # 선지 배열
        kinds = [combo(c["text"]) for c in cs]
        if len(cs) == 5 and all(kinds) and len({k[0] for k in kinds}) == 1:
            kind = kinds[0][0]
            sets = [k[1] for k in kinds]
            for c, s in zip(cs, sets):
                if s != sorted(s) or len(set(s)) != len(s):
                    add("확인", q, "선지 배열", f"{CIRC[c['k']]} 「{c['text']}」 안의 기호가 차례대로가 아니다")
            canon = sorted(sets, key=lambda s: (len(s), sorted(s)))
            if [sorted(s) for s in sets] != [sorted(s) for s in canon]:
                add("확인", q, "선지 배열", "합답형 선지가 관례 순서(개수가 적은 것부터, 같은 개수는 ㄱ→ㄴ→ㄷ)가 아니다: "
                    + " / ".join(name(kind, s) for s in sets))
            if len({tuple(sorted(s)) for s in sets}) < 5:
                add("고칠 것", q, "선지 배열", "같은 조합의 선지가 있다: " + " / ".join(name(kind, s) for s in sets))
            used = {i for s in sets for i in s}
            src = labels.get(kind)
            if src:
                alpha = JAMO if kind == "jamo" else GANA
                ghost = sorted(i for i in used if alpha[i] not in src)
                if ghost:
                    add("고칠 것", q, "선지 기호", f"선지에 쓴 {name(kind, ghost)} 이(가) 문항 안에 없다")
        elif len(cs) == 5 and all(number(c["text"]) for c in cs) and len({number(c["text"])[1] for c in cs}) == 1:
            vals = [number(c["text"])[0] for c in cs]
            if vals != sorted(vals):
                desc = vals == sorted(vals, reverse=True)
                add("확인", q, "선지 배열", "수치 선지가 " + ("큰 값부터다(작은 값부터 권장)" if desc else "크기 순서가 아니다")
                    + ": " + " / ".join(c["text"] for c in cs))
            if len(set(vals)) < len(vals):
                add("고칠 것", q, "선지 배열", "같은 값의 선지가 있다: " + " / ".join(c["text"] for c in cs))
        elif len(cs) == 5:
            if len({re.sub(r"\s", "", c["text"]) for c in cs}) < 5:
                add("고칠 것", q, "선지 배열", "같은 글의 선지가 있다")
            # 표 꼴 선지(칸마다 값: ㉠ ㉡ ㉢ 짝 고르기)와 낱말 선지(6자 이하)는 길이 순서를 보지 않는다
            if not table and max(c["chars"] for c in cs) > 6:
                bad = []
                for a, b in zip(cs, cs[1:]):
                    tol = max(1.5, 0.08 * a["mm"])
                    if b["mm"] < a["mm"] - tol:
                        bad.append(f"{CIRC[a['k']]}({a['chars']}자·{a['mm']:.0f}mm) → "
                                   f"{CIRC[b['k']]}({b['chars']}자·{b['mm']:.0f}mm)")
                if len(bad) >= 3:
                    add("확인", q, "선지 길이", "선지가 아래로 갈수록 짧아진다: "
                        + " ".join(f"{CIRC[c['k']]}{c['chars']}자" for c in cs)
                        + " — 짧은 선지부터 놓는 관례(내용상 순서가 있으면 그대로 둔다)")
                elif bad:
                    add("확인", q, "선지 길이", "아래로 갈수록 짧아지는 곳: " + ", ".join(bad)
                        + " — 짧은 선지부터 놓는 관례(내용상 순서가 있으면 그대로 둔다)")

        # 줄 간격: 선지 줄끼리, 본문 줄끼리
        rows = []
        for c in cs:
            if not rows or abs(c["cy"] - rows[-1]) > 1.0 / MM:
                rows.append(c["cy"])
        gaps = [(b - a) * MM for a, b in zip(rows, rows[1:]) if 0 < (b - a) * MM < 15]
        if gaps and not table:  # 표 꼴 선지는 표 줄 높이라 따로 둔다
            choice_rows.append((q, min(gaps)))
        sl = it["lines"][:cs[0]["line"]]
        for a, b in zip(sl, sl[1:]):
            g = (b["cy"] - a["cy"]) * MM
            if (a["page"], a["col"]) == (b["page"], b["col"]) and 0.6 * a["h"] * MM < g < 1.6 * a["h"] * MM + 2:
                body_gaps.append(g)

    if body_gaps and choice_rows:
        body = statistics.median(body_gaps)
        ch_med = statistics.median(g for _, g in choice_rows)
        stats["body_line_mm"] = round(body, 2)
        stats["choice_line_mm"] = round(ch_med, 2)
        narrow = [(q, g) for q, g in choice_rows if g < body - 0.6]
        if narrow and len(narrow) >= len(choice_rows) * 0.5:
            add("확인", "", "선지 줄 간격", f"선지 줄 간격(가운데값 {ch_med:.1f}mm)이 본문 줄 간격({body:.1f}mm)보다 좁다 — "
                + ", ".join(q + "번" for q, _ in narrow[:12]) + (" 등" if len(narrow) > 12 else ""))
            ref = ch_med
        else:
            for q, g in narrow:
                add("확인", q, "선지 줄 간격", f"선지 줄 간격 {g:.1f}mm — 본문({body:.1f}mm)보다 좁다")
            ref = None
        if ref is None:
            for q, g in choice_rows:
                if abs(g - ch_med) > 1.2 and (q, g) not in narrow:
                    add("확인", q, "선지 줄 간격", f"선지 줄 간격 {g:.1f}mm — 다른 문항(가운데값 {ch_med:.1f}mm)과 다르다")

    if pts:
        stats["points_sum"] = round(sum(pts.values()), 2)
        no = [it["q"] for it in items if it["q"] not in pts]
        if no:
            add("참고", "", "배점", "배점 표시를 찾지 못한 문항: " + ", ".join(q + "번" for q in no))
        elif abs(sum(pts.values()) - 100) > 0.01:
            add("확인", "", "배점", f"시험지에 적힌 배점 합계가 {stats['points_sum']:g}점이다(100점이 아님)")

    if answers:
        nums = []
        for it in items:
            if it["essay"]:
                continue
            v = str(answers.get(it["q"], ""))
            d = next((CIRC.index(x) + 1 for x in v if x in CIRC), None) or (int(v) if v.strip().isdigit() else None)
            nums.append(d)
        cnt = {k: nums.count(k) for k in range(1, 6)}
        stats["answer_count"] = cnt
        n = sum(cnt.values())
        if n >= 10:
            lo, hi = min(cnt.values()), max(cnt.values())
            if hi - lo > max(2, n // 5):
                add("참고", "", "정답 분포", "정답 번호가 고르지 않다: "
                    + " · ".join(f"{CIRC[k - 1]} {v}개" for k, v in cnt.items()))
        run = 1
        sel = [it for it in items if not it["essay"]]
        for i in range(1, len(nums)):
            run = run + 1 if nums[i] and nums[i] == nums[i - 1] else 1
            if run == 3:
                add("참고", sel[i]["q"], "정답 분포", f"정답이 {CIRC[nums[i] - 1]} 로 세 문항 이상 이어진다")

    order = {lv: i for i, lv in enumerate(LEVELS)}
    F.sort(key=lambda f: (order[f["level"]],
                          int(re.sub(r"\D", "", f["q"].split("~")[0]) or 0) + (100 if f["q"].startswith("서") else 0)))
    return {"ok": True, "findings": F, "stats": stats}


def text(res) -> str:
    if not res.get("ok"):
        return "양식 점검: " + res.get("why", "실패")
    s = res["stats"]
    head = f"양식 점검: 선택형 {s.get('items', 0)}문항" + (f" · 서답형 {s['essays']}" if s.get("essays") else "")
    if "body_line_mm" in s:
        head += f" · 줄 간격 본문 {s['body_line_mm']}mm / 선지 {s['choice_line_mm']}mm"
    if "points_sum" in s:
        head += f" · 배점 합 {s['points_sum']:g}"
    out = [head]
    for f in res["findings"]:
        out.append(f"  [{f['level']}] {f['q'] + '번 ' if f['q'] else ''}{f['kind']}: {f['msg']}")
    if not res["findings"]:
        out.append("  걸린 것 없음")
    return "\n".join(out)


if __name__ == "__main__":
    ans = None
    if len(sys.argv) > 2:
        ans = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")).get("answers")
    print(text(check(Path(sys.argv[1]), ans)))
