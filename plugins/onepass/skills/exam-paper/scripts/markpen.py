"""정답 표시를 한글 '형광펜'으로 바꾸고 부정 발문 밑줄을 정리한다 (rebuild.ps1 끝에서 자동 실행, 기존 원안에도 단독 사용).

usage: <python> markpen.py <in.hwp> <out.hwp> [<out.pdf>] [--row-mm 5.6]

- 정답 번호(①~⑤)의 노란 글자 음영(shadeColor #FFFF00)은 인쇄된다 -> 음영을 없애고 형광펜(노랑)으로.
  형광펜은 종이 인쇄에는 안 나온다(한글 인쇄 기본값 PrintMarkPen=0). 하지만 PDF 로 저장하면 찍힌다.
- 밑줄 글자(본문에서 실제로 쓰인 것만)에 굵게를 더한다.
- '옳지 않은' 전체에 밑줄이 있으면 '않은'에만 밑줄이 가게 나눈다.
- 두 줄 선지 표(①~⑤, 2행×3열)의 줄 높이를 넓힌다(기본 5.6mm, 본문 한 줄 높이와 비슷). HTML 로 가져온
  선지 표는 칸 높이가 최소값(약 4.1mm)이라 너무 좁았다(2026-11-24 선생님 지적). 연결형 선지 표(머리 줄 포함 6행)는 건드리지 않는다.
방법: 한글로 HWPX 저장 -> XML 수정 -> 한글로 다시 열어 HWP(·PDF) 저장. 작업은 임시 폴더에서, 경로는 백슬래시.
"""
import sys, os, re, zipfile, tempfile, shutil
sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")
import win32com.client as w

args = sys.argv[1:]
ROW_MM = 5.6
if "--row-mm" in args:
    i = args.index("--row-mm"); ROW_MM = float(args[i + 1]); del args[i:i + 2]
ROW = round(ROW_MM / 25.4 * 7200)  # HWPUNIT (1 inch = 7200); 5.6mm -> 1587 ≈ 1600
src = os.path.normpath(os.path.abspath(args[0]))
dst = os.path.normpath(os.path.abspath(args[1]))
pdf = os.path.normpath(os.path.abspath(args[2])) if len(args) > 2 else None
tmp = tempfile.mkdtemp(prefix="markpen_")


def hwp_open():
    h = w.gencache.EnsureDispatch("HWPFrame.HwpObject")
    try:
        h.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
    except Exception:
        pass
    h.SetMessageBoxMode(0x00020000 | 0x00000010 | 0x00000100)
    return h


def fix_xml(d):
    hp, sp = os.path.join(d, "Contents", "header.xml"), os.path.join(d, "Contents", "section0.xml")
    hdr, sec = open(hp, encoding="utf-8").read(), open(sp, encoding="utf-8").read()
    shade, ul = set(), set()

    def fix_cp(m):
        x, i = m.group(0), m.group(1)
        if 'shadeColor="#FFFF00"' in x:
            shade.add(i)
            x = x.replace('shadeColor="#FFFF00"', 'shadeColor="none"')
        if '<hh:underline type="BOTTOM"' in x and re.search(r'charPrIDRef="%s">\s*<hp:t>[^<]*\S' % i, sec):
            ul.add(i)
            if "<hh:bold/>" not in x:
                x = x.replace("<hh:underline ", "<hh:bold/><hh:underline ", 1)
        return x
    hdr = re.sub(r'<hh:charPr id="(\d+)".*?</hh:charPr>', fix_cp, hdr, flags=re.S)
    n_mark = n_split = 0
    if shade:
        ids = "|".join(shade)
        sec, n_mark = re.subn(r'(<hp:run charPrIDRef="(?:%s)"><hp:t>)([①②③④⑤])' % ids,
                              r'\1<hp:markpenBegin color="#FFFF00"/>\2<hp:markpenEnd/>', sec)
        for m in re.finditer(r'<hp:run charPrIDRef="(?:%s)">(.*?)</hp:run>' % ids, sec, re.S):
            t = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            if t and t not in "①②③④⑤":
                print("CHECK 노란 음영이 정답 번호 밖에 있었음(음영만 지움):", t)
    if ul:
        def split(m):
            nonlocal n_split
            n_split += 1
            prev = re.findall(r'charPrIDRef="(\d+)"', sec[:m.start()])[-1]
            return (f'<hp:run charPrIDRef="{prev}"><hp:t>옳지 </hp:t></hp:run>'
                    f'<hp:run charPrIDRef="{m.group(1)}"><hp:t>않은</hp:t></hp:run>')
        sec = re.sub(r'<hp:run charPrIDRef="(%s)"><hp:t>옳지 않은</hp:t></hp:run>' % "|".join(ul), split, sec)
    ul_txt = [re.sub(r"<[^>]+>", "", m.group(1)) for m in
              re.finditer(r'<hp:run charPrIDRef="(?:%s)">(.*?)</hp:run>' % "|".join(ul or {"-1"}), sec, re.S)]
    # 두 줄 선지 표(2행×3열, 글자가 ①로 시작)의 칸 높이를 ROW 로. 표 높이 = 2×ROW + 바깥 여백(150).
    # 칸 안 글자는 세로 가운데(vertAlign=CENTER)라 위아래로 고르게 벌어진다. 이미 ROW 이상이면 그대로.
    n_rows = 0
    def rows(m):
        nonlocal n_rows
        x = m.group(0)
        if not re.sub(r"<[^>]+>", "", x).lstrip().startswith("①"):
            return x
        hs = [int(v) for v in re.findall(r'<hp:cellSz width="\d+" height="(\d+)"', x)]
        if hs and min(hs) >= ROW:
            return x
        n_rows += 1
        x = re.sub(r'(<hp:cellSz width="\d+" height=")\d+(")', lambda k: f"{k.group(1)}{ROW}{k.group(2)}", x)
        return re.sub(r'(<hp:sz width="\d+"[^>]*? height=")\d+(")', lambda k: f"{k.group(1)}{2 * ROW + 150}{k.group(2)}",
                      x, count=1)
    sec = re.sub(r'<hp:tbl [^>]*rowCnt="2" colCnt="3"[^>]*>.*?</hp:tbl>', rows, sec, flags=re.S)
    open(hp, "w", encoding="utf-8").write(hdr)
    open(sp, "w", encoding="utf-8").write(sec)
    return n_mark, n_split, ul_txt, n_rows


try:
    x1, x2, d = os.path.join(tmp, "a.hwpx"), os.path.join(tmp, "b.hwpx"), os.path.join(tmp, "x")
    h = hwp_open()
    h.Open(src, "", "forceopen:true")
    pages0 = h.PageCount
    h.SaveAs(x1, "HWPX", "")
    h.Clear(1)
    with zipfile.ZipFile(x1) as z:
        z.extractall(d)
    n_mark, n_split, ul_txt, n_rows = fix_xml(d)
    with zipfile.ZipFile(x2, "w") as z:
        z.write(os.path.join(d, "mimetype"), "mimetype", compress_type=zipfile.ZIP_STORED)
        for root, _, files in os.walk(d):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, d).replace("\\", "/")
                if rel != "mimetype":
                    z.write(full, rel, compress_type=zipfile.ZIP_DEFLATED)
    h.Open(x2, "HWPX", "forceopen:true")
    pages1 = h.PageCount
    h.SaveAs(dst, "HWP", "")
    if pdf:
        h.SaveAs(pdf, "PDF", "")
    h.Clear(1)
    h.Quit()
    print(f"형광펜 {n_mark}개, '옳지 않은' 나눔 {n_split}곳, 밑줄+굵게: {ul_txt}, "
          f"선지 줄 높이 {ROW_MM}mm {n_rows}개 표, 쪽 {pages0}->{pages1}")
    if pages0 != pages1:
        print("CHECK 쪽 수가 바뀜 — 캡처 검사 필요")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
