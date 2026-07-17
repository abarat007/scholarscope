import pytest
from src.services.retrieval.fusion import reciprocal_rank_fusion


def test_doc_in_both_rankings_beats_single_ranking_docs():
    bm25 = ["a", "b", "c"]
    dense = ["d", "b", "e"]

    fused = reciprocal_rank_fusion([bm25, dense])
    order = [doc_id for doc_id, _ in fused]

    # "b" is rank 2 in both lists; every other doc appears once.
    assert order[0] == "b"


def test_scores_match_hand_computed_values():
    fused = dict(reciprocal_rank_fusion([["a", "b"], ["b", "a"]], k=60))

    assert fused["a"] == pytest.approx(1 / 61 + 1 / 62)
    assert fused["b"] == pytest.approx(1 / 62 + 1 / 61)


def test_ties_break_deterministically_by_id():
    # "a" and "b" get identical scores; order must still be stable.
    fused = reciprocal_rank_fusion([["a", "b"], ["b", "a"]])
    assert [doc_id for doc_id, _ in fused] == ["a", "b"]


def test_lower_k_amplifies_top_ranks():
    # doc "x" is 1st in one ranking only; doc "y" is 4th in both rankings.
    rankings = [["x", "m", "n", "y"], ["p", "m", "n", "y"]]

    aggressive = dict(reciprocal_rank_fusion(rankings, k=1))
    damped = dict(reciprocal_rank_fusion(rankings, k=1000))

    # with tiny k, a single first place (1/2) beats two fourth places (2/5)
    assert aggressive["x"] > aggressive["y"]
    # with huge k, appearing in both rankings wins
    assert damped["y"] > damped["x"]


def test_empty_and_single_rankings():
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[]]) == []

    fused = reciprocal_rank_fusion([["a", "b"]])
    assert [doc_id for doc_id, _ in fused] == ["a", "b"]


def test_duplicate_ids_within_one_ranking_count_once():
    fused = dict(reciprocal_rank_fusion([["a", "a", "b"]], k=60))
    assert fused["a"] == pytest.approx(1 / 61)
    assert fused["b"] == pytest.approx(1 / 63)


def test_invalid_k_raises():
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([["a"]], k=0)
