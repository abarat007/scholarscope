from datetime import date

from src.services.retrieval.search import build_bm25_query, build_filters, parse_hits


def test_bm25_query_boosts_title_over_abstract():
    body = build_bm25_query("retrieval augmented generation", k=10)
    match = body["query"]["bool"]["must"][0]["multi_match"]
    assert match["query"] == "retrieval augmented generation"
    assert match["fields"] == ["title^2", "abstract"]
    assert body["size"] == 10
    assert "embedding" not in body["_source"]


def test_filters_empty_by_default():
    assert build_filters() == []


def test_category_and_date_filters():
    filters = build_filters("cs.CL", date(2026, 1, 1), date(2026, 6, 30))
    assert {"term": {"categories": "cs.CL"}} in filters
    assert {
        "range": {"published_at": {"gte": "2026-01-01", "lte": "2026-06-30"}}
    } in filters


def test_open_ended_date_range():
    filters = build_filters(None, date(2026, 1, 1), None)
    assert filters == [{"range": {"published_at": {"gte": "2026-01-01"}}}]


def test_parse_hits_maps_source_and_score():
    body = {
        "hits": {
            "hits": [
                {
                    "_score": 7.1,
                    "_source": {
                        "arxiv_id": "2401.00001",
                        "title": "A Paper",
                        "abstract": "About things.",
                        "primary_category": "cs.CL",
                        "published_at": "2026-01-05T00:00:00+00:00",
                    },
                }
            ]
        }
    }
    hits = parse_hits(body)
    assert len(hits) == 1
    assert hits[0].arxiv_id == "2401.00001"
    assert hits[0].score == 7.1
