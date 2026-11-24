"""시험지 검증 파이프라인.

  prepare  PDF → 쪽 이미지, 머리 칸 가리기            (모델에 아무것도 안 보냄)
  approve  가린 이미지를 사람이 본 뒤 「보내도 됨」 표시
  run      네 모델: 풀이 → 흠잡기 → 범위 → 반박 → 채점 기준, 정답 대조, 보고서
  purge    그 시험의 결과와 남은 대화 기록 지우기      (--yes 필요)

결과는 이 PC 로컬(home.WORK, 기본 ~/.exam-tools/work/<이름>/)에만 둔다.
"""
import os
import sys

sys.dont_write_bytecode = True
# 윈도우: 파일·모델 출력의 한글이 cp949 로 깨지지 않게 UTF-8 모드로 다시 띄운다($env:PYTHONUTF8=1 과 같음).
if os.name == "nt" and not sys.flags.utf8_mode:
    import subprocess as _sp
    sys.exit(_sp.call([sys.executable, "-X", "utf8", *sys.orig_argv[1:]]))
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exam_verify import home, prompts, report, runners  # noqa: E402
from exam_verify.pages import pdf_to_pages  # noqa: E402

ROOT = home.WORK
CIRCLED = {"①": "1", "②": "2", "③": "3", "④": "4", "⑤": "5"}


def wd(name: str) -> Path:
    if not re.fullmatch(r"[\w가-힣.\-]+", name) or name.startswith("_"):
        sys.exit("이름은 한글·영문·숫자·-·_ 만 쓰고 _ 로 시작하지 않는다")
    return ROOT / name


def box_hash(box: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(box.glob("page-*.png")):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


# ---------- prepare / approve ----------

def cmd_prepare(a):
    from PIL import Image, ImageDraw

    d = wd(a.name)
    raw, box = d / "raw", d / "box"
    for old in list(raw.glob("page-*.png")) + list(box.glob("page-*.png")):
        old.unlink()
    (d / "APPROVED").unlink(missing_ok=True)
    pages = pdf_to_pages(Path(a.pdf).expanduser(), raw, dpi=a.dpi)
    box.mkdir(parents=True, exist_ok=True)
    if not a.mask and not a.no_auto_mask:
        from exam_verify import autoprep
        a.mask = autoprep.auto_masks(Path(a.pdf).expanduser(), home.load_profile().get("names", []))
        print("가릴 칸 자동: " + (" ".join(a.mask) if a.mask else "찾지 못함(글자 층 없음?) — --mask 로 손으로 정한다"))
    masks = parse_masks(a.mask)
    from PIL import ImageChops

    yellow_pages = []
    for i, p in enumerate(pages, 1):
        im = Image.open(p).convert("RGB")
        W, H = im.size
        # 원안의 정답 형광 표시(노란 바탕)는 정답 누출이다. 흰색으로 지우고 몇 쪽에 있었는지 알린다.
        r, g, b = im.split()
        # 노란 바탕 위 글자의 가장자리는 (k,k,0) 꼴로 남는다. 파랑이 빨강·초록보다 뚜렷이 낮은 곳을
        # 빨강 값의 회색으로 바꾸면 바탕은 흰색, 글자는 검정으로 돌아온다.
        # 빨강≈초록(노랑 계열)일 때만 손댄다. 갈색·주황 그림은 건드리지 않는다.
        ym = ImageChops.multiply(ImageChops.subtract(r, b).point(lambda v: 255 if v > 12 else 0),
                                 ImageChops.subtract(g, b).point(lambda v: 255 if v > 12 else 0))
        ym = ImageChops.multiply(ym, ImageChops.difference(r, g).point(lambda v: 255 if v < 30 else 0))
        if ym.getbbox():
            yellow_pages.append(i)
            if not a.keep_yellow:
                im.paste(Image.merge("RGB", (r, r, r)), mask=ym)
        dr = ImageDraw.Draw(im)
        for x0, y0, x1, y1 in masks.get(i, []):
            dr.rectangle((x0 * W, y0 * H, x1 * W, y1 * H), fill="white", outline="#999999", width=2)
        im.save(box / p.name)
    (d / "meta.json").write_text(json.dumps(
        {"pdf": str(a.pdf), "pages": len(pages), "masks": a.mask or [], "prepared": time.strftime("%F %T")},
        ensure_ascii=False, indent=1))
    print(f"{len(pages)}쪽 준비됨: {box}")
    if write_text(d, a.pdf, a.mask):
        print(f"글자 층(교정 단계용): {d / 'text.txt'} — 가린 칸의 글자가 빠졌는지 같이 확인할 것")
        from exam_verify import autoprep
        left = autoprep.leftovers((d / "text.txt").read_text(), home.load_profile().get("names", []))
        if left:
            print(f"⚠ 가린 뒤에도 글자 층에 남은 이름: {', '.join(left)} — 상자를 더 잡거나 시험 내용인지 확인할 것")
    else:
        print("이 PDF 에는 글자 층이 없다. 교정(오탈자) 단계는 건너뛴다.")
    if yellow_pages:
        print(f"⚠ 노란 형광 표시가 {yellow_pages}쪽에 있었다(정답 표시로 보임). "
              + ("그대로 뒀다." if a.keep_yellow else "흰색으로 지웠다. 지워졌는지 눈으로 확인할 것."))
    print("가린 이미지를 선생님이 확인한 뒤 approve 를 돌린다. 그 전에는 run 이 거부한다.")


def text_hash(d: Path) -> str:
    f = d / "text.txt"
    return hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() and f.read_text().strip() else ""


def parse_masks(items) -> dict:
    masks = {}
    for m in items or []:
        pg, rect = m.split(":")
        masks.setdefault(int(pg), []).append([float(x) for x in rect.split(",")])
    return masks


def write_text(d: Path, pdf, mask_items) -> bool:
    """교정 단계에 보낼 글자 층(가린 칸의 글자는 뺌)을 text.txt 로. 글자 층이 없으면 파일을 지운다."""
    from pages import pdf_text
    t = pdf_text(Path(pdf).expanduser(), parse_masks(mask_items))
    f = d / "text.txt"
    if t:
        f.write_text(t)
    else:
        f.unlink(missing_ok=True)
    return bool(t)


def cmd_text(a):
    """이미 prepare 한 시험지에 글자 층만 다시 뽑는다(이미지와 그 승인은 그대로)."""
    d = wd(a.name)
    meta = json.loads((d / "meta.json").read_text())
    ok = write_text(d, meta["pdf"], meta["masks"])
    print(f"글자 층: {d / 'text.txt'}" if ok else "이 PDF 에는 글자 층이 없다(교정 단계는 건너뛴다)")
    if ok:
        print("가린 칸의 글자가 빠졌는지 선생님이 확인한 뒤 approve 를 돌린다. 그 전에는 교정 단계가 돌지 않는다.")


def cmd_approve(a):
    d = wd(a.name)
    (d / "APPROVED").write_text(box_hash(d / "box") + "\n" + text_hash(d))
    print("보내도 됨 표시함:", d / "APPROVED", "(이미지" + (" + 글자 층)" if text_hash(d) else "만. 글자 층 없음)"))


def cmd_pdf(a):
    from exam_verify import autoprep
    autoprep.hwp_to_pdf(Path(a.hwp).expanduser(), Path(a.out).expanduser())


def cmd_answers(a):
    """정답·배점표(md)에서 정답표를 읽어 answers.json 에 쓴다. 사람이 확인한 뒤 --confirm 으로 확정."""
    from exam_verify import autoprep
    d = wd(a.name)
    f = d / "answers.json"
    if a.confirm:
        kd = json.loads(f.read_text())
        kd["confirmed"] = True
        f.write_text(json.dumps(kd, ensure_ascii=False, indent=1))
        print(f"정답표 확정: {len(kd['answers'])}문항 ({f})")
        return
    if not a.md:
        sys.exit("정답·배점표 md 파일을 준다: answers <이름> <정답_배점표.md>")
    r = autoprep.parse_answer_md(Path(a.md).expanduser().read_text(encoding="utf-8"))
    if not r["answers"]:
        sys.exit("정답 표를 찾지 못했다(머리 칸이 문항 번호, 바로 아래 줄이 정답인 표가 필요)")
    d.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"confirmed": False, "answers": r["answers"]}, ensure_ascii=False, indent=1))
    if r["scope"] and not (d / "scope.txt").exists():
        (d / "scope.txt").write_text(r["scope"])
    qs = sorted(r["answers"], key=qkey)
    print(f"{r['title']}\n정답 {len(qs)}문항 — 선생님이 눈으로 확인한 뒤에만 --confirm")
    for i in range(0, len(qs), 10):
        print("  " + "  ".join(f"{q}:{r['answers'][q]}" for q in qs[i:i + 10]))
    if r["scope"]:
        print(f"범위(run 에 그대로 씀, scope.txt): {r['scope']}")


def cmd_plan(a):
    """돌리기 전에: 검토자·호출 수·걸리는 시간·남은 한도."""
    from exam_verify import autoprep
    d = wd(a.name)
    models = a.models.split(",")
    scope = (d / "scope.txt").exists()
    est = autoprep.estimate(len(models), scope, bool(text_hash(d)), bool(a.rubric),
                            len({runners.vendor(m) for m in models}))
    print("검토자: " + ", ".join(f"{runners.LABEL[m]}({runners.MODELS[m][2]})" for m in models))
    print(f"호출 약 {est['calls']}번(모델마다 {est['per_model']}단계 + 반박), 걸리는 시간 약 {est['minutes']}분")
    if any(runners.MODELS[m][1] == "codex" for m in models):
        print("ChatGPT(codex) 한도: " + (autoprep.codex_usage() or "기록 없음(한 번 돌린 뒤 보인다)"))
    if any(runners.MODELS[m][1] == "agy" for m in models):
        print("Gemini(agy) 한도: " + (autoprep.agy_usage(runners._bin("agy")) or "읽지 못함"))
    if any(runners.MODELS[m][1] == "claude" for m in models):
        print("Claude 한도: Claude 앱의 사용량 화면(또는 get_usage)에서 본다")


# ---------- 파싱·정규화 ----------

def parse_json(text: str) -> dict:
    blocks = re.findall(r"```json\s*(.*?)```", text, flags=re.S)
    cands = blocks[::-1]
    i, j = text.find("{"), text.rfind("}")
    if i >= 0 and j > i:
        cands.append(text[i:j + 1])
    for c in cands:
        try:
            o = json.loads(c)
            if isinstance(o, dict):
                return o
        except Exception:
            continue
    return {}


def norm_q(q) -> str:
    s = str(q).strip().rstrip(".번").replace(" ", "").strip("[]")
    # 모델마다 "서답1", "서답형1", "[서답형 1]" 로 달리 적는다. 한 꼴로 모은다.
    return re.sub(r"^(서답|서술|논술|단답)형?(\d+)$", r"\1\2", s)


def choice_set(ans) -> frozenset:
    """선택형 답을 번호 집합으로. 번호를 못 찾으면 빈 집합."""
    s = str(ans)
    for k, v in CIRCLED.items():
        s = s.replace(k, f" {v} ")
    if re.search(r"[①-⑤]", str(ans)):
        return frozenset(re.findall(r"\b[1-5]\b", s))
    if re.fullmatch(r"\s*[1-5](\s*[,/·]\s*[1-5])*\s*", s):
        return frozenset(re.findall(r"[1-5]", s))
    return frozenset()


def qkey(q: str):
    m = re.search(r"\d+", q)
    return (0 if re.fullmatch(r"\d+", q) else 1, int(m.group()) if m else 0, q)


# ---------- run ----------

def staged(d: Path, stage: str, key: str, prompt: str, box: Path, fast: bool, force=False) -> dict:
    """한 번 부르고 runs/ 에 저장. 이미 성공한 결과가 있으면 다시 부르지 않는다(빠진 모델만 이어 돌리기)."""
    f = d / "runs" / f"{stage}__{key}.json"
    # 재사용 열쇠: 프롬프트 + 쪽 이미지 + 추론 단계. 이미지를 다시 만들었거나 --fast 결과면 다시 부른다.
    sha = hashlib.sha256(f"{prompt}|{box_hash(box)}|{'fast' if fast else 'full'}".encode()).hexdigest()
    if f.exists() and not force:
        old = json.loads(f.read_text())
        if old.get("ok") and old.get("prompt_sha") == sha:
            return old
    r = runners.call(key, prompt, box, fast=fast)
    r["stage"] = stage
    r["prompt_sha"] = sha
    r["parsed"] = parse_json(r.get("text", "")) if r["ok"] else {}
    if r["ok"] and not r["parsed"]:
        r["ok"], r["error"] = False, "JSON 을 읽지 못함"
    r["at"] = time.strftime("%F %T")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(r, ensure_ascii=False, indent=1))
    print(f"  [{stage}] {runners.LABEL[key]}: {'됨' if r['ok'] else '실패 — ' + r['error'][:120]}", flush=True)
    return r


def cmd_run(a):
    d = wd(a.name)
    box = d / "box"
    pages = sorted(box.glob("page-*.png"))
    if not pages:
        sys.exit("먼저 prepare 를 돌린다")
    ok_file = d / "APPROVED"
    appr = ok_file.read_text().split("\n") if ok_file.exists() else [""]
    if appr[0].strip() != box_hash(box):
        sys.exit("거부: 가린 이미지에 대한 「보내도 됨」(approve)이 없거나 그 뒤 이미지가 바뀌었다")
    models = a.models.split(",")
    text = (d / "text.txt").read_text() if text_hash(d) else ""
    proof_skip = ""
    if not text:
        proof_skip = "교정(글자 층 없음)"
    elif len(appr) < 2 or appr[1].strip() != text_hash(d):
        text, proof_skip = "", "교정(글자 층 승인 없음)"
    if proof_skip:
        print(f"⚠ {proof_skip}: 오탈자 단계를 건너뛴다", flush=True)
    key = {}
    if not a.answers and (d / "answers.json").exists():
        a.answers = str(d / "answers.json")
    if not a.scope and (d / "scope.txt").exists():
        a.scope = (d / "scope.txt").read_text().strip()
    if a.answers:
        kd = json.loads(Path(a.answers).expanduser().read_text())
        if not kd.get("confirmed"):
            sys.exit('거부: 정답표에 "confirmed": true 가 없다(선생님 눈 확인 뒤에만 넣는다)')
        key = {norm_q(k): v for k, v in kd["answers"].items()}
    print(f"시험지 {len(pages)}쪽 · 모델 {', '.join(runners.LABEL[m] for m in models)}", flush=True)

    # 1) 모델마다 풀이 → 흠잡기 → 범위 (모델끼리는 동시에, 서로의 결과는 못 봄)
    def per_model(m):
        out = {"solve": staged(d, "solve", m, prompts.fill(prompts.SOLVE, pages), box, a.fast)}
        out["critique"] = staged(d, "critique", m, prompts.fill(prompts.CRITIQUE, pages), box, a.fast)
        if a.scope:
            out["scope"] = staged(d, "scope", m, prompts.fill(prompts.SCOPE, pages, scope=a.scope), box, a.fast)
        if text:
            out["proof"] = staged(d, "proof", m, prompts.fill(prompts.PROOF, pages, text=text), box, a.fast)
        return m, out

    with ThreadPoolExecutor(max_workers=len(models)) as ex:
        res = dict(ex.map(per_model, models))

    # 2) 지적 모으기
    issues, n = [], 0
    for m in models:
        for stage in ("critique", "scope"):
            r = res[m].get(stage)
            for it in (r or {}).get("parsed", {}).get("issues", []) if r and r["ok"] else []:
                n += 1
                issues.append({"id": f"i{n}", "by": m, "stage": stage, "q": norm_q(it.get("q", "?")),
                               "severity": str(it.get("severity", "C")).strip()[:1].upper(),
                               "claim": it.get("claim", ""), "evidence": it.get("evidence", ""),
                               "fix": it.get("fix", ""), "confidence": it.get("confidence", "")})
    alive = [m for m in models if res[m]["critique"]["ok"]]
    for it in issues:
        it["same_by"] = sorted({o["by"] for o in issues if (o["q"], o["severity"]) == (it["q"], it["severity"])})

    # 3) 반박: 같은 지적을 하지 않은 모델이 맡는다. 다른 회사 모델을 먼저 고르고(맡은 일이 적은 쪽),
    #    다른 회사가 없으면(예: Claude 요금제만) 같은 회사의 다른 모델이 맡는다. 모두 같은 지적이면 건너뛴다.
    if not a.no_rebut and len(alive) > 1:
        todo = {}
        for it in issues:
            if set(it["same_by"]) >= set(alive):
                it["verdict"], it["verdict_by"], it["verdict_reason"] = "skipped", "", "모든 모델이 같은 지적"
                continue
            cands = [c for c in alive if c not in it["same_by"]]
            cands.sort(key=lambda c: (runners.vendor(c) == runners.vendor(it["by"]), len(todo.get(c, [])),
                                      alive.index(c)))
            if cands:
                todo.setdefault(cands[0], []).append(it)

        def rebut(pair):
            m, its = pair
            claims = "\n".join(f"- [{i['id']}] {i['q']}번 ({prompts.SEVERITY.get(i['severity'], '')}): "
                               f"{i['claim']} / 근거: {i['evidence']}" for i in its)
            if a.scope and any(i["severity"] == "E" for i in its):  # 범위 밖 지적은 범위를 알아야 가릴 수 있다
                claims = f"(이 시험의 출제 범위: {a.scope})\n" + claims
            r = staged(d, "rebut", m, prompts.fill(prompts.REBUT, pages, claims=claims), box, a.fast)
            vs = {v.get("id"): v for v in r.get("parsed", {}).get("verdicts", [])} if r["ok"] else {}
            for i in its:
                v = vs.get(i["id"], {})
                i["verdict"], i["verdict_by"], i["verdict_reason"] = v.get("verdict", "none"), m, v.get("reason", "")

        with ThreadPoolExecutor(max_workers=4) as ex:
            list(ex.map(rebut, todo.items()))

    # 4) 채점 기준(서답형): 기준표는 이 단계에서만 보여 준다
    rubric_runs = {}
    if a.rubric:
        rub = Path(a.rubric).expanduser().read_text()
        blind = []
        for m in models:
            for x in res[m]["solve"].get("parsed", {}).get("answers", []) if res[m]["solve"]["ok"] else []:
                if not choice_set(x.get("answer", "")):
                    blind.append(f"- {norm_q(x.get('q'))}번 / 수험생 {models.index(m) + 1}: {x.get('answer')}")
        p = prompts.fill(prompts.RUBRIC, pages, rubric=rub, answers="\n".join(blind) or "(없음)")
        with ThreadPoolExecutor(max_workers=len(models)) as ex:
            rubric_runs = dict(zip(models, ex.map(lambda m: staged(d, "rubric", m, p, box, a.fast), models)))
        for m, r in rubric_runs.items():
            for it in r.get("parsed", {}).get("issues", []) if r["ok"] else []:
                n += 1
                issues.append({"id": f"i{n}", "by": m, "stage": "rubric", "q": norm_q(it.get("q", "?")),
                               "severity": "F", "claim": it.get("claim", ""), "evidence": it.get("evidence", ""),
                               "fix": it.get("fix", ""), "confidence": it.get("confidence", ""),
                               "same_by": [m], "verdict": "none", "verdict_by": "", "verdict_reason": ""})

    for it in issues:
        if it["stage"] == "rubric":
            it["same_by"] = sorted({o["by"] for o in issues if o["stage"] == "rubric" and o["q"] == it["q"]})

    # 4-2) 교정(오탈자): 글자 층을 한 글자씩 읽은 결과. 반박 단계는 거치지 않는다.
    proofs = []
    for m in models:
        r = res[m].get("proof")
        for it in (r or {}).get("parsed", {}).get("issues", []) if r and r["ok"] else []:
            n += 1
            proofs.append({"id": f"i{n}", "by": m, "stage": "proof", "q": norm_q(it.get("q", "?")), "severity": "D",
                           "claim": f"오탈자 의심: 「{it.get('quote', '')}」 → 「{it.get('fix', '')}」",
                           "evidence": it.get("why", ""), "fix": it.get("fix", ""), "quote": it.get("quote", ""),
                           "confidence": it.get("confidence", ""), "verdict": "none", "verdict_by": "",
                           "verdict_reason": ""})
    squash = lambda t: re.sub(r"\s+", "", t)
    for it in proofs:
        it["same_by"] = sorted({o["by"] for o in proofs if o["q"] == it["q"] and (
            squash(o["quote"]) in squash(it["quote"]) or squash(it["quote"]) in squash(o["quote"]))})
    issues += proofs

    # 5) 정답 대조(스크립트가 한다. 모델은 정답을 본 적이 없다)
    answers = {}
    for m in models:
        if res[m]["solve"]["ok"]:
            for x in res[m]["solve"]["parsed"].get("answers", []):
                answers.setdefault(norm_q(x.get("q", "?")), {})[m] = x
    qs = sorted(set(answers) | set(key) | {i["q"] for i in issues}, key=qkey)
    rows = []
    for q in qs:
        k = key.get(q)
        ks = choice_set(k) if k is not None else frozenset()
        per = {}
        for m in models:
            x = answers.get(q, {}).get(m)
            if x is None:
                continue
            s = choice_set(x.get("answer", ""))
            match = None if (k is None or not ks) else (s == ks)
            per[m] = {**x, "match": match}
        sets = {choice_set(x.get("answer", "")) or str(x.get("answer")) for x in per.values()}
        rows.append({"q": q, "key": k, "answers": per,
                     "mismatch": sorted(m for m, x in per.items() if x["match"] is False),
                     "disagree": len(sets) > 1,
                     "issues": [i for i in issues if i["q"] == q]})

    failed = sorted({f"{runners.LABEL[m]}({s})" for m in models for s, r in res[m].items() if not r["ok"]}
                    | {f"{runners.LABEL[m]}(rubric)" for m, r in rubric_runs.items() if not r["ok"]}
                    | ({proof_skip} if proof_skip else set()))
    prev = None
    if a.prev:
        pf = wd(a.prev) / "report.json"
        prev = json.loads(pf.read_text()) if pf.exists() else None
    data = {"name": a.name, "at": time.strftime("%F %T"), "pages": len(pages), "scope": a.scope or "",
            "models": models, "model_ids": {m: res[m]["solve"].get("model_reported") or res[m]["solve"].get("model_id")
                                            for m in models},
            "failed": failed, "has_key": bool(key), "fast": a.fast, "rows": rows,
            "page_hashes": [hashlib.sha256(p.read_bytes()).hexdigest()[:12] for p in pages]}
    report.mark_new(data, prev)
    (d / "report.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    (d / "report.html").write_text(report.render(data))
    print(f"\n보고서: {d / 'report.html'}")
    print(report.summary_line(data))
    if not a.quiet and sys.platform == "darwin":
        subprocess.run(["osascript", "-e", f'display notification "{a.name} 검증 끝남" with title "시험지 검증"'],
                       capture_output=True)


# ---------- purge ----------

def cmd_purge(a):
    d = wd(a.name)
    convs = []
    for f in (d / "runs").glob("*.json") if (d / "runs").exists() else []:
        cid = json.loads(f.read_text()).get("conversation_id")
        if cid:
            convs += list((Path.home() / ".gemini/antigravity-cli").rglob(f"{cid}*"))
    print("지울 것:", d, *convs, sep="\n  ")
    if not a.yes:
        print("(--yes 를 붙이면 지운다)")
        return
    for p in convs:
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    shutil.rmtree(d)
    print("지움")


def main():
    ap = argparse.ArgumentParser(prog="exam-verify")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare"); p.add_argument("name"); p.add_argument("pdf")
    p.add_argument("--mask", action="append", help="쪽:x0,y0,x1,y1 (0~1 비율), 여러 번 가능")
    p.add_argument("--keep-yellow", action="store_true", help="노란 형광 표시를 지우지 않는다")
    p.add_argument("--no-auto-mask", action="store_true", help="가릴 칸을 자동으로 찾지 않는다")
    p.add_argument("--dpi", type=int, default=200); p.set_defaults(fn=cmd_prepare)
    p = sub.add_parser("text"); p.add_argument("name"); p.set_defaults(fn=cmd_text)
    p = sub.add_parser("pdf", help="한글 원안 → PDF (윈도우, 숨은 채)"); p.add_argument("hwp"); p.add_argument("out")
    p.set_defaults(fn=cmd_pdf)
    p = sub.add_parser("answers", help="정답·배점표 md → answers.json (확인 뒤 --confirm)")
    p.add_argument("name"); p.add_argument("md", nargs="?"); p.add_argument("--confirm", action="store_true")
    p.set_defaults(fn=cmd_answers)
    p = sub.add_parser("plan", help="돌리기 전 검토자·호출 수·한도")
    p.add_argument("name"); p.add_argument("--models", default=",".join(runners.ACTIVE)); p.add_argument("--rubric")
    p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("approve"); p.add_argument("name"); p.set_defaults(fn=cmd_approve)
    p = sub.add_parser("run"); p.add_argument("name")
    p.add_argument("--answers"); p.add_argument("--rubric"); p.add_argument("--scope"); p.add_argument("--prev")
    p.add_argument("--models", default=",".join(runners.ACTIVE),
                   help="검토자(기본: exam-setup 이 profile.json 에 적은 목록)")
    p.add_argument("--fast", action="store_true", help="낮은 추론 단계(시험용)")
    p.add_argument("--no-rebut", action="store_true"); p.add_argument("--quiet", action="store_true")
    p.set_defaults(fn=cmd_run)
    p = sub.add_parser("purge"); p.add_argument("name"); p.add_argument("--yes", action="store_true")
    p.set_defaults(fn=cmd_purge)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
