# -*- coding: utf-8 -*-
"""시험지용 그래프 그리기 예시: 한글 글꼴, 눈금 없는 상댓값 축, 구간 음영, 곡선 이름표.
usage: <python> make_graph_example.py OUT.png"""
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for f in (r"C:\Windows\Fonts\malgun.ttf",):            # 맑은 고딕 (Windows 기본)
    try:
        font_manager.fontManager.addfont(f); plt.rcParams["font.family"] = "Malgun Gothic"
    except Exception:
        pass
plt.rcParams["axes.unicode_minus"] = False

t = np.linspace(0, 10, 401)
A = 2.0 * t                                           # 예: 물체 A의 이동 거리
B = 1.0 * t                                           # 예: 물체 B의 이동 거리
fig, ax = plt.subplots(figsize=(3.3, 2.2), dpi=300)
ax.plot(t, A, color="black", lw=1.4)
ax.plot(t, B, color="black", lw=1.4, ls="--")
ax.axvspan(4, 6, color="0.85", lw=0)                  # 구간 표시
ax.text(5, 21, "Ⅰ", ha="center", va="bottom", fontsize=9)
ax.text(9.2, 19.5, "A", fontsize=8); ax.text(9.2, 10.5, "B", fontsize=8)
ax.set_xlim(0, 10); ax.set_ylim(0, 24)
ax.set_xticks([]); ax.set_yticks([])
ax.set_xlabel("시간", fontsize=8); ax.set_ylabel("이동 거리(상댓값)", fontsize=8)
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
fig.tight_layout(pad=0.3)
fig.savefig(sys.argv[1] if len(sys.argv) > 1 else "graph.png")
print("ok")
