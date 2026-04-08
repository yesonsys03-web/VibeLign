# === ANCHOR: MCP_HANDLER_REGISTRY_START ===
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Protocol, cast


# === ANCHOR: MCP_HANDLER_REGISTRY_TEXTCONTENTFACTORY_START ===
class TextContentFactory(Protocol):
    # === ANCHOR: MCP_HANDLER_REGISTRY___CALL___START ===
# === ANCHOR: MCP_HANDLER_REGISTRY_TEXTCONTENTFACTORY_END ===
    def __call__(self, *, type: str, text: str) -> object: ...
    # === ANCHOR: MCP_HANDLER_REGISTRY___CALL___END ===


# === ANCHOR: MCP_HANDLER_REGISTRY_CHECKPOINTHANDLERSMODULE_START ===
class CheckpointHandlersModule(Protocol):
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_CHECKPOINT_CREATE_START ===
    def handle_checkpoint_create(
        self, root: Path, arguments: dict[str, object], text_content: TextContentFactory
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_CHECKPOINT_CREATE_END ===
    ) -> list[object]: ...

    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_CHECKPOINT_LIST_START ===
    def handle_checkpoint_list(
        self, root: Path, text_content: TextContentFactory
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_CHECKPOINT_LIST_END ===
    ) -> list[object]: ...
# === ANCHOR: MCP_HANDLER_REGISTRY_CHECKPOINTHANDLERSMODULE_END ===

    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_CHECKPOINT_RESTORE_START ===
    def handle_checkpoint_restore(
        self, root: Path, arguments: dict[str, object], text_content: TextContentFactory
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_CHECKPOINT_RESTORE_END ===
    ) -> list[object]: ...


# === ANCHOR: MCP_HANDLER_REGISTRY_TRANSFERHANDLERSMODULE_START ===
class TransferHandlersModule(Protocol):
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_HANDOFF_CREATE_START ===
    def handle_handoff_create(
        self, root: Path, arguments: dict[str, object], text_content: TextContentFactory
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_HANDOFF_CREATE_END ===
    ) -> list[object]: ...

    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_PROJECT_CONTEXT_GET_START ===
# === ANCHOR: MCP_HANDLER_REGISTRY_TRANSFERHANDLERSMODULE_END ===
    def handle_project_context_get(
        self, root: Path, arguments: dict[str, object], text_content: TextContentFactory
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_PROJECT_CONTEXT_GET_END ===
    ) -> list[object]: ...


# === ANCHOR: MCP_HANDLER_REGISTRY_HEALTHHANDLERSMODULE_START ===
class HealthHandlersModule(Protocol):
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_DOCTOR_RUN_START ===
    def handle_doctor_run(
        self, root: Path, arguments: dict[str, object], text_content: TextContentFactory
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_DOCTOR_RUN_END ===
    ) -> list[object]: ...

    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_GUARD_CHECK_START ===
# === ANCHOR: MCP_HANDLER_REGISTRY_HEALTHHANDLERSMODULE_END ===
    def handle_guard_check(
        self, root: Path, arguments: dict[str, object], text_content: TextContentFactory
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_GUARD_CHECK_END ===
    ) -> list[object]: ...


# === ANCHOR: MCP_HANDLER_REGISTRY_PROTECTHANDLERSMODULE_START ===
class ProtectHandlersModule(Protocol):
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_PROTECT_ADD_START ===
    def handle_protect_add(
        self, root: Path, arguments: dict[str, object], text_content: TextContentFactory
# === ANCHOR: MCP_HANDLER_REGISTRY_PROTECTHANDLERSMODULE_END ===
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_PROTECT_ADD_END ===
    ) -> list[object]: ...


# === ANCHOR: MCP_HANDLER_REGISTRY_PATCHHANDLERSMODULE_START ===
class PatchHandlersModule(Protocol):
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_PATCH_GET_START ===
    def handle_patch_get(
        self, root: Path, arguments: dict[str, object], text_content: TextContentFactory
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_PATCH_GET_END ===
    ) -> list[object]: ...

    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_PATCH_APPLY_START ===
# === ANCHOR: MCP_HANDLER_REGISTRY_PATCHHANDLERSMODULE_END ===
    def handle_patch_apply(
        self, root: Path, arguments: dict[str, object], text_content: TextContentFactory
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_PATCH_APPLY_END ===
    ) -> list[object]: ...


# === ANCHOR: MCP_HANDLER_REGISTRY_ANCHORHANDLERSMODULE_START ===
class AnchorHandlersModule(Protocol):
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_ANCHOR_RUN_START ===
    def handle_anchor_run(
        self, root: Path, text_content: TextContentFactory
# === ANCHOR: MCP_HANDLER_REGISTRY_ANCHORHANDLERSMODULE_END ===
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_ANCHOR_RUN_END ===
    ) -> list[object]: ...


# === ANCHOR: MCP_HANDLER_REGISTRY_MISCHANDLERSMODULE_START ===
class MiscHandlersModule(Protocol):
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_EXPLAIN_GET_START ===
    def handle_explain_get(
        self, root: Path, arguments: dict[str, object], text_content: TextContentFactory
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_EXPLAIN_GET_END ===
    ) -> list[object]: ...

    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_ANCHOR_LIST_START ===
    def handle_anchor_list(
        self, root: Path, text_content: TextContentFactory
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_ANCHOR_LIST_END ===
    ) -> list[object]: ...
# === ANCHOR: MCP_HANDLER_REGISTRY_MISCHANDLERSMODULE_END ===

    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_CONFIG_GET_START ===
    def handle_config_get(
        self, root: Path, text_content: TextContentFactory
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_CONFIG_GET_END ===
    ) -> list[object]: ...


# === ANCHOR: MCP_HANDLER_REGISTRY_DOCTORHANDLERSMODULE_START ===
class DoctorHandlersModule(Protocol):
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_DOCTOR_PLAN_START ===
    def handle_doctor_plan(
        self, root: Path, arguments: dict[str, object], text_content: TextContentFactory
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_DOCTOR_PLAN_END ===
    ) -> list[object]: ...

    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_DOCTOR_PATCH_START ===
    def handle_doctor_patch(
        self, root: Path, arguments: dict[str, object], text_content: TextContentFactory
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_DOCTOR_PATCH_END ===
    ) -> list[object]: ...
# === ANCHOR: MCP_HANDLER_REGISTRY_DOCTORHANDLERSMODULE_END ===

    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_DOCTOR_APPLY_START ===
    def handle_doctor_apply(
        self, root: Path, arguments: dict[str, object], text_content: TextContentFactory
    # === ANCHOR: MCP_HANDLER_REGISTRY_HANDLE_DOCTOR_APPLY_END ===
    ) -> list[object]: ...


# === ANCHOR: MCP_HANDLER_REGISTRY_DISPATCHHANDLER_START ===
class DispatchHandler(Protocol):
    # === ANCHOR: MCP_HANDLER_REGISTRY___CALL___START ===
    def __call__(
        self, root: Path, arguments: dict[str, object], text_content: TextContentFactory
# === ANCHOR: MCP_HANDLER_REGISTRY_DISPATCHHANDLER_END ===
    # === ANCHOR: MCP_HANDLER_REGISTRY___CALL___END ===
    ) -> list[object]: ...


# === ANCHOR: MCP_HANDLER_REGISTRY__CHECKPOINT_HANDLERS_START ===
def _checkpoint_handlers() -> CheckpointHandlersModule:
    return cast(
        CheckpointHandlersModule,
        cast(object, importlib.import_module("vibelign.mcp.mcp_checkpoint_handlers")),
    )
# === ANCHOR: MCP_HANDLER_REGISTRY__CHECKPOINT_HANDLERS_END ===


# === ANCHOR: MCP_HANDLER_REGISTRY__TRANSFER_HANDLERS_START ===
def _transfer_handlers() -> TransferHandlersModule:
    return cast(
        TransferHandlersModule,
        cast(object, importlib.import_module("vibelign.mcp.mcp_transfer_handlers")),
    )
# === ANCHOR: MCP_HANDLER_REGISTRY__TRANSFER_HANDLERS_END ===


# === ANCHOR: MCP_HANDLER_REGISTRY__HEALTH_HANDLERS_START ===
def _health_handlers() -> HealthHandlersModule:
    return cast(
        HealthHandlersModule,
        cast(object, importlib.import_module("vibelign.mcp.mcp_health_handlers")),
    )
# === ANCHOR: MCP_HANDLER_REGISTRY__HEALTH_HANDLERS_END ===


# === ANCHOR: MCP_HANDLER_REGISTRY__PROTECT_HANDLERS_START ===
def _protect_handlers() -> ProtectHandlersModule:
    return cast(
        ProtectHandlersModule,
        cast(object, importlib.import_module("vibelign.mcp.mcp_protect_handlers")),
    )
# === ANCHOR: MCP_HANDLER_REGISTRY__PROTECT_HANDLERS_END ===


# === ANCHOR: MCP_HANDLER_REGISTRY__PATCH_HANDLERS_START ===
def _patch_handlers() -> PatchHandlersModule:
    return cast(
        PatchHandlersModule,
        cast(object, importlib.import_module("vibelign.mcp.mcp_patch_handlers")),
    )
# === ANCHOR: MCP_HANDLER_REGISTRY__PATCH_HANDLERS_END ===


# === ANCHOR: MCP_HANDLER_REGISTRY__ANCHOR_HANDLERS_START ===
def _anchor_handlers() -> AnchorHandlersModule:
    return cast(
        AnchorHandlersModule,
        cast(object, importlib.import_module("vibelign.mcp.mcp_anchor_handlers")),
    )
# === ANCHOR: MCP_HANDLER_REGISTRY__ANCHOR_HANDLERS_END ===


# === ANCHOR: MCP_HANDLER_REGISTRY__MISC_HANDLERS_START ===
def _misc_handlers() -> MiscHandlersModule:
    return cast(
        MiscHandlersModule,
        cast(object, importlib.import_module("vibelign.mcp.mcp_misc_handlers")),
    )
# === ANCHOR: MCP_HANDLER_REGISTRY__MISC_HANDLERS_END ===


# === ANCHOR: MCP_HANDLER_REGISTRY__DOCTOR_HANDLERS_START ===
def _doctor_handlers() -> DoctorHandlersModule:
    return cast(
        DoctorHandlersModule,
        cast(object, importlib.import_module("vibelign.mcp.mcp_doctor_handlers")),
    )
# === ANCHOR: MCP_HANDLER_REGISTRY__DOCTOR_HANDLERS_END ===


# === ANCHOR: MCP_HANDLER_REGISTRY__HANDLE_CHECKPOINT_LIST_START ===
def _handle_checkpoint_list(
    root: Path, arguments: dict[str, object], text_content: TextContentFactory
# === ANCHOR: MCP_HANDLER_REGISTRY__HANDLE_CHECKPOINT_LIST_END ===
) -> list[object]:
    _ = arguments
    return _checkpoint_handlers().handle_checkpoint_list(root, text_content)


# === ANCHOR: MCP_HANDLER_REGISTRY__HANDLE_ANCHOR_RUN_START ===
def _handle_anchor_run(
    root: Path, arguments: dict[str, object], text_content: TextContentFactory
# === ANCHOR: MCP_HANDLER_REGISTRY__HANDLE_ANCHOR_RUN_END ===
) -> list[object]:
    _ = arguments
    return _anchor_handlers().handle_anchor_run(root, text_content)


# === ANCHOR: MCP_HANDLER_REGISTRY__HANDLE_ANCHOR_LIST_START ===
def _handle_anchor_list(
    root: Path, arguments: dict[str, object], text_content: TextContentFactory
# === ANCHOR: MCP_HANDLER_REGISTRY__HANDLE_ANCHOR_LIST_END ===
) -> list[object]:
    _ = arguments
    return _misc_handlers().handle_anchor_list(root, text_content)


# === ANCHOR: MCP_HANDLER_REGISTRY__HANDLE_CONFIG_GET_START ===
def _handle_config_get(
    root: Path, arguments: dict[str, object], text_content: TextContentFactory
# === ANCHOR: MCP_HANDLER_REGISTRY__HANDLE_CONFIG_GET_END ===
) -> list[object]:
    _ = arguments
    return _misc_handlers().handle_config_get(root, text_content)


DISPATCH_TABLE: dict[str, DispatchHandler] = {
    "checkpoint_create": _checkpoint_handlers().handle_checkpoint_create,
    "checkpoint_list": _handle_checkpoint_list,
    "checkpoint_restore": _checkpoint_handlers().handle_checkpoint_restore,
    "handoff_create": _transfer_handlers().handle_handoff_create,
    "project_context_get": _transfer_handlers().handle_project_context_get,
    "doctor_run": _health_handlers().handle_doctor_run,
    "guard_check": _health_handlers().handle_guard_check,
    "protect_add": _protect_handlers().handle_protect_add,
    "patch_get": _patch_handlers().handle_patch_get,
    "patch_apply": _patch_handlers().handle_patch_apply,
    "anchor_run": _handle_anchor_run,
    "explain_get": _misc_handlers().handle_explain_get,
    "anchor_list": _handle_anchor_list,
    "config_get": _handle_config_get,
    "doctor_plan": _doctor_handlers().handle_doctor_plan,
    "doctor_patch": _doctor_handlers().handle_doctor_patch,
    "doctor_apply": _doctor_handlers().handle_doctor_apply,
}
# === ANCHOR: MCP_HANDLER_REGISTRY_END ===
