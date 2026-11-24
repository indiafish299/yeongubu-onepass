"""Render PDF pages to PNG. Usage: pdfrender.py PDF OUTDIR PAGES(1-based, comma/range) [SCALE]"""
import sys, pathlib
import pypdfium2 as pdfium

pdf, outdir, spec = sys.argv[1], pathlib.Path(sys.argv[2]), sys.argv[3]
scale = float(sys.argv[4]) if len(sys.argv) > 4 else 1.3
outdir.mkdir(parents=True, exist_ok=True)
pages = []
for part in spec.split(","):
    if "-" in part:
        a, b = part.split("-"); pages += list(range(int(a), int(b) + 1))
    else:
        pages.append(int(part))
doc = pdfium.PdfDocument(pdf)
stem = pathlib.Path(pdf).stem[:20].replace(" ", "_")
for n in pages:
    img = doc[n - 1].render(scale=scale).to_pil()
    p = outdir / f"{stem}_p{n:02d}.png"
    img.save(p)
    print(p)
