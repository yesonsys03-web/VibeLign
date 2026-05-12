"""Regenerate tokenizer parity goldens.

Run when `patch_suggester` 의 leaf 함수 또는 alias table (`_TOKEN_ALIASES`,
`_KOREAN_ALIAS_KEYS`, `_KOREAN_PARTICLE_SUFFIXES`) 가 변경되면 재실행.

Output: `tests/fixtures/tokenizer_goldens/<function>.expected.json` 6개 파일.

Python is the source of truth — Rust port (planned 2026-05-13~) 는 동일 입력에
대해 byte-equal expected 를 반환해야 한다. 순서/중복 제거 정책 (`_expand_token`
의 dedup, `tokenize` 의 dict.fromkeys-equivalent) 까지 보존.

Usage (from repo root):
    uv run python tests/fixtures/tokenizer_goldens/_regenerate.py
"""

from __future__ import annotations

import json
from pathlib import Path

from vibelign.core.patch_suggester import (
    _decompose_korean_compound,
    _expand_token,
    _intent_tokens,
    _normalize_korean_token,
    _split_identifier_parts,
    tokenize,
)


# (description, input) — 한 입력 셋을 모든 leaf 함수에 통과시킨다.
# 카테고리:
#  A. English basic / camelCase / snake_case / 숫자
#  B. Korean alias-known single (`_TOKEN_ALIASES` key)
#  C. Korean alias-unknown
#  D. Korean compound (decomposable into 2+ alias keys)
#  E. Korean particle suffix
#  F. Mixed Korean+English / sentence
#  G. Edge: empty / single char / numeric / special
CASES: list[tuple[str, str]] = [
    # A. English basic
    ("A01 english single", "button"),
    ("A02 english single", "login"),
    ("A03 english single", "submit"),
    ("A04 english single", "form"),
    ("A05 english single", "menu"),
    ("A06 english single", "search"),
    ("A07 english single", "settings"),
    ("A08 english single", "panel"),
    ("A09 english single", "modal"),
    ("A10 english single", "icon"),
    ("A11 camelCase", "loginButton"),
    ("A12 camelCase", "submitForm"),
    ("A13 camelCase", "handleClick"),
    ("A14 camelCase", "useEffect"),
    ("A15 PascalCase", "LoginPage"),
    ("A16 PascalCase", "ClaudeHookCard"),
    ("A17 snake_case", "user_id"),
    ("A18 snake_case", "api_key_value"),
    ("A19 snake_case + digit", "v2_login"),
    ("A20 snake_case + digit", "test_case_123"),
    ("A21 digit only", "12345"),
    ("A22 alpha + digit", "button123"),
    # B. Korean alias-known single (verified against _TOKEN_ALIASES keys)
    ("B01 alias-known", "훅"),
    ("B02 alias-known", "로그인"),
    ("B03 alias-known", "회원가입"),
    ("B04 alias-known", "메뉴"),
    ("B05 alias-known", "홈"),
    ("B06 alias-known", "화면"),
    ("B07 alias-known", "토큰"),
    ("B08 alias-known", "설정"),
    ("B09 alias-known", "버전"),
    ("B10 alias-known", "비밀번호"),
    ("B11 alias-known", "비활성화"),
    ("B12 alias-known compound-as-key", "메인화면"),
    ("B13 alias-known compound-as-key", "시작화면"),
    ("B14 alias-known compound-as-key", "홈화면"),
    # C. Korean alias-unknown
    ("C01 alias-unknown", "이상한단어"),
    ("C02 alias-unknown", "햇볕"),
    ("C03 alias-unknown", "구름"),
    ("C04 alias-unknown", "감자"),
    ("C05 alias-unknown", "강아지"),
    ("C06 alias-unknown long", "허클거리는바람"),
    # D. Korean compound — non-decomposable (D01~D10) + decomposable (D11~D20).
    #    decompose() 는 *모든* 부분이 alias key 일 때만 분해. 한 부분이라도 alias 가
    #    아니면 [] 반환. 두 가지 path 모두 fixture 에 포함하여 Rust port 가 동일한
    #    fail-fast 동작을 갖도록 검증.
    ("D01 non-decomposable (버튼 not alias)", "로그인버튼"),
    ("D02 decomposable", "회원가입화면"),
    ("D03 non-decomposable (변경 not alias)", "비밀번호변경"),
    ("D04 non-decomposable (버튼 not alias)", "메뉴버튼"),
    ("D05 non-decomposable (검색 not alias)", "검색버튼"),
    ("D06 decomposable", "설정화면"),
    ("D07 non-decomposable (테마 not alias)", "테마설정"),
    ("D08 non-decomposable (버튼 not alias)", "비활성화버튼"),
    ("D09 non-decomposable (버튼 not alias)", "홈버튼"),
    ("D10 non-decomposable triple (버튼 not alias)", "로그인화면버튼"),
    ("D11 decomposable", "로그인화면"),
    ("D12 decomposable", "사용자설정"),
    ("D13 decomposable", "비밀번호설정"),
    ("D14 decomposable", "활성화상태"),
    ("D15 decomposable", "토큰발급"),
    ("D16 decomposable", "프로필설정"),
    ("D17 decomposable", "이메일발급"),
    ("D18 decomposable", "메뉴화면"),
    ("D19 decomposable triple", "프로필설정화면"),
    ("D20 decomposable triple", "로그인화면설정"),
    # E. Korean particle suffix
    ("E01 particle 을", "버튼을"),
    ("E02 particle 이", "로그인이"),
    ("E03 particle 에", "홈에"),
    ("E04 particle 에서", "메뉴에서"),
    ("E05 particle 는", "화면는"),
    ("E06 particle 도", "설정도"),
    ("E07 particle 와", "테마와"),
    ("E08 particle 의", "검색의"),
    ("E09 particle 가", "버튼가"),
    ("E10 particle 까지", "로그인까지"),
    ("E11 particle 부터", "홈부터"),
    ("E12 particle 보다", "메뉴보다"),
    ("E13 particle 라고", "버튼라고"),
    ("E14 particle 처럼", "홈처럼"),
    ("E15 particle 입니다 — trim 미발동 (token 4 ≤ suffix 3+1)", "홈입니다"),
    # F. Mixed Korean+English / sentence
    ("F01 한국어 + space + english", "로그인 button"),
    ("F02 english + 한국어", "submit버튼"),
    ("F03 phrase english", "click the submit button"),
    ("F04 phrase 한국어", "로그인 버튼을 눌러주세요"),
    ("F05 phrase mixed", "Login 화면에서 비밀번호 변경"),
    ("F06 path-like", "src/components/LoginButton.tsx"),
    ("F07 path-like 한글", "src/components/로그인버튼.tsx"),
    ("F08 path snake + camel", "src/anchor_tools/ClaudeHookCard.ts"),
    ("F09 with digits", "user_42 화면 v2"),
    ("F10 emoji adjacent", "로그인 ✨ 버튼"),
    # G. Edge cases
    ("G01 empty", ""),
    ("G02 single space", " "),
    ("G03 single english char", "a"),
    ("G04 single digit", "1"),
    ("G05 single korean char", "가"),
    ("G06 special only", "@#$%"),
    ("G07 dots", "..."),
    ("G08 mixed special + alpha", "hello-world!"),
    ("G09 underscore only", "___"),
    ("G10 newline", "first\nsecond"),
    ("G11 tab", "first\tsecond"),
    ("G12 multi-space", "a    b"),
    ("G13 long english", "thisIsAVeryLongCamelCaseIdentifierName"),
    ("G14 long korean", "로그인버튼화면메뉴설정테마"),
    ("G15 mixed case rapid switch", "abCDef로그인XY"),
]


FIXTURE_DIR = Path(__file__).resolve().parent


def _normalize_output(value: object) -> object:
    """Sets → sorted list for stable JSON output. Lists pass through."""
    if isinstance(value, set):
        return sorted(value)
    return value


def regenerate() -> None:
    functions: list[tuple[str, object]] = [
        ("_decompose_korean_compound", _decompose_korean_compound),
        ("_split_identifier_parts", _split_identifier_parts),
        ("_normalize_korean_token", _normalize_korean_token),
        ("_expand_token", _expand_token),
        ("tokenize", tokenize),
        ("_intent_tokens", _intent_tokens),
    ]

    for name, func in functions:
        cases_output = []
        for desc, inp in CASES:
            out = func(inp)
            cases_output.append(
                {
                    "description": desc,
                    "input": inp,
                    "expected": _normalize_output(out),
                }
            )

        path = FIXTURE_DIR / f"{name}.expected.json"
        payload = {
            "function": name,
            "source": "vibelign/core/patch_suggester.py",
            "case_count": len(cases_output),
            "cases": cases_output,
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {path.name}: {len(cases_output)} cases")


if __name__ == "__main__":
    regenerate()
