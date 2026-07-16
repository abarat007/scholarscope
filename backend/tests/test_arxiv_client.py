import httpx
import pytest
from src.services.ingestion.arxiv_client import (
    ArxivClient,
    AsyncRateLimiter,
    parse_atom_feed,
)

SAMPLE_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2401.12345v2</id>
    <title>Retrieval-Augmented Generation:
      A   Survey</title>
    <summary>We survey RAG systems
      across many domains.</summary>
    <published>2024-01-20T10:00:00Z</published>
    <updated>2024-02-01T09:30:00Z</updated>
    <author><name>Ada Lovelace</name></author>
    <author><name>Alan Turing</name></author>
    <arxiv:primary_category term="cs.CL"/>
    <category term="cs.CL"/>
    <category term="cs.AI"/>
    <link href="http://arxiv.org/pdf/2401.12345v2" title="pdf" rel="related"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/cs/0301012v1</id>
    <title>A Legacy Identifier Paper</title>
    <summary>Old-style arXiv id.</summary>
    <published>2003-01-15T00:00:00Z</published>
    <updated>2003-01-15T00:00:00Z</updated>
    <author><name>Grace Hopper</name></author>
    <category term="cs.DS"/>
  </entry>
</feed>
"""


class FakeTime:
    def __init__(self):
        self.now = 0.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(round(seconds, 6))
        self.now += seconds


def test_parse_atom_feed_extracts_fields():
    papers = parse_atom_feed(SAMPLE_FEED)
    assert len(papers) == 2

    modern = papers[0]
    assert modern.arxiv_id == "2401.12345"
    assert modern.version == 2
    assert modern.title == "Retrieval-Augmented Generation: A Survey"
    assert modern.abstract == "We survey RAG systems across many domains."
    assert modern.authors == ["Ada Lovelace", "Alan Turing"]
    assert modern.categories == ["cs.CL", "cs.AI"]
    assert modern.primary_category == "cs.CL"
    assert modern.published_at.year == 2024
    assert modern.pdf_url == "http://arxiv.org/pdf/2401.12345v2"

    legacy = papers[1]
    assert legacy.arxiv_id == "cs/0301012"
    assert legacy.version == 1
    assert legacy.primary_category == "cs.DS"  # falls back to first category
    assert legacy.pdf_url == "https://arxiv.org/pdf/cs/0301012"


async def test_rate_limiter_spaces_consecutive_requests():
    t = FakeTime()
    limiter = AsyncRateLimiter(3.0, clock=t.clock, sleep=t.sleep)

    await limiter.acquire()  # first acquisition is free
    t.now += 1.0  # one second of "work"
    await limiter.acquire()  # must wait out the remaining 2s

    assert t.sleeps == [2.0]


async def test_rate_limiter_skips_wait_when_interval_elapsed():
    t = FakeTime()
    limiter = AsyncRateLimiter(3.0, clock=t.clock, sleep=t.sleep)

    await limiter.acquire()
    t.now += 5.0
    await limiter.acquire()

    assert t.sleeps == []


def _client_with_transport(handler, t: FakeTime) -> ArxivClient:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    limiter = AsyncRateLimiter(3.0, clock=t.clock, sleep=t.sleep)
    return ArxivClient(http, rate_limiter=limiter, sleep=t.sleep, backoff_base_s=2.0)


async def test_search_retries_server_errors_with_backoff():
    t = FakeTime()
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, text=SAMPLE_FEED)

    client = _client_with_transport(handler, t)
    papers = await client.search("cat:cs.CL")

    assert calls["count"] == 3
    assert len(papers) == 2
    # exponential backoff sleeps: 2s after first failure, 4s after second
    assert 2.0 in t.sleeps and 4.0 in t.sleeps


async def test_search_does_not_retry_client_errors():
    t = FakeTime()
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(400)

    client = _client_with_transport(handler, t)
    with pytest.raises(httpx.HTTPStatusError):
        await client.search("cat:cs.CL")

    assert calls["count"] == 1
