# === ANCHOR: MCP_TOOL_SPECS_START ===
from typing import TypedDict


# === ANCHOR: MCP_TOOL_SPECS_TOOLSPEC_START ===
class ToolSpec(TypedDict):
    name: str
    description: str
    inputSchema: dict[str, object]
# === ANCHOR: MCP_TOOL_SPECS_TOOLSPEC_END ===


TOOL_SPECS: tuple[ToolSpec, ...] = (
    {
        "name": "checkpoint_create",
        "description": "현재 프로젝트 상태를 체크포인트로 저장합니다. 작업 전 반드시 호출하세요.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "체크포인트 설명 (예: '로그인 완성')",
                }
            },
            "required": ["message"],
        },
    },
    {
        "name": "checkpoint_list",
        "description": "저장된 체크포인트 목록을 반환합니다.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "checkpoint_restore",
        "description": "특정 체크포인트로 프로젝트를 복원합니다. checkpoint_list로 ID를 확인 후 사용하세요.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "checkpoint_id": {
                    "type": "string",
                    "description": "복원할 체크포인트 ID",
                }
            },
            "required": ["checkpoint_id"],
        },
    },
    {
        "name": "checkpoint_diff",
        "description": "두 저장 지점 사이에 바뀐 파일 요약을 JSON으로 반환합니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "from_checkpoint_id": {"type": "string", "description": "이전 저장 ID"},
                "to_checkpoint_id": {"type": "string", "description": "나중 저장 ID"},
            },
            "required": ["from_checkpoint_id", "to_checkpoint_id"],
        },
    },
    {
        "name": "checkpoint_preview_restore",
        "description": "되돌리기 전에 어떤 파일이 바뀔지 JSON으로 미리 확인합니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "checkpoint_id": {"type": "string", "description": "확인할 저장 ID"},
                "relative_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "일부 파일만 확인할 때의 파일 경로 목록",
                },
            },
            "required": ["checkpoint_id"],
        },
    },
    {
        "name": "checkpoint_restore_files",
        "description": "선택한 파일만 저장 지점의 내용으로 되돌립니다. 다른 파일은 그대로 둡니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "checkpoint_id": {"type": "string", "description": "복원할 저장 ID"},
                "relative_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "되돌릴 파일 경로 목록",
                },
            },
            "required": ["checkpoint_id", "relative_paths"],
        },
    },
    {
        "name": "checkpoint_restore_suggestions",
        "description": "되돌릴 때 먼저 확인하면 좋은 파일 추천을 JSON으로 반환합니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "checkpoint_id": {"type": "string", "description": "추천을 받을 저장 ID"},
                "cap": {"type": "integer", "description": "추천 개수 상한 (기본값: 5)"},
            },
            "required": ["checkpoint_id"],
        },
    },
    {
        "name": "checkpoint_has_changes",
        "description": "해당 저장 지점 이후 파일 변경이 있는지 JSON으로 반환합니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "checkpoint_id": {"type": "string", "description": "비교할 저장 ID"}
            },
            "required": ["checkpoint_id"],
        },
    },
    {
        "name": "retention_apply",
        "description": "오래된 자동 저장을 안전 규칙에 따라 정리하고 결과를 JSON으로 반환합니다.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "project_context_get",
        "description": (
            "현재 프로젝트의 요약 컨텍스트를 생성합니다. "
            "토큰이 부족하거나 AI 툴을 바꿀 때 이 내용을 새 AI에게 전달하면 "
            "어떤 프로젝트인지, 어떤 작업을 하고 있었는지 즉시 파악할 수 있습니다. "
            "토큰 절약에도 효과적입니다."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "compact": {
                    "type": "boolean",
                    "description": "간략 모드 — 파일 트리 깊이 2 (기본값: false)",
                },
                "full": {
                    "type": "boolean",
                    "description": "전체 모드 — 파일 트리 깊이 4 (기본값: false)",
                },
            },
        },
    },
    {
        "name": "doctor_run",
        "description": "프로젝트 건강 진단을 실행합니다. 점수, 상태, 권장 조치를 JSON으로 반환합니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "strict": {
                    "type": "boolean",
                    "description": "엄격 모드 (기본값: false)",
                }
            },
        },
    },
    {
        "name": "guard_check",
        "description": "프로젝트 상태와 최근 변경사항을 분석하여 안전 여부를 판단합니다. pass/warn/fail 반환.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "strict": {
                    "type": "boolean",
                    "description": "엄격 모드 — warn도 fail로 처리 (기본값: false)",
                },
                "since_minutes": {
                    "type": "integer",
                    "description": "최근 N분 이내 변경사항 분석 (기본값: 30)",
                },
            },
        },
    },
    {
        "name": "protect_add",
        "description": "파일을 보호 목록에 추가합니다. AI가 수정하면 안 되는 파일을 등록하세요.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "보호할 파일의 상대 경로 목록",
                }
            },
            "required": ["file_paths"],
        },
    },
    {
        "name": "patch_get",
        "description": (
            "사용자의 자연어 요청을 CodeSpeak(구조화된 수정 지시어)로 번역하고, "
            "프로젝트 앵커 인덱스를 검색하여 수정할 파일과 정확한 위치(target_anchor)를 특정합니다. "
            "코드를 수정하기 전에 반드시 이 도구를 먼저 호출하고, "
            "반환된 target_file과 target_anchor 범위 안에서만 수정하세요."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "request": {
                    "type": "string",
                    "description": "수정 요청 (예: '로그인 버튼 크기 키워줘')",
                },
                "lazy_fanout": {
                    "type": "boolean",
                    "description": (
                        "다중 의도가 있을 때 첫 의도만 상세 계획하고 "
                        "나머지는 pending_sub_intents로 돌려 비용을 줄임"
                    ),
                },
            },
            "required": ["request"],
        },
    },
    {
        "name": "patch_apply",
        "description": (
            "Strict Patch JSON을 validator 규칙으로 검증한 뒤 정확히 한 번 매치될 때만 적용합니다. "
            "적용 직전에 자동 checkpoint를 생성합니다. "
            "dry_run=true이면 검증만 하고 파일을 쓰지 않으며 checkpoint도 만들지 않습니다."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "strict_patch": {
                    "type": "object",
                    "description": "patch_get 또는 handoff prompt에서 얻은 Strict Patch JSON",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "true면 검증만 수행 (워크스페이스 변경·checkpoint 없음)",
                },
            },
            "required": ["strict_patch"],
        },
    },
    {
        "name": "handoff_create",
        "description": (
            "현재 AI 세션 요약을 받아 PROJECT_CONTEXT.md 상단에 Session Handoff 블록을 생성합니다. "
            "토큰 한도 도달 또는 AI 툴 전환 직전에 호출하세요. "
            "새 AI가 이 블록을 읽으면 즉시 작업을 이어갈 수 있습니다."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_summary": {
                    "type": "string",
                    "description": "현재 세션에서 작업한 내용 요약 (한두 줄 bullet)",
                },
                "first_next_action": {
                    "type": "string",
                    "description": "다음 AI가 가장 먼저 해야 할 일 (한 줄)",
                },
                "completed_work": {
                    "type": "string",
                    "description": "현재 세션 변경 기록 또는 완료된 작업 요약 (선택)",
                },
                "unfinished_work": {
                    "type": "string",
                    "description": "미완료 작업 요약 (선택)",
                },
                "decision_context": {
                    "type": "object",
                    "description": "방향 전환 컨텍스트 (선택)",
                    "properties": {
                        "tried": {"type": "string"},
                        "blocked_by": {"type": "string"},
                        "switched_to": {"type": "string"},
                    },
                },
                "notes": {
                    "type": "string",
                    "description": "추가 메모나 블로커 (선택)",
                },
            },
            "required": ["session_summary", "first_next_action"],
        },
    },
    {
        "name": "anchor_run",
        "description": (
            "앵커가 없는 파일에 앵커를 자동으로 삽입합니다. "
            "코드 수정 작업 전 반드시 호출하세요. "
            "앵커가 있어야 AI가 정확한 위치를 찾아 수정할 수 있습니다."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "anchor_list",
        "description": "프로젝트의 앵커 인덱스를 반환합니다. vib scan을 먼저 실행해야 합니다.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "anchor_auto_intent",
        "description": (
            "모든 앵커에 대해 코드 기반 + AI 기반으로 intent/aliases/description을 "
            "anchor_meta.json에 생성합니다. patch_suggester 스코어링 품질 향상을 위해 "
            "앵커 삽입 후 반드시 한 번 실행하세요. "
            "기존 수동/AI 메타는 보존되며, force=true일 때만 재생성됩니다."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "force": {
                    "type": "boolean",
                    "description": "true면 기존 AI/수동 메타도 재생성 (기본값: false)",
                },
                "only_ext": {
                    "type": "string",
                    "description": "특정 확장자만 처리 (예: '.py,.ts')",
                },
            },
        },
    },
    {
        "name": "anchor_set_intent",
        "description": (
            "특정 앵커에 의도(intent)와 별칭(aliases)·설명(description)·경고(warning)·"
            "연결(connects)을 직접 등록합니다. "
            "이 메타는 _source='manual'로 표시되어 auto_intent 실행 시 보존됩니다."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "anchor_name": {
                    "type": "string",
                    "description": "앵커 이름 (_START/_END 접미사 없이)",
                },
                "intent": {
                    "type": "string",
                    "description": "한 줄 의도 설명",
                },
                "aliases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "검색 별칭 (한국어/영어 혼합 가능)",
                },
                "description": {
                    "type": "string",
                    "description": "상세 설명 (선택)",
                },
                "warning": {
                    "type": "string",
                    "description": "AI에게 전달할 주의사항 (선택)",
                },
                "connects": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "연결된 앵커 이름 목록 (선택)",
                },
            },
            "required": ["anchor_name", "intent"],
        },
    },
    {
        "name": "transfer_set_decision",
        "description": "현재 세션의 의사결정을 work_memory.decisions 에 누적합니다. PROJECT_CONTEXT.md 의 active_intent / Decision context 에 자동 반영됩니다. 두 옵션 사이에서 선택할 때, 의도가 바뀔 때 호출하세요. WHY 포함 권장.",
        "inputSchema": {
            "type": "object",
            "required": ["text"],
            "properties": {"text": {"type": "string", "description": "결정 내용 한 줄."}},
        },
    },
    {
        "name": "transfer_set_verification",
        "description": "테스트/검증 결과를 work_memory.verification 에 누적합니다. PROJECT_CONTEXT.md 의 Verification snapshot 에 자동 반영됩니다.",
        "inputSchema": {
            "type": "object",
            "required": ["text"],
            "properties": {"text": {"type": "string", "description": "검증 명령 + 결과."}},
        },
    },
    {
        "name": "transfer_set_relevant",
        "description": "이번 세션의 핵심 파일을 work_memory.relevant_files 에 등록합니다. PROJECT_CONTEXT.md 의 Relevant files 에 자동 반영됩니다.",
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "description": "프로젝트 루트 기준 상대 경로"},
                "why": {"type": "string", "description": "왜 이 파일이 핵심인가."}
            },
        },
    },
    {
        "name": "anchor_get_meta",
        "description": (
            "anchor_meta.json을 반환합니다. anchor_name을 지정하면 해당 앵커의 메타만, "
            "생략하면 전체 메타를 반환합니다. 수동 편집 UI의 prefill에 사용하세요."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "anchor_name": {
                    "type": "string",
                    "description": "조회할 앵커 이름 (생략 시 전체)",
                },
            },
        },
    },
    {
        "name": "explain_get",
        "description": "최근 변경된 파일과 변경 내용을 분석하여 반환합니다. 작업 후 무엇이 바뀌었는지 확인할 때 사용하세요.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "since_minutes": {
                    "type": "integer",
                    "description": "최근 N분 이내 변경사항 분석 (기본값: 120)",
                }
            },
        },
    },
    {
        "name": "config_get",
        "description": "VibeLign 현재 설정을 반환합니다.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "doctor_plan",
        "description": "프로젝트 분석 결과를 실행 가능한 단계 목록(Plan)으로 반환합니다. 파일 수정 없음.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "strict": {
                    "type": "boolean",
                    "description": "엄격 모드 (기본값: false)",
                }
            },
        },
    },
    {
        "name": "doctor_patch",
        "description": "Plan의 각 Action에 대한 변경 예정 미리보기를 반환합니다. 파일 수정 없음.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "strict": {
                    "type": "boolean",
                    "description": "엄격 모드 (기본값: false)",
                }
            },
        },
    },
    {
        "name": "doctor_apply",
        "description": "Plan을 실행합니다. checkpoint 자동 생성 후 add_anchor 등 안전한 action만 적용.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "strict": {
                    "type": "boolean",
                    "description": "엄격 모드 (기본값: false)",
                }
            },
        },
    },
)
# === ANCHOR: MCP_TOOL_SPECS_END ===
