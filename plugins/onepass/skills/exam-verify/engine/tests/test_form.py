"""양식 점검 시험: 가짜 시험지(make_fake_form.py)에 심은 오류가 모두 걸리고, 정상 문항(1·11번)은 걸리지 않아야 한다.
usage: python test_form.py   (끝줄 OK 면 통과)"""
import sys

sys.dont_write_bytecode = True
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "exam_verify"))
import form  # noqa: E402
import make_fake_form  # noqa: E402

WANT = [("2", "기호 순서"), ("3", "보기 번호"), ("4", "선지 기호"), ("4", "선지 배열"), ("5", "선지 배열"),
        ("6", "선지 길이"), ("6", "선지 줄 간격"), ("7", "문항 번호"), ("8", "배치"), ("9", "기호 순서"),
        ("10", "배치"), ("", "문항 수"), ("", "배점"), ("", "정답 분포"), ("6", "정답 분포")]
ANS = {"1": "③", "2": "③", "3": "①", "4": "②", "5": "②", "6": "②", "8": "③", "9": "①", "10": "③", "11": "①"}

with tempfile.TemporaryDirectory() as td:
    pdf = Path(td) / "fake_form.pdf"
    make_fake_form.main(pdf)
    res = form.check(pdf, ANS)
print(form.text(res))
got = {(f["q"], f["kind"]) for f in res["findings"]}
miss = [w for w in WANT if w not in got]
clean = [f for f in res["findings"] if f["q"] in ("1", "11")]
assert res["stats"]["items"] == 10, res["stats"]
assert not miss, f"못 잡은 것: {miss}"
assert not clean, f"정상 문항이 걸림: {clean}"
print("OK")
