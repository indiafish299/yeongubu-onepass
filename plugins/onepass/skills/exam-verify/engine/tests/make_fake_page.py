"""호출·격리 시험용 가짜 시험지 한 쪽을 만든다(PDF 한 장).

넣은 것: 이미지에만 있는 확인 문자열, 그림을 봐야 풀리는 문항(1번),
일부러 심은 복수 정답(2번), 정상 문항(3번).
"""
import sys

sys.dont_write_bytecode = True
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
if not Path(FONT).exists():  # 윈도우
    FONT = "C:/Windows/Fonts/malgun.ttf"
NONCE = "QX7-41KM-ZP"


def main(out: Path) -> None:
    W, H = 1654, 2339  # A4 200dpi
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    f = lambda s: ImageFont.truetype(FONT, s)
    d.text((120, 100), "과학 연습 평가", font=f(56), fill="black")
    d.text((1100, 120), f"확인 문자열: {NONCE}", font=f(30), fill="black")
    d.line((120, 190, W - 120, 190), fill="black", width=3)

    y = 250
    d.text((120, y), "1. 그림은 직선 위에서 운동하는 물체의 속도를 시간에 따라 나타낸 것이다.", font=f(36), fill="black")
    d.text((160, y + 55), "0초부터 4초까지 물체가 이동한 거리는?", font=f(36), fill="black")
    # 그래프: 원점 (300, 800), 가로 1초=120px, 세로 1m/s=50px
    ox, oy = 300, 800
    d.line((ox, oy, ox + 600, oy), fill="black", width=3)
    d.line((ox, oy, ox, oy - 380), fill="black", width=3)
    for t in range(1, 5):
        d.line((ox + 120 * t, oy - 8, ox + 120 * t, oy + 8), fill="black", width=2)
        d.text((ox + 120 * t - 8, oy + 15), str(t), font=f(28), fill="black")
    for v in (2, 4, 6):
        d.line((ox - 8, oy - 50 * v, ox + 8, oy - 50 * v), fill="black", width=2)
        d.text((ox - 45, oy - 50 * v - 16), str(v), font=f(28), fill="black")
    d.line((ox, oy, ox + 480, oy - 300), fill="black", width=5)
    d.text((ox + 610, oy - 15), "시간(s)", font=f(28), fill="black")
    d.text((ox - 60, oy - 430), "속도(m/s)", font=f(28), fill="black")
    d.text((ox - 30, oy + 15), "0", font=f(28), fill="black")
    d.text((160, 880), "① 6 m     ② 12 m     ③ 18 m     ④ 24 m     ⑤ 30 m", font=f(36), fill="black")

    y = 1020
    d.text((120, y), "2. 다음 중 실온(25 ℃), 1기압에서 액체 상태인 물질은?", font=f(36), fill="black")
    d.text((160, y + 70), "① 철     ② 물     ③ 산소     ④ 에탄올     ⑤ 소금", font=f(36), fill="black")

    y = 1260
    d.text((120, y), "3. 질량이 2 kg인 물체에 알짜힘 10 N이 작용할 때 물체의 가속도 크기는?", font=f(36), fill="black")
    d.text((160, y + 70), "① 2 m/s²   ② 5 m/s²   ③ 8 m/s²   ④ 12 m/s²   ⑤ 20 m/s²", font=f(36), fill="black")

    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "PDF", resolution=200)
    print(out)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
