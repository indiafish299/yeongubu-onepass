"""exam-tools 의 집 폴더와 검토자 구성(profile.json).

집 폴더: 환경변수 EXAM_TOOLS_HOME, 없으면 ~/.exam-tools
  venv/          검증 코드용 파이썬(설치 때 만든다)
  profile.json   이 PC 에서 실제로 되는 검토자 목록(exam-setup 이 써 둔다)
  work/<이름>/   시험지마다 결과. 이 PC 로컬에만 둔다(드라이브·메신저로 보내지 않는다)
"""
import sys

sys.dont_write_bytecode = True
import json
import os
from pathlib import Path

HOME = Path(os.environ.get("EXAM_TOOLS_HOME") or (Path.home() / ".exam-tools"))
PROFILE = HOME / "profile.json"
_OLD_WORK = Path.home() / ".hermes/work/exam-verify"  # 처음 만든 맥 판의 자리(그 PC 에서는 그대로 쓴다)
WORK = Path(os.environ["EXAM_VERIFY_WORK"]) if os.environ.get("EXAM_VERIFY_WORK") else (
    _OLD_WORK if (_OLD_WORK.exists() and not os.environ.get("EXAM_TOOLS_HOME")) else HOME / "work")

# 회사별 후보(앞쪽이 먼저). exam-setup 이 짧게 불러 보고 되는 것만 profile.json 에 남긴다.
# per: 그 회사에서 검토자로 쓸 수. 요금제가 낮아 앞 모델이 안 되면 다음 모델로 내려간다.
CANDIDATES = {
    "anthropic": {"tool": "claude", "per": 2, "models": [
        ("fable", "claude-fable-5-2", "페이블 5.2"),
        ("opus", "claude-opus-5-5", "오푸스 5.5"),
        ("sonnet", "claude-sonnet-5-5", "소넷 5.5")]},
    "openai": {"tool": "codex", "per": 1, "models": [
        ("sol", "gpt-6.2-sol", "솔 6.2"),
        ("sol56", "gpt-5.6-sol", "솔 5.6")]},
    "google": {"tool": "agy", "per": 1, "models": [
        ("neon", "gemini-4-neon-xhigh", "네온"),
        ("neonh", "gemini-4-neon-high", "네온(high)"),
        ("argon", "gemini-4-argon-high", "아르곤")]},
}
VENDOR_NAME = {"anthropic": "Claude", "openai": "ChatGPT", "google": "Gemini"}

# profile.json 이 없을 때(처음 만든 맥 구성)
DEFAULT = [
    {"key": "fable", "vendor": "anthropic", "tool": "claude", "model": "claude-fable-5-2", "label": "페이블 5.2"},
    {"key": "opus", "vendor": "anthropic", "tool": "claude", "model": "claude-opus-5-5", "label": "오푸스 5.5"},
    {"key": "sol", "vendor": "openai", "tool": "codex", "model": "gpt-6.2-sol", "label": "솔 6.2"},
    {"key": "neon", "vendor": "google", "tool": "agy", "model": "gemini-4-neon-xhigh", "label": "네온"},
]


def load_profile() -> dict:
    try:
        return json.loads(PROFILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_profile(p: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    PROFILE.write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")


def reviewers() -> list:
    """쓸 검토자 목록. profile.json 의 reviewers, 없으면 DEFAULT."""
    r = load_profile().get("reviewers")
    return r if r else [dict(x) for x in DEFAULT]


def fast_model(model: str) -> str:
    """빠른 시험용(--fast) 모델. 제미나이는 낮은 단계 모델로 바꾼다(다른 회사는 추론 단계만 낮춘다)."""
    for suf in ("-xhigh", "-high", "-medium"):
        if model.startswith("gemini-") and model.endswith(suf):
            return model[: -len(suf)] + "-low"
    return model
