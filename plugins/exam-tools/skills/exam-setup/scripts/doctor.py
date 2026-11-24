"""exam-tools 점검·설치·검토자 구성.

  doctor.py check            무엇이 있고 없는지, 로그인됐는지 (바꾸는 것 없음)
  doctor.py install [VENDORS] 쓰는 AI 의 명령줄 도구를 설치·업데이트 (claude, codex; 필요하면 node)
  doctor.py probe [VENDORS]   후보 모델을 아주 짧게 불러 보고 되는 것만 profile.json 의 검토자로 적는다
  doctor.py names 이름...      가릴 칸 자동 찾기에 쓸 학교명·선생님 이름을 적어 둔다

VENDORS: anthropic,openai,google 중 쉼표로. 없으면 로그인돼 있는 회사 + anthropic.
결과는 사람이 읽는 표와 함께 마지막 줄에 JSON(@@JSON …)으로도 낸다.
"""
import sys

sys.dont_write_bytecode = True
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "exam-verify" / "engine"
sys.path.insert(0, str(ENGINE))
from exam_verify import home as H  # noqa: E402
from exam_verify import runners as R  # noqa: E402

WIN = os.name == "nt"
TOOL = {"anthropic": "claude", "openai": "codex", "google": "agy"}
LOGIN_CMD = {"claude": "claude auth login", "codex": "codex login", "agy": "agy  (처음 실행 화면에서 Google 계정으로 로그인)"}


def run(cmd, timeout=120, shell=False):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, stdin=subprocess.DEVNULL, shell=shell)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, "없음"
    except subprocess.TimeoutExpired:
        return 124, "시간 초과"


def which(name):
    for d in (Path.home() / ".local/bin", Path.home() / ".cargo/bin"):
        for ext in ((".exe", ".cmd", "") if WIN else ("",)):
            if (d / (name + ext)).exists():
                return str(d / (name + ext))
    return shutil.which(name)


def tool_state(tool):
    exe = which(tool)
    st = {"tool": tool, "installed": bool(exe), "path": exe or "", "version": "", "login": False, "note": ""}
    if not exe:
        return st
    base = R._bin(tool)
    _, v = run(base + ["--version"], 60)
    st["version"] = v.strip().splitlines()[-1][:60] if v.strip() else ""
    if tool == "claude":
        rc, out = run(base + ["auth", "status"], 60)
        try:
            st["login"] = bool(json.loads(out[out.find("{"):]).get("loggedIn"))
        except Exception:
            st["login"] = False
    elif tool == "codex":
        rc, out = run(base + ["login", "status"], 60)
        st["login"] = rc == 0 and "Logged in" in out
    elif tool == "agy":
        rc, out = run(base + ["models"], 90)
        st["login"] = rc == 0 and "gemini" in out.lower()
        if not st["login"]:
            st["note"] = out.strip()[-120:]
    return st


def hangul():
    if WIN:
        try:
            import winreg
            winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"HWPFrame.HwpObject"))
            return "한글 자동화 있음"
        except Exception:
            return ""
    apps = list(Path("/Applications").glob("Hancom*")) + list(Path("/Applications").glob("*한컴*"))
    return "한컴 앱: " + ", ".join(a.name for a in apps) if apps else ""


def check():
    tools = {t: tool_state(t) for t in ("claude", "codex", "agy")}
    env = {
        "os": f"{platform.system()} {platform.release()}",
        "python": sys.version.split()[0],
        "hangul": hangul(),
        "git": bool(which("git")), "node": bool(which("node")), "npm": bool(which("npm")),
        "uv": bool(which("uv")),
        "home": str(H.HOME), "work": str(H.WORK),
        "reviewers": [f"{r['label']}({r['model']})" for r in H.reviewers()] if H.load_profile().get("reviewers") else [],
    }
    print(f"운영체제 {env['os']} · 파이썬 {env['python']} · 한글: {env['hangul'] or '없음(PDF 는 선생님이 한글에서 저장)'}")
    print(f"git {'있음' if env['git'] else '없음'} · node {'있음' if env['node'] else '없음'} · uv {'있음' if env['uv'] else '없음'}")
    for v, t in TOOL.items():
        s = tools[t]
        state = ("로그인됨" if s["login"] else "로그인 필요") if s["installed"] else "없음"
        print(f"{H.VENDOR_NAME[v]:8s} {t:6s} {state:6s} {s['version']}")
    print("검토자 구성: " + (", ".join(env["reviewers"]) or "아직 없음(probe 를 돌린다)"))
    print("@@JSON " + json.dumps({"env": env, "tools": tools}, ensure_ascii=False))
    return env, tools


def vendors_arg(args, tools=None):
    if args:
        return [v.strip() for v in args[0].split(",") if v.strip() in TOOL]
    tools = tools or {t: tool_state(t) for t in TOOL.values()}
    vs = [v for v, t in TOOL.items() if tools[t]["login"]]
    return vs if "anthropic" in vs else ["anthropic"] + vs


def install(args):
    vs = vendors_arg(args)
    done = []
    if "anthropic" in vs and not which("claude"):
        cmd = ("irm https://claude.ai/install.ps1 | iex" if WIN else "curl -fsSL https://claude.ai/install.sh | bash")
        rc, out = run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd] if WIN
                      else ["bash", "-lc", cmd], 900)
        done.append(f"claude 설치 {'됨' if rc == 0 else '실패: ' + out.strip()[-200:]}")
    if "openai" in vs:
        if not which("npm"):
            if WIN and which("winget"):
                rc, out = run(["winget", "install", "-e", "--id", "OpenJS.NodeJS.LTS", "--silent",
                               "--accept-package-agreements", "--accept-source-agreements",
                               "--disable-interactivity"], 900)
                done.append(f"node 설치 {'됨' if rc == 0 else '실패: ' + out.strip()[-200:]}")
                os.environ["PATH"] += os.pathsep + r"C:\Program Files\nodejs"
            elif not WIN and which("brew"):
                rc, out = run(["brew", "install", "node"], 1800)
                done.append(f"node 설치 {'됨' if rc == 0 else '실패: ' + out.strip()[-200:]}")
            else:
                done.append("node 없음 — https://nodejs.org 에서 LTS 를 설치해야 codex 를 깔 수 있다")
        npm = which("npm")
        if npm:
            rc, out = run([npm, "install", "-g", "@openai/codex@latest"], 900, shell=WIN)
            _, v = run(R._bin("codex") + ["--version"], 60)
            done.append(f"codex 최신판 {'설치됨' if rc == 0 else '실패: ' + out.strip()[-200:]} ({v.strip()[-20:]})")
    if "google" in vs and not which("agy"):
        done.append("agy(Antigravity CLI) 없음 — Google Antigravity 를 설치하면 함께 들어온다. 자동 설치는 하지 않는다")
    for d in done:
        print(d)
    if not done:
        print("설치할 것 없음")
    print("@@JSON " + json.dumps({"installed": done, "vendors": vs}, ensure_ascii=False))


def probe(args):
    tools = {t: tool_state(t) for t in TOOL.values()}
    vs = vendors_arg(args, tools)
    chosen, tried = [], []
    for v in vs:
        c = H.CANDIDATES[v]
        if not tools[c["tool"]]["login"]:
            tried.append({"vendor": v, "skip": f"{c['tool']} 로그인 필요: {LOGIN_CMD[c['tool']]}"})
            print(f"{H.VENDOR_NAME[v]}: 건너뜀 — {c['tool']} 로그인 필요 ({LOGIN_CMD[c['tool']]})")
            continue
        got = 0
        for key, model, label in c["models"]:
            if got >= c["per"]:
                break
            r = R.ping(v, c["tool"], model)
            tried.append({**r, "key": key})
            print(f"{H.VENDOR_NAME[v]} {label}({model}): {'됨' if r['ok'] else '안 됨 — ' + r['error'][:100]}")
            if r["ok"]:
                chosen.append({"key": key, "vendor": v, "tool": c["tool"], "model": model, "label": label})
                got += 1
    p = H.load_profile()
    if chosen:
        p["reviewers"] = chosen
    p["probe"] = tried
    H.save_profile(p)
    n_v = len({c["vendor"] for c in chosen})
    print(f"검토자 {len(chosen)}명 ({n_v}개 회사): " + ", ".join(c["label"] for c in chosen))
    if n_v == 1:
        print("한 회사 모델만 있다 → 반박은 같은 회사의 다른 모델이 맡고, 보고서에 그렇게 적힌다")
    print("@@JSON " + json.dumps({"reviewers": chosen, "tried": tried}, ensure_ascii=False))


def names(args):
    p = H.load_profile()
    p["names"] = [a for a in args if a.strip()]
    H.save_profile(p)
    print("가릴 이름: " + ", ".join(p["names"]))


if __name__ == "__main__":
    cmd, rest = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("check", [])
    {"check": lambda a: check(), "install": install, "probe": probe, "names": names}[cmd](rest)
