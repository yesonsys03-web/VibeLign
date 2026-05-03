import os

from vibelign.core.feature_flags import is_enabled


def test_recovery_apply_feature_flag_is_default_off() -> None:
    old_value = os.environ.pop("VIBELIGN_RECOVERY_APPLY", None)
    try:
        assert is_enabled("RECOVERY_APPLY") is False
    finally:
        if old_value is not None:
            os.environ["VIBELIGN_RECOVERY_APPLY"] = old_value


def test_recovery_apply_feature_flag_accepts_true_values() -> None:
    old_value = os.environ.get("VIBELIGN_RECOVERY_APPLY")
    os.environ["VIBELIGN_RECOVERY_APPLY"] = "yes"
    try:
        assert is_enabled("RECOVERY_APPLY") is True
    finally:
        if old_value is None:
            _ = os.environ.pop("VIBELIGN_RECOVERY_APPLY", None)
        else:
            os.environ["VIBELIGN_RECOVERY_APPLY"] = old_value
