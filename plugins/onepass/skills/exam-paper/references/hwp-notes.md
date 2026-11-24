# 한글(HWP) 자동화 메모 — 실제 원안 작업에서 겪은 것

## 파일·경로
- 구글드라이브·원드라이브 등 클라우드 동기화 폴더의 한글 파일을 COM으로 직접 열면 숨은 대화상자 때문에 멈춘다 → scratch로 복사해서 작업, 결과만 복사.
- 한글에 넘기는 경로는 **백슬래시**(`os.path.normpath`). 슬래시 경로는 숨은 '접근 허용' 창으로 멈춘다.
- 대괄호가 든 이름(`[비상교육] …`)은 PowerShell에서 `-LiteralPath`.
- PowerShell 5.1: BOM 없는 .ps1에 한글을 쓰면 깨진다 → 한글 문자열은 JSON 파일이나 인자로 넘긴다(`replace_json.py`).
- 숨은 Hwp.exe가 남으면 창 제목이 없는 것만 정리(`Get-Process Hwp`, MainWindowTitle 빈 것). 선생님이 띄운 한글은 건드리지 않는다.
- TEXT로 저장한 파일은 CP949.
- 임시 폴더(scratchpad)는 며칠 뒤 정리되며 파일이 지워진다 → 재사용할 스크립트는 이 스킬 폴더에 둔다.

## COM API
- 위치: `GetPos()` → (list, para, pos), `SetPos(list, para, pos)`는 잘못된 위치에도 True를 돌려주므로 `GetPos()`로 확인. list 0 = 본문, 1.. = 표 칸·머리말·꼬리말.
- `KeyIndicator()`(쪽·단·줄)는 out 인자라 PowerShell에서 못 받음 → Python pywin32 `gencache.EnsureDispatch`.
- 파일 끼워 넣기: `HInsertFile.filename`(소문자) / KeepSection=0, KeepCharshape=1, KeepParashape=1.
- 그 전에 list id를 훑느라 SetPos를 많이 부르면 커서가 엉뚱한 곳에 가 있다 → 끼워 넣기 전 `MoveDocEnd`.
- `RepeatFind`는 문서 끝에서 처음으로 되돌아간다 → while 루프에 쓰면 끝없이 돈다. 문단을 하나씩 읽어 찾는다.
- 문단 모양: `HParaShape` — `BreakNonLatinWord`(0 어절, 1 글자), `Condense`(최소 공백 %), `LeftMargin`/`Indentation`(1pt = 200), 내어쓰기는 Indentation 음수.
- 글자 모양 일부만 바꾸기: `act = hwp.CreateAction("CharShape"); s = act.CreateSet(); s.SetItem("SpacingHangul", v) …; act.Execute(s)` (GetDefault 없이 → 밑줄·형광 등 다른 속성 유지). 언어 7개(Hangul, Latin, Hanja, Japanese, Other, Symbol, User) 모두.
- `ParagraphShapeIndentAtCaret`: 커서 위치에 맞춰 내어쓰기. **표 칸 안에서는 LeftMargin을 무시**하므로 LeftMargin 0에서 먼저 하고 그다음 LeftMargin을 준다.
- 머리 글자 뒤 빈칸: 일반 빈칸은 최소 공백·양쪽 정렬로 줄었다 늘었다 해서 내어쓰기가 어긋난다. `InsertNonBreakingSpace`(묶음 빈칸)가 폭도 자연스럽고 안 변한다. 고정폭 빈칸(`InsertFixedWidthSpace`)은 너무 좁다.
- 표: `ctrl.Properties`의 `TreatAsChar`=1(글자처럼, 쪽 넘김으로 안 쪼개짐), `PageBreak`(0 나누지 않음, 1 셀 단위), `RepeatHeader`, `HorzRelTo/HorzAlign/HorzOffset`. 표 위치는 앵커 문단(`GetAnchorPos`)의 문단 모양을 따른다.
- AllReplace는 꼬리말에 안 닿을 때가 있다 → 모든 list를 문단별로 훑어 바꾼다(`fix_footer.py`).
- 페이지 이미지: `CreatePageImage(path, page0, dpi, 24, "bmp")`(png를 줘도 bmp로 나옴) → PIL로 png 변환.

## 정답 표시 = 형광펜
- HTML `background-color`는 한글로 가져오면 글자 **음영색**(`shadeColor`)이 된다 → 인쇄된다. 형광펜(HWPX `<hp:t><hp:markpenBegin color="#FFFF00"/>③<hp:markpenEnd/>…`)은 종이 인쇄(인쇄 설정 `PrintMarkPen` 기본 0)와 `CreatePageImage`에는 안 나오지만, **SaveAs PDF 에는 찍힌다**.
- 선지 표 줄 높이: HTML 로 가져온 2행×3열 선지 표는 칸 높이가 최소값(`cellSz height` 282, 줄 약 4.1mm)이다. HWPX 에서 `cellSz height`=1600, 표 `sz height`=2×1600+150 으로 바꾸면 5.6mm(`markpen.py`). 문구를 XML 에서 바꿀 때는 그 문단의 `linesegarray` 를 지워야 줄 배치가 다시 계산된다(안 지우면 뒤 문단이 사라짐). header.xml 의 paraPr 를 복제해 붙이는 방법은 문서를 깨뜨렸다.
- COM으로 형광펜: 글자 선택 후 `CreateAction("MarkPenShape")` + `Color`(BGR, 노랑 0x00FFFF). 여러 곳은 HWPX로 저장해 XML을 고치는 편이 빠르고 확실하다(`markpen.py`).
- HWPX는 zip: `mimetype`을 맨 앞에 압축 없이 넣어야 한글이 연다. PowerShell `Expand-Archive`는 .hwpx 확장자를 거부 → .zip으로 복사해서 풀거나 Python zipfile.

## HTML 가져오기
- `cellpadding` 무시, 칸 `padding`은 일부만. 상자 안 좌우 여백은 가져온 뒤 문단 LeftMargin/RightMargin으로.
- CSS `word-break`, 자간, 장평은 안 먹는다 → 가져온 뒤 일괄 적용.
- `margin:4pt 0 3pt 1.6em` 같은 축약형은 무시될 수 있다 → margin-top/-left 따로.
- px → HWP: 96 dpi 기준(360 px ≈ 95 mm). B4 2단 원안의 단 폭 ≈ 102 mm(≈385 px).

## PDF 측정(자간 조정)
- pypdfium2 `get_charbox(i, loose=True)`로 글꼴 기준 상자 → 같은 줄이 한 기준선으로 묶인다.
- 쪽 머리말(y>770)·꼬리말(y<80)은 빼야 쪽을 넘는 문단이 이어진다.
- 같은 문장(발문 "이에 대한 설명으로…")이 여러 번 → 문서 순서대로 n번째끼리 짝짓기.
- **PdfDocument를 꼭 close** — 안 닫으면 다음 측정 때 한글이 같은 PDF를 못 덮어써서 첫 결과만 계속 읽는다(조정이 전혀 안 되는 증상).
- 벌어진 줄 = 줄의 평균 단어 간격 / 그 글꼴의 자연 간격(마지막 줄들의 중앙값) > 1.25~1.3. 외톨이 = 마지막 줄 4글자 이하 또는 "[5점]"만.
- 자간 후보 -12~0 % (−11·−12는 외톨이 해결용, 벌점 큼). 문단 줄바꿈은 위치와 무관하므로 후보마다 전체를 한 번에 바꿔 PDF 한 번으로 잰다.
