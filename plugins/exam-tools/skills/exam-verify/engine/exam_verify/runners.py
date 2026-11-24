"""검토자 모델을 구독 명령줄 도구(claude·codex·agy)로 한 번씩 부른다. 누가 검토자인지는 home.reviewers().

원칙: 모델이 볼 수 있는 것은 box 폴더의 쪽 이미지뿐이다. 실행 기록의 도구 호출을 검사해
box 밖 파일을 읽었거나 명령·웹을 썼으면 그 실행을 무효(격리 위반)로 돌려준다.
"""
import sys

sys.dont_write_bytecode = True
import json
import os
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exam_verify import home as H  # noqa: E402

HOME = Path.home()
BIN = HOME / ".local/bin"
CODEX_HOME = H.WORK / "_codex_home"  # auth.json 만 이어 둔 빈 설정 폴더


def _bin(name: str) -> list:
    """실행할 명령의 앞부분(목록). 맥은 ~/.local/bin, 없으면(윈도우 등) PATH 에서 찾는다.

    윈도우의 npm 명령(codex.cmd)은 cmd.exe 를 거치는데, cmd.exe 는 인자의 줄바꿈에서 명령을 잘라
    여러 줄 프롬프트의 첫 줄만 넘긴다(11/24 확인: JSON 지시가 빠져 솔이 맨글로 답함).
    그래서 .cmd 면 그 안의 node 스크립트를 node 로 직접 부른다."""
    p = BIN / name
    exe = str(p) if p.exists() else (shutil.which(name) or name)
    if os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
        js = Path(exe).parent / "node_modules/@openai/codex/bin/codex.js" if name == "codex" else None
        node = Path(exe).parent / "node.exe"
        node = str(node) if node.exists() else (shutil.which("node") or "node")
        if js and js.exists():
            return [node, str(js)]
    return [exe]


# 다시 해 봐도 소용없는 실패(로그인·모델 이름). 세 번 되풀이하지 않고 바로 알린다.
FATAL = ("Not logged in", "Failed to authenticate", "OAuth session expired", "model_not_found",
         "is not supported when using Codex")

# key: (회사, 도구, 모델 ID) — profile.json 의 검토자 + 고를 수 있는 모든 후보(--models 로 직접 고를 때)
MODELS, LABEL = {}, {}
for _v, _c in H.CANDIDATES.items():
    for _k, _m, _l in _c["models"]:
        MODELS[_k], LABEL[_k] = (_v, _c["tool"], _m), _l
for _r in H.reviewers():
    MODELS[_r["key"]], LABEL[_r["key"]] = (_r["vendor"], _r["tool"], _r["model"]), _r.get("label", _r["key"])
ACTIVE = [r["key"] for r in H.reviewers()]  # run 의 기본 검토자
# 그 PC·계정에서만 이름이 다를 때: EXAM_VERIFY_MODELS="sol=gpt-5.6-sol" (보고서에는 실제 부른 이름이 남는다)
for _kv in filter(None, os.environ.get("EXAM_VERIFY_MODELS", "").split(",")):
    _k, _, _v = _kv.partition("=")
    if _k.strip() in MODELS and _v.strip():
        MODELS[_k.strip()] = MODELS[_k.strip()][:2] + (_v.strip(),)


def vendor(key: str) -> str:
    return MODELS[key][0]


def _inside(path: str, box: Path) -> bool:
    try:
        Path(path).resolve().relative_to(box.resolve())
        return True
    except Exception:
        return False


def _proc(cmd, cwd, env=None, timeout=3600):
    e = dict(os.environ)
    if env:
        e.update(env)
    # 모델 출력은 UTF-8. 윈도우 기본(cp949)으로 풀면 한글이 깨지거나 예외가 난다.
    p = subprocess.run(cmd, cwd=str(cwd), env=e, stdin=subprocess.DEVNULL, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def _lines(out: str):
    for line in out.splitlines():
        try:
            yield json.loads(line)
        except Exception:
            continue


def _claude(model, prompt, box, images, fast):
    cmd = _bin("claude") + ["-p", prompt, "--model", model, "--tools", "Read",
           "--strict-mcp-config", "--setting-sources", "", "--disable-slash-commands",
           "--no-session-persistence", "--output-format", "stream-json", "--verbose",
           "--effort", "low" if fast else "max"]
    rc, out, err = _proc(cmd, box)
    text, tools, bad, reported, error = "", [], [], "", ""
    for o in _lines(out):
        if o.get("type") == "assistant":
            reported = o.get("message", {}).get("model", reported)
            for c in o.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    path = c.get("input", {}).get("file_path", "")
                    tools.append(f"{c.get('name')}:{path}")
                    if c.get("name") != "Read" or not _inside(path, box):
                        bad.append(tools[-1])
        elif o.get("type") == "result":
            text = o.get("result", "")
            if o.get("is_error"):
                error = text or "오류"
    if rc != 0 and not error:
        error = (err or "실패").strip()[:300]
    return text, tools, bad, reported, error, {}


def _codex(model, prompt, box, images, fast):
    CODEX_HOME.mkdir(parents=True, exist_ok=True)
    link = CODEX_HOME / "auth.json"
    if not link.exists():
        try:
            link.symlink_to(HOME / ".codex/auth.json")
        except OSError:  # 윈도우는 링크 권한이 없을 수 있다. 그때는 복사(로그인을 새로 하면 이 파일을 지운다).
            shutil.copyfile(HOME / ".codex/auth.json", link)
    cmd = _bin("codex") + ["exec", "-m", model, "-s", "read-only", "--skip-git-repo-check",
           "--ephemeral", "--json", "-c", 'web_search="disabled"',
           "-c", f'model_reasoning_effort="{"low" if fast else "xhigh"}"']
    for f in ("shell_tool", "unified_exec", "plugins", "apps", "browser_use", "computer_use",
              "multi_agent", "image_generation"):
        cmd += ["--disable", f]
    for p in images:
        cmd += ["-i", str(p)]
    cmd += ["--", prompt]
    rc, out, err = _proc(cmd, box, env={"CODEX_HOME": str(CODEX_HOME)})
    text, tools, bad, error, warn = "", [], [], "", ""
    for o in _lines(out):
        item = o.get("item") or {}
        if o.get("type") == "item.completed":
            if item.get("type") == "agent_message":
                text = item.get("text", "")
            elif item.get("type") == "error":  # 경고(예: 모델 정보 없음)이지 도구 호출이 아니다
                warn = item.get("message", "")
            elif item.get("type") not in ("reasoning",):
                tools.append(item.get("type", "?"))
                bad.append(tools[-1])  # 이미지는 붙여 주므로 어떤 도구 호출도 필요 없다
        elif o.get("type") in ("error", "turn.failed"):
            error = json.dumps(o, ensure_ascii=False)[:300]
    if rc != 0 and not error:
        error = (err or "실패").strip()[-300:]
    return text, tools, bad, model, error, ({"warning": warn} if warn else {})


def _agy(model, prompt, box, images, fast):
    cmd = _bin("agy") + ["-p", prompt, "--model", model, "--sandbox",
           "--disable-slash-commands", "--output-format", "stream-json"]
    rc, out, err = _proc(cmd, box)
    text, tools, bad, reported, error, extra = "", [], [], model, "", {}
    for o in _lines(out):
        ev = o.get("event")
        if ev == "init":
            reported = o.get("init", {}).get("model", model)
            extra["conversation_id"] = o.get("conversation_id", "")
        elif ev == "step_update":
            su = o["step_update"]
            if su.get("step_type") == "tool" and su.get("state") == "DONE":
                params = (su.get("tool_info") or {}).get("parameters") or {}
                path = params.get("Path") or params.get("AbsolutePath") or ""
                tools.append(f"{su.get('tool_name')}:{path}")
                if su.get("tool_name") not in ("read_file", "view_file") or not _inside(path, box):
                    bad.append(tools[-1])
        elif ev == "result":
            r = o.get("result", {})
            text = r.get("response", "")
            if r.get("status") != "SUCCESS":
                error = json.dumps(r, ensure_ascii=False)[:300]
    if rc != 0 and not error:
        error = (err or "실패").strip()[-300:]
    return text, tools, bad, reported, error, extra


_TOOLS = {"claude": _claude, "codex": _codex, "agy": _agy}


def ping(vendor_: str, tool: str, model: str, timeout: int = 300) -> dict:
    """그 모델을 이 PC·계정으로 부를 수 있는지 아주 짧게 확인한다(시험 내용 없음, 낮은 추론 단계)."""
    import tempfile

    box = Path(tempfile.mkdtemp(prefix="exam_ping_"))
    try:
        text, tools, bad, reported, error, _ = _TOOLS[tool](model, "「확인」이라는 낱말 하나만 답하라. 파일은 읽지 마라.",
                                                            box, [], True)
    except subprocess.TimeoutExpired:
        text, error, reported = "", "시간 초과", model
    except FileNotFoundError:
        text, error, reported = "", f"{tool} 명령 없음", model
    finally:
        shutil.rmtree(box, ignore_errors=True)
    if not error and not text.strip():
        error = "빈 응답"
    return {"vendor": vendor_, "tool": tool, "model": model, "ok": not error, "error": error[:300],
            "reported": reported}


def call(key: str, prompt: str, box: Path, fast: bool = False, tries: int = 3) -> dict:
    """모델 하나를 부른다. 실패하면 두 번 더 해 본다. 결과는 dict(ok, text, ...)."""
    _, tool, model = MODELS[key]
    if fast:
        model = H.fast_model(model)
    images = sorted(box.glob("page-*.png"))
    last = {}
    for attempt in range(1, tries + 1):
        try:
            text, tools, bad, reported, error, extra = _TOOLS[tool](model, prompt, box, images, fast)
        except subprocess.TimeoutExpired:
            text, tools, bad, reported, error, extra = "", [], [], model, "시간 초과", {}
        if bad:
            error = "격리 위반: " + ", ".join(bad)[:300]
        if not error and not text.strip():
            error = "빈 응답"
        last = {"model": key, "model_id": model, "model_reported": reported, "tool": tool,
                "ok": not error, "error": error, "text": text, "tool_calls": tools,
                "attempts": attempt, **extra}
        if last["ok"] or bad or any(s in error for s in FATAL):
            break
    return last
