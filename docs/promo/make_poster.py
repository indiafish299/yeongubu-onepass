"""안내 페이지(onepass-guide.html)의 로고·연구부장님 그림을 가져와 지비톡용 세로 포스터 HTML 을 만든다.
쓰기: python make_poster.py  ->  poster.html (Edge headless --force-prefers-reduced-motion 로 1080x1350 캡처)"""
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
here = Path(__file__).resolve().parent
g = (here.parent / "onepass-guide.html").read_text(encoding="utf-8")
css = re.search(r"<style>(.*?)</style>", g, re.S).group(1)
font = re.search(r'<link rel="stylesheet"[^>]+>', g).group(0)
logo = re.search(r'(<svg viewBox="0 0 460 150".*?</svg>)', g, re.S).group(1)
boss = re.search(r'(<svg viewBox="0 0 220 290">.*?</svg>)', g, re.S).group(1)

poster = f"""<!doctype html><meta charset="utf-8">{font}
<style>{css}
html,body{{margin:0;padding:0;width:1080px;height:1350px;overflow:hidden}}
body{{background:var(--paper);font-size:30px}}
.pz{{box-sizing:border-box;width:1080px;height:1350px;padding:44px 76px 48px;display:flex;flex-direction:column;gap:24px;
  background:radial-gradient(circle at 92% 8%, color-mix(in srgb,var(--pen) 55%,transparent) 0 160px, transparent 161px), var(--paper)}}
.top{{display:grid;grid-template-columns:1fr 300px;align-items:end;gap:10px}}
.top .logo{{max-width:600px}}
.tag{{font-family:var(--body);font-size:38px;line-height:1.45;font-weight:700;margin:0}}
.steps2{{display:grid;gap:16px;margin:0;padding:0;list-style:none}}
.steps2 li{{display:grid;grid-template-columns:76px 1fr;gap:22px;align-items:center;background:var(--card);border:2px solid var(--line);border-radius:22px;padding:16px 26px}}
.steps2 b.n{{width:76px;height:76px;border-radius:50%;background:var(--pen);display:grid;place-items:center;font-family:var(--logo);font-size:44px;color:var(--pen-ink)}}
.steps2 .t{{font-size:36px;font-weight:700;line-height:1.3}}
.steps2 .s{{font-size:26px;color:var(--mut);line-height:1.4;margin-top:4px}}
.chips{{display:flex;flex-wrap:wrap;gap:12px}}
.chips span{{font-size:26px;border-radius:99px;padding:8px 20px;background:var(--card);border:2px solid var(--line)}}
.foot{{margin-top:auto;display:flex;justify-content:space-between;align-items:center;font-size:26px;color:var(--mut)}}
.foot b{{font-family:var(--logo);font-size:34px;color:var(--tag);font-weight:400}}
/* 포스터(정지 그림)에는 「패스!」 뒤 바닥에 떨어진 담뱃갑을 보인다 */
.boss .b-pack{{animation:none!important;opacity:1!important;transform:translate(33px,62px) rotate(270deg)!important}}
</style>
<div class="pz">
  <div class="top">
    <div><div class="logo">{logo}</div></div>
    <div class="boss">{boss}</div>
  </div>
  <p class="tag">시험지 원안, <span class="pen">만들고 검증까지 한 번에</span>.<br>Claude에게 말로 부탁만 하세요.</p>
  <ol class="steps2">
    <li><b class="n">1</b><div><div class="t">Claude 앱 설치·로그인</div><div class="s">claude.ai/download · 유료 요금제 · Code 탭</div></div></li>
    <li><b class="n">2</b><div><div class="t">설치 문장 한 줄 붙여 넣기</div><div class="s">쪽지 속 한 줄을 복사해 Claude에게 · 「허용」만 누르기</div></div></li>
    <li><b class="n">3</b><div><div class="t">「원패스 준비해 줘」</div><div class="s">앱을 껐다 켜고 말하기 · 로그인 창만 선생님이</div></div></li>
  </ol>
  <div class="chips">
    <span>정답 형광펜 · 선지 간격 자동</span><span>AI 여럿이 정답 모른 채 풀어 봄</span>
    <span>꼭 다시 볼 문항만 쏙</span><span>시험지는 내 컴퓨터에만</span>
  </div>
  <div class="foot"><span>윈도우·맥 · 설치 1~5분</span><b>연구부 원패스</b></div>
</div>"""
(here / "poster.html").write_text(poster, encoding="utf-8")
print(here / "poster.html")
