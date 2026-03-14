# === ANCHOR: CODESPEAK_START ===
import re
from dataclasses import dataclass, asdict


ACTION_MAP = {
    "add": ["add", "insert", "create", "append", "new", "make", "build"],
    "remove": ["remove", "delete", "drop", "clear", "clean"],
    "fix": ["fix", "repair", "resolve", "debug", "handle", "catch"],
    "update": ["update", "change", "edit", "modify", "improve", "enhance", "upgrade"],
    "split": ["split", "separate", "divide", "extract", "refactor"],
    "apply": ["apply", "set", "enable", "activate"],
}

LAYER_MAP = {
    "ui": [
        "button",
        "window",
        "dialog",
        "layout",
        "sidebar",
        "toolbar",
        "panel",
        "screen",
        "render",
        "widget",
        "progress",
        "menu",
    ],
    "service": ["login", "auth", "register", "user", "session", "token", "password"],
    "engine": ["patch", "anchor", "guard", "scan", "analyze", "build", "compile"],
    "api": ["request", "fetch", "http", "endpoint", "route", "server", "response"],
    "data": [
        "db",
        "database",
        "model",
        "schema",
        "store",
        "cache",
        "json",
        "yaml",
        "file",
        "save",
        "load",
    ],
    "cli": ["command", "arg", "flag", "option", "help", "output", "print"],
}

STOPWORDS = {
    "a",
    "an",
    "the",
    "to",
    "for",
    "with",
    "and",
    "of",
    "in",
    "on",
    "please",
    "my",
    "this",
    "that",
    "me",
}

TARGET_HINTS = {
    "ui": "component",
    "service": "auth",
    "engine": "pipeline",
    "api": "endpoint",
    "data": "resource",
    "cli": "command",
    "core": "patch",
}


@dataclass
class CodeSpeakResult:
    codespeak: str
    layer: str
    target: str
    subject: str
    action: str
    confidence: str
    interpretation: str
    clarifying_questions: list[str]

    def to_dict(self):
        return asdict(self)


def tokenize_request(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z_]+", text.lower())


def _infer_action(tokens: list[str]) -> tuple[str, int]:
    for action, words in ACTION_MAP.items():
        for token in tokens:
            if token in words:
                return action, 2
    return "update", 0


def _infer_layer(tokens: list[str]) -> tuple[str, int]:
    for layer, words in LAYER_MAP.items():
        for token in tokens:
            if token in words:
                return layer, 2
    return "core", 0


def _infer_target(tokens: list[str], layer: str) -> str:
    if layer == "ui":
        if "layout" in tokens or "sidebar" in tokens or "toolbar" in tokens:
            return "layout"
        return "component"
    if layer == "service" and "login" in tokens:
        return "auth"
    return TARGET_HINTS.get(layer, "patch")


def _infer_subject(tokens: list[str], layer: str, action: str) -> tuple[str, int]:
    excluded = set(STOPWORDS)
    excluded.add(action)
    for words in ACTION_MAP.values():
        excluded.update(words)
    candidates = [token for token in tokens if token not in excluded]
    if not candidates:
        return f"{layer}_request", 0
    if candidates[:2] == ["progress", "bar"]:
        return "progress_bar", 2
    if len(candidates) >= 2 and candidates[0] == "side" and candidates[1] == "bar":
        return "sidebar", 2
    return "_".join(candidates[:2]), 1


def build_codespeak(request: str) -> CodeSpeakResult:
    tokens = tokenize_request(request)
    action, action_score = _infer_action(tokens)
    layer, layer_score = _infer_layer(tokens)
    target = _infer_target(tokens, layer)
    subject, subject_score = _infer_subject(tokens, layer, action)
    total = action_score + layer_score + subject_score
    confidence = "high" if total >= 5 else "medium" if total >= 3 else "low"
    clarifying_questions = []
    if confidence == "low":
        clarifying_questions = [
            "어느 화면이나 파일을 바꾸고 싶은지 더 구체적으로 말해줄 수 있나요?",
            "추가인지 수정인지, 또는 버그 수정인지 알려줄 수 있나요?",
        ]
    interpretation = (
        f"'{request}' 요청을 {layer} 영역의 {subject} {action} 작업으로 해석했습니다."
    )
    return CodeSpeakResult(
        codespeak=f"{layer}.{target}.{subject}.{action}",
        layer=layer,
        target=target,
        subject=subject,
        action=action,
        confidence=confidence,
        interpretation=interpretation,
        clarifying_questions=clarifying_questions,
    )
# === ANCHOR: CODESPEAK_END ===
