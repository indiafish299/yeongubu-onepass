"""검증 준비를 쉽게: 한글 → PDF, 가릴 칸 자동 찾기, 정답·배점표에서 정답 읽기, 한도·시간 어림."""
import sys

sys.dont_write_bytecode = True
import glob
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

# ---------- 한글 → PDF ----------


def hwp_to_pdf(src: Path, dst: Path) -> None:
    """윈도우 한글 자동화로 숨은 채 PDF 로 저장한다(창을 앞으로 띄우지 않는다).
    클라우드 동기화 폴더의 원본을 직접 열면 숨은 대화상자로 멈출 수 있어 임시 사본으로 연다.
    원안의 형광펜(정답 표시)은 PDF 에 찍힌다 → prepare 가 노란색을 지운다."""
    if os.name != "nt":
        sys.exit("한글 → PDF 자동 변환은 윈도우(한글 설치) 전용이다. 맥은 tools/hwp2pdf.sh 또는 한글에서 직접 PDF 저장.")
    import win32com.client as w

    tmp = Path(tempfile.mkdtemp(prefix="exam_hwp_"))
    try:
        copy = tmp / ("src" + src.suffix.lower())
        shutil.copyfile(src, copy)
        out = tmp / "out.pdf"
        hwp = w.gencache.EnsureDispatch("HWPFrame.HwpObject")
        try:
            hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
        except Exception:
            pass
        hwp.SetMessageBoxMode(0x00020000 | 0x00000010 | 0x00000100)
        try:
            if not hwp.Open(os.path.normpath(str(copy)), "", "forceopen:true"):
                sys.exit("한글이 파일을 열지 못했다")
            pages = hwp.PageCount
            if not hwp.SaveAs(os.path.normpath(str(out)), "PDF", ""):
                sys.exit("한글이 PDF 로 저장하지 못했다")
            hwp.Clear(1)
        finally:
            hwp.Quit()
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out, dst)
        print(f"PDF {pages}쪽: {dst}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------- 가릴 칸 자동 찾기 ----------

SCHOOL = re.compile(r"[가-힣]{2,}(?:고등학교|중학교|초등학교|학교)")
KEYS = ("저작권", "출제자", "결재", "실시일자", "(인)", "교감", "교장", "부장")


def _lines(page):
    """쪽의 글자를 줄로 묶는다: [(위 y, 아래 y, 글)] (0~1, 위에서부터)."""
    W, H = page.get_size()
    tp = page.get_textpage()
    chars = []
    for i in range(tp.count_chars()):
        ch = tp.get_text_range(i, 1)
        if not ch.strip():
            continue
        l, b, r, t = tp.get_charbox(i)
        chars.append((1 - t / H, 1 - b / H, l / W, ch))
    chars.sort(key=lambda c: (c[0] + c[1]) / 2)
    groups = []  # 세로 위치가 가까운 글자끼리 한 줄
    for c in chars:
        cy = (c[0] + c[1]) / 2
        if groups and abs(cy - groups[-1][0]) < 0.006:
            groups[-1][1].append(c)
        else:
            groups.append([cy, [c]])
    lines = []
    for _, cs in groups:
        cs.sort(key=lambda c: c[2])  # 줄 안은 왼쪽부터
        lines.append([min(c[0] for c in cs), max(c[1] for c in cs), "".join(c[3] for c in cs)])
    return lines


def auto_masks(pdf: Path, names=()) -> list:
    """학교명·출제자·시행일·결재란·저작권 줄을 찾아 가릴 상자 목록("쪽:x0,y0,x1,y1")을 만든다.
    1쪽 머리 표는 첫 문항(또는 <배점안내>) 위를 통째로, 쪽 아래의 학교명·저작권 줄은 그 줄부터 쪽 끝까지 가린다.
    글자 층이 없으면(스캔본) 빈 목록 — 그때는 손으로 정한다."""
    import pypdfium2 as pdfium

    names = [n for n in names if n]
    def hit(t):
        t = t.replace(" ", "")
        return bool(SCHOOL.search(t)) or any(k in t for k in KEYS) or any(n.replace(" ", "") in t for n in names)

    out = []
    doc = pdfium.PdfDocument(str(pdf))
    try:
        for n, page in enumerate(doc, 1):
            lines = _lines(page)
            if not lines:
                continue
            # 머리 표가 끝나는 곳 = 처음 나오는 <배점안내> 또는 문항 번호(두 단이면 오른쪽 단 문항이 먼저일 수 있다)
            start = next((l for l in lines if re.match(r"^(<배점안내>|\d{1,2}\.)", l[2].replace(" ", ""))), None)
            top_cut = start[0] - 0.012 if start else None
            if top_cut and any(hit(l[2]) for l in lines if l[1] <= top_cut + 0.012):
                out.append(f"{n}:0.04,{max(0.0, lines[0][0] - 0.02):.3f},0.96,{top_cut:.3f}")
            for y0, y1, t in lines:
                if not hit(t) or (top_cut and y1 <= top_cut + 0.012):
                    continue
                if y0 > 0.85:  # 쪽 아래(꼬리말·저작권): 그 줄부터 쪽 끝까지
                    out.append(f"{n}:0.04,{y0 - 0.008:.3f},0.96,0.997")
                    break
                out.append(f"{n}:0.04,{y0 - 0.006:.3f},0.96,{y1 + 0.006:.3f}")
    finally:
        doc.close()
    return out


def leftovers(text: str, names=()) -> list:
    """가린 뒤 글자 층에 남은 학교명·이름(있으면 사람이 다시 본다)."""
    found = set(SCHOOL.findall(text.replace(" ", "")))
    found |= {n for n in names if n and n.replace(" ", "") in text.replace(" ", "")}
    return sorted(found)


# ---------- 정답·배점표 → 정답표 ----------

CIRC = "①②③④⑤"


def parse_answer_md(md: str) -> dict:
    """exam-paper 의 「정답_배점표.md」에서 정답과 범위를 읽는다.
    표 머리 칸이 문항 번호(1, 2, … / 서답1)이고 바로 아래 줄에 정답이 있는 표를 쓴다."""
    rows = [l for l in md.splitlines()]
    answers = {}
    i = 0
    while i < len(rows):
        if rows[i].lstrip().startswith("|"):
            block = []
            while i < len(rows) and rows[i].lstrip().startswith("|"):
                block.append([c.strip() for c in rows[i].strip().strip("|").split("|")])
                i += 1
            body = [r for r in block if not all(re.fullmatch(r":?-{2,}:?", c or "-") for c in r)]
            if len(body) >= 2 and all(re.fullmatch(r"(\d+|서답형?\s*\d+)", c) for c in body[0] if c):
                for q, a in zip(body[0], body[1]):
                    if q and a:
                        answers.setdefault(re.sub(r"\s", "", q), a)
        else:
            i += 1
    scope = ""
    m = re.search(r"\*\*범위:\*\*\s*(.+)", md)
    if m:
        scope = m.group(1).strip()
    title = (re.search(r"^#\s+(.+)$", md, flags=re.M) or [None, ""])[1]
    return {"answers": answers, "scope": scope, "title": title}


# ---------- 한도·시간 어림 ----------


def estimate(n_models: int, scope: bool, text: bool, rubric: bool, vendors: int) -> dict:
    per = 2 + int(scope) + int(text) + int(rubric)          # 풀이·흠잡기 (+범위·교정·채점 기준)
    calls = per * n_models + max(1, min(vendors, n_models))  # + 반박
    return {"calls": calls, "per_model": per, "minutes": "30~60"}


def codex_usage() -> str:
    """codex 의 최근 실행 기록에서 남은 한도(쓴 %)를 읽는다. 기록이 없으면 빈 글."""
    files = sorted(glob.glob(str(Path.home() / ".codex/sessions/**/*.jsonl"), recursive=True), key=os.path.getmtime)
    for f in reversed(files[-5:]):
        try:
            for line in reversed(Path(f).read_text(encoding="utf-8", errors="replace").splitlines()):
                if '"rate_limits"' in line:
                    rl = json.loads(line)
                    rl = rl.get("payload", rl).get("rate_limits") or rl.get("rate_limits") or {}
                    parts = []
                    for k, lab in (("primary", "5시간"), ("secondary", "주간")):
                        if isinstance(rl.get(k), dict) and "used_percent" in rl[k]:
                            parts.append(f"{lab} {100 - float(rl[k]['used_percent']):.0f}% 남음")
                    if parts:
                        return ", ".join(parts)
        except Exception:
            continue
    return ""


def agy_usage(agy: list) -> str:
    try:
        p = subprocess.run(agy + ["-p", "/usage", "--print-timeout", "1m"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=90, stdin=subprocess.DEVNULL)
    except Exception:
        return ""
    out = []
    for line in p.stdout.splitlines():
        c = line.split("\t")
        if len(c) >= 3 and c[0].startswith("Gemini") and "Remaining" in c[1]:
            out.append(f"{'주간' if 'Weekly' in c[1] else '5시간'} {c[2]} 남음")
    return ", ".join(out)
