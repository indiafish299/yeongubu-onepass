"""채점 기준 단계 시험용 가짜 시험지 한 쪽(선택형 1 + 서답형 3)과 채점 기준표를 만든다.

채점 기준에 일부러 심은 흠:
  서답1 — 기준이 "14 m/s"만 인정(10√2 m/s, 14.1 m/s 같은 타당한 답이 빠짐)
  서답2 — 기준이 페인트·기름 두 가지만 인정(도금, 합금 등 타당한 답이 빠짐)
  서답3 — "밀도를 적절히 언급하면"이라는 모호한 낱말, 부분 점수 기준 없음
쓰기: make_fake_essay.py <출력.pdf> <rubric.md> <answers.json>
"""
import json
import sys

sys.dont_write_bytecode = True
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
if not Path(FONT).exists():  # 윈도우
    FONT = "C:/Windows/Fonts/malgun.ttf"

LINES = [
    (56, "과학 연습 평가 (서답형)"), (0, ""),
    (36, "1. 질량이 2 kg인 물체에 알짜힘 10 N이 작용할 때 물체의 가속도 크기는?"),
    (36, "    ① 2 m/s²   ② 5 m/s²   ③ 8 m/s²   ④ 12 m/s²   ⑤ 20 m/s²"), (0, ""),
    (36, "[서답형 1] 질량이 2 kg인 물체를 지면으로부터 10 m 높이에서 가만히 놓았다."),
    (36, "    지면에 닿기 직전 물체의 속력을 구하시오. (단, 중력 가속도는 10 m/s²이고,"),
    (36, "    공기 저항은 무시한다.) [5점]"), (0, ""),
    (36, "[서답형 2] 철로 만든 물건이 녹스는 것을 막는 방법을 두 가지 쓰시오. [6점]"), (0, ""),
    (36, "[서답형 3] 얼음이 물 위에 뜨는 까닭을 서술하시오. [5점]"),
]

RUBRIC = """# 서답형 채점 기준
- 서답1 (5점): 14 m/s 라고 쓰면 5점. 그 밖의 답은 0점.
- 서답2 (6점): '페인트를 칠한다', '기름을 바른다' 를 쓰면 각 3점.
- 서답3 (5점): 밀도를 적절히 언급하면 5점.
"""


def main(out: Path, rubric: Path, answers: Path) -> None:
    W, H = 1654, 2339
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    y = 100
    for size, text in LINES:
        if size:
            d.text((120, y), text, font=ImageFont.truetype(FONT, size), fill="black")
        y += (size or 40) + 30
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "PDF", resolution=200)
    rubric.write_text(RUBRIC)
    answers.write_text(json.dumps({"confirmed": True, "confirmed_note": "가짜 시험지(시험용)",
                                   "answers": {"1": "②"}}, ensure_ascii=False))
    print(out, rubric, answers)


if __name__ == "__main__":
    main(*(Path(p) for p in sys.argv[1:4]))
