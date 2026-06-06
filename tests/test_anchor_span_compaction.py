from vibelign.core.anchor_tools import compact_anchor_spans, rehydrate_anchor_spans


def test_compact_drops_objects_to_strings() -> None:
    spans = [
        {"name": "FOO", "start": 1, "end": 10},
        {"name": "BAR_2", "start": 12, "end": 30, "signature": "def bar():"},
    ]
    assert compact_anchor_spans(spans) == ["FOO:1-10", "BAR_2:12-30"]


def test_rehydrate_restores_name_start_end() -> None:
    assert rehydrate_anchor_spans(["FOO:1-10", "BAR_2:12-30"]) == [
        {"name": "FOO", "start": 1, "end": 10},
        {"name": "BAR_2", "start": 12, "end": 30},
    ]


def test_round_trip_preserves_name_start_end() -> None:
    spans = [
        {"name": "A", "start": 1, "end": 5},
        {"name": "B_3", "start": 7, "end": 99},
    ]
    restored = rehydrate_anchor_spans(compact_anchor_spans(spans))
    assert restored == [
        {"name": "A", "start": 1, "end": 5},
        {"name": "B_3", "start": 7, "end": 99},
    ]


def test_rehydrate_passes_through_legacy_objects() -> None:
    legacy = [{"name": "OLD", "start": 1, "end": 2, "signature": "x"}]
    assert rehydrate_anchor_spans(legacy) == legacy


def test_compact_passes_through_already_compact_strings() -> None:
    assert compact_anchor_spans(["FOO:1-10"]) == ["FOO:1-10"]


def test_rehydrate_skips_malformed_entries() -> None:
    assert rehydrate_anchor_spans(["FOO:1-10", "garbage", "BAD:notnum"]) == [
        {"name": "FOO", "start": 1, "end": 10}
    ]
