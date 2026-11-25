"""양식 점검(form.py) 시험용 가짜 시험지: 글자 층이 있는 2단 A4 PDF 두 쪽. 일부러 심은 형식 오류마다 걸려야 한다.

심은 것(번호 = 문항):
  2  <보기> ㄱ·ㄷ·ㄴ 순서 / 3  ③ 빠짐 / 4  합답형 순서 어긋남 + 없는 기호 ㄹ / 5  수치 선지 순서 어긋남
  6  선지가 아래로 갈수록 짧아짐 + 선지 줄 간격 좁음 / 7 없음(번호 빠짐) / 8  「[5점]」 혼자 남은 줄
  9  (가)·(다)·(나) 순서 / 10 왼쪽 단 → 오른쪽 단으로 넘어감 / 배점안내 총(12)문항, 배점 합 50
정상: 1, 11
usage: python make_fake_form.py out.pdf
"""
import sys

sys.dont_write_bytecode = True
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.backends.backend_pdf import PdfPages

plt.rcParams["pdf.fonttype"] = 42  # 글자 층(ToUnicode)이 남게 트루타입으로 넣는다
for f in ("C:/Windows/Fonts/malgun.ttf", "/System/Library/Fonts/AppleSDGothicNeo.ttc",
          "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"):
    if Path(f).exists():
        font_manager.fontManager.addfont(f)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name()
        break

W, H = 210, 297
PITCH = 5.0  # mm, 본문 줄 간격


def page(pdf, lines):
    fig = plt.figure(figsize=(W / 25.4, H / 25.4))
    for x, y, t in lines:
        fig.text(x / W, 1 - y / H, t, fontsize=9.5, va="center", ha="left")
    pdf.savefig(fig)
    plt.close(fig)


def item(col, y, rows, choice_pitch=PITCH):
    """rows: 본문 줄들과 ('C', 선지 줄) — 선지 줄은 choice_pitch 간격"""
    x = 15 if col == 0 else 112
    out = []
    prev_c = False
    for i, r in enumerate(rows):
        if isinstance(r, tuple):
            y += choice_pitch if prev_c else PITCH
            out.append((x + 3, y, r[1]))
            prev_c = True
        else:
            y += PITCH if i else 0
            out.append((x if i == 0 else x + 3, y, r))
            prev_c = False
    return out, y + 2 * PITCH


def main(out: Path):
    p1, p2 = [], []
    p1.append((15, 15, "2026학년도 2학기 연습 평가 과학"))
    p1.append((15, 25, "<배점안내> 본 과목은 총(12)문항, (2면)으로 되어 있습니다."))
    p2.append((15, 15, "2026학년도 2학기 연습 평가 과학"))
    y = 35
    L, y = item(0, y, ["1. 다음 설명으로 옳은 것만을 [보기]에서 있는 대로 고른 것은? [5점]", "[보기]",
                       "ㄱ. 물은 100 ℃에서 끓는다.", "ㄴ. 얼음은 물에 뜬다.", "ㄷ. 수증기는 기체이다.",
                       ("C", "① ㄱ   ② ㄴ   ③ ㄱ, ㄴ"), ("C", "④ ㄴ, ㄷ   ⑤ ㄱ, ㄴ, ㄷ")]); p1 += L
    L, y = item(0, y, ["2. 다음 설명으로 옳은 것만을 [보기]에서 있는 대로 고른 것은? [5점]", "[보기]",
                       "ㄱ. 빛은 직진한다.", "ㄷ. 소리는 진공에서 전달된다.", "ㄴ. 빛은 굴절한다.",
                       ("C", "① ㄱ   ② ㄷ   ③ ㄱ, ㄴ"), ("C", "④ ㄴ, ㄷ   ⑤ ㄱ, ㄴ, ㄷ")]); p1 += L
    L, y = item(0, y, ["3. 다음 중 홑원소 물질은? [5점]",
                       ("C", "① 산소   ② 물   ④ 소금"), ("C", "⑤ 설탕")]); p1 += L
    L, y = item(0, y, ["4. 다음 설명으로 옳은 것만을 [보기]에서 있는 대로 고른 것은? [5점]", "[보기]",
                       "ㄱ. 철은 자석에 붙는다.", "ㄴ. 구리는 전기가 통한다.", "ㄷ. 나무는 전기가 잘 통한다.",
                       ("C", "① ㄱ, ㄴ   ② ㄱ   ③ ㄷ"), ("C", "④ ㄴ, ㄷ   ⑤ ㄱ, ㄹ")]); p1 += L
    L, y = item(0, y, ["5. 물체의 질량이 2 kg 일 때 무게는 몇 N 인가? [5점]",
                       ("C", "① 19.6 N   ② 9.8 N   ③ 4.9 N"), ("C", "④ 29.4 N   ⑤ 39.2 N")]); p1 += L
    L, y = item(0, y, ["6. 생태계에 대한 설명으로 옳은 것은? [5점]",
                       ("C", "① 생산자는 빛에너지를 화학 에너지로 바꾸어 양분을 만든다."),
                       ("C", "② 분해자는 죽은 생물을 분해하여 무기물로 돌려보낸다."),
                       ("C", "③ 소비자는 다른 생물을 먹어 양분을 얻는다."),
                       ("C", "④ 먹이 사슬은 한 방향이다."), ("C", "⑤ 햇빛은 비생물이다.")],
                choice_pitch=3.2); p1 += L
    L, y = item(0, y, ["8. 다음 중 포유류가 아닌 것은? 다음 중 포유류가 아닌 것은 무엇인지 고른 것은?",
                       "[5점]", ("C", "① 고래   ② 박쥐   ③ 상어"), ("C", "④ 사람   ⑤ 원숭이")]); p1 += L
    L, y = item(0, y, ["9. 다음은 물질의 상태 변화 (가)~(다)이다. 이에 대한 설명으로 옳은 것은? [5점]",
                       "(가) 얼음이 녹는다.", "(다) 물이 끓는다.", "(나) 수증기가 물이 된다.",
                       ("C", "① (가)는 융해이다.   ② (나)는 기화이다."),
                       ("C", "③ (다)는 응고이다.   ④ (가)는 승화이다."), ("C", "⑤ (나)는 융해이다.")]); p1 += L
    L, y = item(0, y, ["10. 다음은 지구의 구조를 나타낸 것이다. 이에 대한 설명으로 옳은 것은? [5점]",
                        "지각, 맨틀, 외핵, 내핵으로 이루어져 있다.", "가장 두꺼운 층은 맨틀이다."]); p1 += L
    yr = 35
    L, yr = item(1, yr - 2 * PITCH, ["외핵은 액체 상태이다.",
                                      ("C", "① 지각이 가장 두껍다.   ② 내핵은 액체이다."),
                                      ("C", "③ 맨틀은 고체이다.   ④ 외핵은 기체이다."), ("C", "⑤ 핵은 없다.")])
    p1 += [(x - 3 if t.startswith("외핵") else x, yy, t) for x, yy, t in L]
    L, yr = item(1, yr, ["11. 다음 중 산성 용액은? [5점]",
                         ("C", "① 식초   ② 비눗물   ③ 설탕물"), ("C", "④ 소금물   ⑤ 증류수")]); p1 += L
    with PdfPages(out) as pdf:
        page(pdf, p1)
        page(pdf, p2)  # 머리말만 있는 쪽(머리말은 되풀이되니 본문에서 빠진다)
    print(out)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
