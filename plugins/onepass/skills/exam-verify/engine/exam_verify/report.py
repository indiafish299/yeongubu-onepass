"""보고서: 사람이 다시 볼 의심 목록(통과 도장이 아니다)."""
import sys

sys.dont_write_bytecode = True
from html import escape as e

from exam_verify.prompts import SEVERITY
from exam_verify.runners import LABEL

WEIGHT = {"A": 50, "B": 40, "E": 30, "F": 30, "C": 20, "D": 10}
VERDICT = {"upheld": "반박 실패(지적 유지)", "refuted": "반박됨", "unsure": "가리지 못함",
           "skipped": "모든 모델이 같은 지적", "none": "반박 안 함", None: "반박 안 함"}


def score(row) -> int:
    s = 100 * len(row["mismatch"]) + (15 if row["disagree"] else 0)
    for i in row["issues"]:
        w = WEIGHT.get(i["severity"], 10) + 5 * len(i.get("same_by", []))
        s += w // 3 if i.get("verdict") == "refuted" else w
    return s


def mark_new(data, prev):
    """지난 실행과 견주어 새로 생긴 지적과 달라진 쪽을 표시한다."""
    data["prev"] = prev["name"] if prev else ""
    old = {(r["q"], i["severity"]) for r in prev["rows"] for i in r["issues"]} if prev else set()
    for r in data["rows"]:
        for i in r["issues"]:
            i["new"] = bool(prev) and (r["q"], i["severity"]) not in old
    def groups(d):
        g = {}
        for r in d["rows"] if d else []:
            for i in r["issues"]:
                x = g.setdefault((r["q"], i["severity"]), {"by": set(), "claim": i["claim"]})
                x["by"].add(i["by"])
        return g
    was_g, now_g = groups(prev), groups(data)
    data["issue_change"] = [
        {"q": q, "severity": sv, "was": len(was_g.get((q, sv), {"by": ()})["by"]),
         "now": len(now_g.get((q, sv), {"by": ()})["by"]), "claim": (was_g.get((q, sv)) or now_g[(q, sv)])["claim"]}
        for q, sv in sorted(set(was_g) | set(now_g))
        if prev and len(was_g.get((q, sv), {"by": ()})["by"]) != len(now_g.get((q, sv), {"by": ()})["by"])]
    was = {r["q"]: r["mismatch"] for r in prev["rows"]} if prev else {}
    data["mismatch_change"] = [{"q": r["q"], "was": was.get(r["q"], []), "now": r["mismatch"]}
                               for r in data["rows"] if prev and sorted(was.get(r["q"], [])) != sorted(r["mismatch"])]
    data["changed_pages"] = ([n + 1 for n, h in enumerate(data["page_hashes"])
                              if n >= len(prev["page_hashes"]) or prev["page_hashes"][n] != h] if prev else [])


def summary_line(data) -> str:
    rows = data["rows"]
    return (f"문항 {len(rows)}개 · 정답표와 어긋난 문항 {sum(1 for r in rows if r['mismatch'])}개 · "
            f"지적 {sum(len(r['issues']) for r in rows)}건"
            + (f" · 양식 {len(data['form']['findings'])}건" if data.get("form", {}).get("ok") else "")
            + (f" · ⚠ 빠진 실행: {', '.join(data['failed'])}" if data["failed"] else ""))


def plain(data) -> str:
    """보고서 맨 위의 쉬운 말 요약 세 줄(선생님이 먼저 읽는 곳)."""
    from exam_verify.runners import vendor
    rows, models = data["rows"], data["models"]
    n_v = len({vendor(m) for m in models})
    mism = [r["q"] for r in rows if r["mismatch"]]
    # 꼭 다시 볼 것: 복수 정답·조건 부족·범위 밖 지적 가운데 반박을 이겨 냈거나(유지·모두 같은 지적)
    # 두 모델 이상이 함께 짚은 것. 한 모델만 내고 가려지지 않은 지적은 「가볍게 볼」로.
    serious = [r["q"] for r in rows
               if any(i["severity"] in "ABE" and i.get("verdict") != "refuted"
                      and (i.get("verdict") in ("upheld", "skipped") or len(i.get("same_by", [])) >= 2)
                      for i in r["issues"])]
    other = [r["q"] for r in rows if r["issues"] and r["q"] not in serious]
    li = [f"검토자 {len(models)}명(회사 {n_v}곳)이 정답을 모른 채 직접 풀고 흠을 찾았습니다."
          + (" 빠진 실행이 있어 검증이 다 되지 않았습니다." if data["failed"] else "")
          + (" 한 회사 모델만 썼습니다. 다른 회사 AI 가 있으면 더 믿을 만합니다." if n_v == 1 else "")]
    if data["has_key"]:
        li.append("정답표와 다른 답이 나온 문항: " + (", ".join(f"{q}번" for q in mism) if mism else "없음"))
    li.append("꼭 다시 볼 문항(복수 정답·조건 부족·범위 밖 지적을 여러 모델이 함께 짚었거나 반박을 이겨 냄): "
              + (", ".join(f"{q}번" for q in serious) if serious else "없음")
              + (f" · 가볍게 볼 문항: {', '.join(q + '번' for q in other)}" if other else ""))
    fm = data.get("form") or {}
    if fm.get("ok"):
        fx = [f for f in fm["findings"] if f["level"] == "고칠 것"]
        ck = [f for f in fm["findings"] if f["level"] == "확인"]
        qs = lambda fs: ", ".join(dict.fromkeys(f["q"] + "번" for f in fs if f["q"])) or "문서 전체"
        li.append("양식 점검(스크립트): " + ("걸린 것 없음" if not fm["findings"] else
                  (f"고칠 것 {len(fx)}건({qs(fx)})" if fx else "고칠 것 없음")
                  + (f" · 확인할 것 {len(ck)}건({qs(ck)})" if ck else "")))
    return "<div class='card'><h3>한눈에</h3><ul>" + "".join(f"<li>{e(x)}</li>" for x in li) + "</ul></div>"


FORM_CLS = {"고칠 것": "bad", "확인": "warn", "참고": "mut"}


def _form_li(f):
    return (f"<li><span class='{FORM_CLS.get(f['level'], '')}'><b>{e(f['level'])}</b></span> "
            + (f"<b>{e(f['q'])}번</b> " if f["q"] else "")
            + f"<span class='chip'>{e(f['kind'])}</span> {e(f['msg'])}</li>")


def form_section(data) -> str:
    fm = data.get("form")
    if not fm:
        return ""
    h = ["<h2>양식 점검</h2><div class='note'>AI 없이 스크립트가 시험지 PDF 의 글자와 위치로 본 것이다(이 PC 밖으로 보내지 않음). "
         "고치지는 않고 알리기만 한다 — 선지 순서를 바꾸면 정답 번호도 바뀌니 정답표와 함께 고친다.</div>"]
    if not fm.get("ok"):
        return "".join(h) + f"<div class='mut'>{e(fm.get('why', ''))}</div>"
    st = fm.get("stats", {})
    bits = [f"선택형 {st.get('items', 0)}문항"] + ([f"서답형 {st['essays']}"] if st.get("essays") else [])
    if "body_line_mm" in st:
        bits.append(f"줄 간격 본문 {st['body_line_mm']}mm · 선지 {st['choice_line_mm']}mm")
    if "points_sum" in st:
        bits.append(f"배점 합 {st['points_sum']:g}점")
    if st.get("answer_count"):
        bits.append("정답 " + " ".join(f"{'①②③④⑤'[int(k) - 1]}{v}" for k, v in st["answer_count"].items()))
    h.append(f"<div class='mut'>{e(' · '.join(bits))}</div>")
    if not fm["findings"]:
        h.append("<div class='ok'>걸린 것 없음 — 번호·기호 순서, 선지 배열, 배치, 줄 간격을 봤다.</div>")
    else:
        h.append("<ul>" + "".join(_form_li(f) for f in fm["findings"]) + "</ul>")
    return "".join(h)


CSS = """
:root{--bg:#fbfaf7;--fg:#1d1c1a;--mut:#6b6862;--line:#dedbd3;--card:#fff;--bad:#b3261e;--warn:#9a5b00;--ok:#256c3a;--chip:#efece5}
@media (prefers-color-scheme:dark){:root{--bg:#171614;--fg:#eceae4;--mut:#a09c93;--line:#34322e;--card:#201f1c;--bad:#ff8a80;--warn:#f0b35a;--ok:#7fcf95;--chip:#2b2926}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,"Apple SD Gothic Neo",sans-serif}
main{max-width:920px;margin:0 auto;padding:32px 16px 80px}h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:36px 0 10px}
.mut{color:var(--mut);font-size:14px}.banner{border:2px solid var(--bad);color:var(--bad);padding:12px 14px;border-radius:8px;margin:16px 0;font-weight:600}
.note{border-left:3px solid var(--line);padding:2px 12px;color:var(--mut);font-size:14px;margin:14px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:12px 0}
.card h3{margin:0 0 8px;font-size:17px}.chip{display:inline-block;background:var(--chip);border-radius:99px;padding:1px 9px;font-size:13px;margin:0 4px 4px 0}
.bad{color:var(--bad)}.warn{color:var(--warn)}.ok{color:var(--ok)}table{border-collapse:collapse;width:100%;font-size:14px}
td,th{border-top:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}th{color:var(--mut);font-weight:500}
.issue{border-top:1px solid var(--line);padding:9px 0}.issue.refuted{opacity:.6}.sev{font-weight:700}ol.top{padding-left:22px}
.wrap{overflow-x:auto}a{color:inherit}
"""


def _answers(r, models):
    out = ['<div class="wrap"><table><tr><th>모델</th><th>답</th><th>확신</th><th>가정·멈칫</th></tr>']
    for m in models:
        x = r["answers"].get(m)
        if not x:
            out.append(f"<tr><td>{LABEL[m]}</td><td class='mut' colspan=3>답 없음</td></tr>")
            continue
        cls = {True: "ok", False: "bad", None: ""}[x["match"]]
        mark = {True: " ✓", False: " ✗ 정답표와 다름", None: ""}[x["match"]]
        notes = " / ".join(t for t in (x.get("assumed"), x.get("stuck")) if t)
        out.append(f"<tr><td>{LABEL[m]}</td><td class='{cls}'>{e(str(x.get('answer', '')))}{mark}</td>"
                   f"<td>{e(str(x.get('confidence', '')))}</td><td>{e(notes)}</td></tr>")
    return "".join(out) + "</table></div>"


def _issue(i):
    v = i.get("verdict")
    vtxt = VERDICT.get(v, v)
    by = f" — {LABEL.get(i.get('verdict_by'), '')}: {e(i.get('verdict_reason', ''))}" if i.get("verdict_by") else ""
    return (f"<div class='issue {'refuted' if v == 'refuted' else ''}'>"
            f"<span class='sev'>{e(i['severity'])} {e(SEVERITY.get(i['severity'], ''))}</span> "
            f"<span class='chip'>{' · '.join(LABEL[m] for m in i.get('same_by', [i['by']]))} "
            f"({len(i.get('same_by', [1]))}개 모델)</span>"
            f"<span class='chip'>지적: {LABEL[i['by']]}</span>"
            + ("<span class='chip warn'>새 지적</span>" if i.get("new") else "")
            + f"<div>{e(i['claim'])}</div>"
            + (f"<div class='mut'>근거: {e(i['evidence'])}</div>" if i.get("evidence") else "")
            + (f"<div class='mut'>고칠 방법: {e(i['fix'])}</div>" if i.get("fix") else "")
            + f"<div class='mut'>반박 결과: {e(vtxt)}{by}</div></div>")


def render(data) -> str:
    models = data["models"]
    rows = data["rows"]
    top = [r for r in sorted(rows, key=score, reverse=True) if score(r) > 0]
    h = [f"<!doctype html><html lang='ko'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
         f"<title>시험지 검증 {e(data['name'])}</title><style>{CSS}</style><main>",
         f"<h1>시험지 검증 — {e(data['name'])}</h1>",
         f"<div class='mut'>{e(data['at'])} · {data['pages']}쪽 · "
         + " · ".join(f"{LABEL[m]}({e(str(data['model_ids'].get(m)))})" for m in models)
         + (" · 낮은 추론 단계(시험용)" if data.get("fast") else "") + "</div>"]
    if data["failed"]:
        h.append(f"<div class='banner'>검증 불완전 — 빠진 실행: {e(', '.join(data['failed']))}. "
                 "같은 명령을 다시 돌리면 빠진 것만 이어서 돌린다.</div>")
    if not data["has_key"]:
        h.append("<div class='banner'>정답표 없이 돌렸다. 정답 대조는 하지 않았다.</div>")
    h.append(plain(data))
    h.append("<div class='note'>이 문서는 통과 도장이 아니라 사람이 다시 볼 의심 목록이다. 모델들이 같은 곳을 함께 놓칠 수 있고, "
             "멀쩡한 문항을 틀렸다고 할 수도 있다. 최종 판정은 출제자와 교과 협의회가 한다.</div>")
    if data.get("prev"):
        h.append(f"<div class='note'>지난 실행 「{e(data['prev'])}」와 견줌 — 달라진 쪽: "
                 f"{', '.join(map(str, data['changed_pages'])) or '없음'}</div>")
    if data.get("prev"):
        news = sorted({r["q"] for r in rows for i in r["issues"] if i.get("new")}, key=lambda q: (len(q), q))
        h.append("<h2>지난 실행과 달라진 것</h2>")
        h.append(f"<div>새로 생긴 지적이 있는 문항: {e(', '.join(q + '번' for q in news)) or '없음'}</div>")
        if data.get("mismatch_change"):
            h.append("<div>정답표 대조가 달라진 문항: " + ", ".join(
                f"{e(c['q'])}번(다른 답 {len(c['was'])}개 모델 → {len(c['now'])}개 모델)" for c in data["mismatch_change"]) + "</div>")
        ch = sorted(data.get("issue_change", []), key=lambda c: (c["now"] - c["was"], c["severity"]))
        down = [c for c in ch if c["now"] < c["was"]]
        h.append(f"<div>지적한 모델 수가 줄거나 사라진 지적 {len(down)}종"
                 + (" <span class='mut'>— 줄었다고 고쳐진 것은 아니다. 모델이 이번에 짚지 않았을 수도 있으니 고친 문항은 직접 확인한다.</span>"
                    if down else "") + "</div><ul>")
        for c in down:
            h.append(f"<li><b>{e(c['q'])}번</b> {e(c['severity'])} {e(SEVERITY.get(c['severity'], ''))} "
                     f"<span class='chip'>{c['was']}개 모델 → {c['now']}개 모델</span> "
                     f"<span class='mut'>지난번: {e(c['claim'][:120])}</span></li>")
        h.append("</ul>")
        up = [c for c in ch if c["now"] > c["was"]]
        h.append(f"<div>지적한 모델 수가 늘거나 새로 생긴 지적 {len(up)}종</div><ul>")
        for c in reversed(up):
            h.append(f"<li><b>{e(c['q'])}번</b> {e(c['severity'])} {e(SEVERITY.get(c['severity'], ''))} "
                     f"<span class='chip'>{c['was']}개 모델 → {c['now']}개 모델</span></li>")
        h.append("</ul>")
    h.append(f"<h2>먼저 볼 문항 ({len(top)}개)</h2><ol class='top'>")
    for r in top:
        why = []
        if r["mismatch"]:
            why.append(f"<span class='bad'>정답표({e(str(r['key']))})와 다른 답: {', '.join(LABEL[m] for m in r['mismatch'])}</span>")
        elif r["disagree"]:
            why.append("<span class='warn'>모델끼리 답이 갈림</span>")
        sev = sorted({i["severity"] for i in r["issues"] if i.get("verdict") != "refuted"})
        if sev:
            why.append("지적: " + ", ".join(f"{s} {SEVERITY.get(s, '')}" for s in sev))
        elif r["issues"]:
            why.append("<span class='mut'>지적은 모두 반박됨</span>")
        h.append(f"<li><a href='#q{e(r['q'])}'><b>{e(r['q'])}번</b></a> — {' · '.join(why)}</li>")
    h.append("</ol>" if top else "</ol><div class='mut'>올라온 것이 없다. 그래도 통과를 뜻하지는 않는다.</div>")
    h.append(form_section(data))
    h.append("<h2>문항별</h2>")
    fby = {}
    for f in (data.get("form") or {}).get("findings", []):
        fby.setdefault(f["q"], []).append(f)
    for r in rows:
        key = f"정답표 {e(str(r['key']))}" if r["key"] is not None else "정답표에 없음"
        h.append(f"<div class='card' id='q{e(r['q'])}'><h3>{e(r['q'])}번 <span class='mut'>· {key}</span></h3>")
        h.append(_answers(r, models))
        if fby.get(r["q"]):
            h.append("<div class='issue'><span class='sev'>양식</span><ul>" + "".join(_form_li(f) for f in fby[r["q"]]) + "</ul></div>")
        for i in sorted(r["issues"], key=lambda i: (i.get("verdict") == "refuted", -WEIGHT.get(i["severity"], 0))):
            h.append(_issue(i))
        h.append("</div>")
    h.append("</main></html>")
    return "".join(h)
