from vibelign.core.planning_cli.fallback import (
    INTERNAL_PROVIDER_PRIORITY,
    provider_try_order,
)


def test_preferred_first_then_priority():
    order = provider_try_order("agy")
    assert order[0] == "agy"
    assert order == ["agy"] + [p for p in INTERNAL_PROVIDER_PRIORITY if p != "agy"]


def test_no_duplicates():
    order = provider_try_order("claude")
    assert len(order) == len(set(order))


def test_unknown_preferred_still_tries_priority():
    order = provider_try_order("zzz")
    assert order[0] == "zzz"
    assert INTERNAL_PROVIDER_PRIORITY[0] in order


def test_none_preferred_uses_priority_only():
    assert provider_try_order(None) == list(INTERNAL_PROVIDER_PRIORITY)
