# -*- coding: utf-8 -*-
"""Text lines of a PDF with geometry, for measuring word gaps (loose justified lines).
Each line: page, column (0/1), y (baseline), x0, x1, size (font size, pt), text, gaps (word gaps in pt)."""
import pypdfium2 as pdfium


def lines(pdf_path):
    doc = pdfium.PdfDocument(pdf_path)
    out = []
    for pi in range(len(doc)):
        page = doc[pi]
        W = page.get_width()
        tp = page.get_textpage()
        chars = []
        for i in range(tp.count_chars()):
            ch = tp.get_text_range(i, 1)
            if not ch or ch in "\r\n":
                continue
            l, b, r, t = tp.get_charbox(i, loose=True)
            if r - l <= 0 and ch != " ":
                continue
            chars.append((ch, l, b, r, t))
        # group by column then baseline
        rows = {}
        for ch, l, b, r, t in chars:
            col = 0 if (l + r) / 2 < W / 2 else 1
            key = (col, round(b * 2) / 2)
            rows.setdefault(key, []).append((l, r, t - b, ch))
        # merge baselines that differ by < 1.2 pt (mixed fonts on one line)
        keys = sorted(rows, key=lambda k: (k[0], -k[1]))
        merged = []
        for k in keys:
            if merged and merged[-1][0][0] == k[0] and abs(merged[-1][0][1] - k[1]) < 1.2:
                merged[-1][1].extend(rows[k])
            else:
                merged.append([k, list(rows[k])])
        for (col, y), cs in merged:
            cs.sort()
            glyphs = [c for c in cs if c[3] != " "]
            if not glyphs:
                continue
            size = sorted(c[2] for c in glyphs)[len(glyphs) // 2]
            gaps = []
            for a, b2 in zip(glyphs, glyphs[1:]):
                g = b2[0] - a[1]
                if g > 0.18 * size:
                    gaps.append(g)
            text = "".join(c[3] for c in cs)
            out.append(dict(page=pi + 1, col=col, y=y, x0=glyphs[0][0], x1=glyphs[-1][1], size=size,
                            text=text, norm="".join(c[3] for c in glyphs), gaps=gaps))
    doc.close()                      # release the file so Hancom can overwrite it next round
    return out


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    for ln in lines(sys.argv[1]):
        if ln["page"] == int(sys.argv[2]):
            g = ln["gaps"]
            print(f"c{ln['col']} y{ln['y']:.0f} x{ln['x0']:.0f}-{ln['x1']:.0f} s{ln['size']:.1f} "
                  f"gap{(sum(g)/len(g) if g else 0):.1f}/{len(g)} | {ln['text'][:40]}")
