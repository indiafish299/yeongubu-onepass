"""PDF를 쪽 이미지(PNG)로 바꾼다. 학생이 받는 인쇄본과 같은 모양을 모델에 보여 주기 위함."""
import re
import sys

sys.dont_write_bytecode = True
from pathlib import Path

import pypdfium2 as pdfium


def pdf_to_pages(pdf: Path, out_dir: Path, dpi: int = 200) -> list[Path]:
    """쪽마다 page-01.png ... 를 만들고 경로 목록을 돌려준다. 쪽 수가 안 맞으면 예외."""
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(pdf))
    paths = []
    for i in range(len(doc)):
        img = doc[i].render(scale=dpi / 72).to_pil().convert("RGB")
        p = out_dir / f"page-{i + 1:02d}.png"
        img.save(p, "PNG")
        paths.append(p)
    if len(paths) != len(doc) or not paths:
        raise RuntimeError(f"쪽 수 불일치: PDF {len(doc)}쪽, 이미지 {len(paths)}장")
    return paths


if __name__ == "__main__":
    for p in pdf_to_pages(Path(sys.argv[1]), Path(sys.argv[2])):
        print(p)


def pdf_text(pdf: Path, masks: dict) -> str:
    """PDF 글자 층을 쪽마다 뽑는다. masks = {쪽: [[x0,y0,x1,y1], ...]} (0~1 비율, 위에서부터)로 가린 칸의 글자는 뺀다.
    글자 층이 없는 PDF(스캔본)면 빈 글."""
    import pypdfium2 as pdfium

    out = []
    doc = pdfium.PdfDocument(str(pdf))
    for n, page in enumerate(doc, 1):
        W, H = page.get_size()
        tp = page.get_textpage()
        chars = []
        for i in range(tp.count_chars()):
            ch = tp.get_text_range(i, 1)
            if ch.strip():
                l, b, r, t = tp.get_charbox(i)
                cx, cy = (l + r) / 2 / W, 1 - (b + t) / 2 / H
                if any(x0 <= cx <= x1 and y0 <= cy <= y1 for x0, y0, x1, y1 in masks.get(n, [])):
                    continue
            chars.append(ch)
        body = re.sub(r"[ \t]+", " ", "".join(chars).replace("\r", ""))
        body = re.sub(r"\n\s*\n+", "\n", body).strip()
        out.append(f"=== {n}쪽 ===\n{body}")
    return "\n\n".join(out) if any(len(o.split("\n", 1)[-1]) > 20 for o in out) else ""
