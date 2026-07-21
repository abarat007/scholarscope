"""Daily arXiv ingestion for the configured categories.

Thin orchestration layer by design: scheduling, retries, and alerting live
here; fetching, arXiv rate limiting, and idempotent upserts live in the
backend service behind POST /ingest/arxiv. The 2-day ingestion window means
a missed run self-heals on the next tick.
"""

import json
import logging
import os
import urllib.request
from datetime import datetime, timedelta

from airflow.decorators import dag, task

log = logging.getLogger(__name__)

BACKEND_URL = os.environ.get("SCHOLARSCOPE_BACKEND_URL", "http://backend:8000")
DEFAULT_CATEGORIES = "cs.CL,cs.AI,cs.LG"
# Comma-separated arXiv category codes. To cover cross-domain topics that
# collide with CS vocabulary (e.g. "spatial omics" vs. "spatial reasoning"),
# add the relevant q-bio categories here — they use the same arXiv API/client
# as CS, so no new ingestion code is needed. Common picks:
#   q-bio.NC  Neurons and Cognition   q-bio.GN  Genomics
#   q-bio.QM  Quantitative Methods    q-bio.CB  Cell Behavior
#   q-bio.TO  Tissues and Organs
# e.g. ARXIV_INGEST_CATEGORIES=cs.CL,cs.AI,cs.LG,q-bio.NC,q-bio.QM
CATEGORIES = [
    c.strip()
    for c in os.environ.get("ARXIV_INGEST_CATEGORIES", DEFAULT_CATEGORIES).split(",")
    if c.strip()
]
DAYS_BACK = 2
MAX_RESULTS = 500


def alert_on_failure(context) -> None:
    """DAG-level alerting: always log loudly; post to a webhook when configured."""
    ti = context["task_instance"]
    message = (
        f"scholarscope ingestion failed: dag={ti.dag_id} task={ti.task_id} "
        f"try={ti.try_number} logical_date={context.get('logical_date')}"
    )
    log.error(message)
    webhook = os.environ.get("ALERT_WEBHOOK_URL")
    if not webhook:
        return
    request = urllib.request.Request(
        webhook,
        data=json.dumps({"text": message}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(request, timeout=10)
    except OSError:
        log.exception("failed to deliver failure alert to webhook")


@dag(
    dag_id="arxiv_ingest",
    schedule="@daily",
    start_date=datetime(2026, 7, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": alert_on_failure,
    },
    tags=["ingestion"],
)
def arxiv_ingest():
    @task
    def ingest(category: str) -> dict:
        body = json.dumps(
            {"category": category, "days_back": DAYS_BACK, "max_results": MAX_RESULTS}
        ).encode()
        request = urllib.request.Request(
            f"{BACKEND_URL}/ingest/arxiv",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=600) as response:
            result = json.loads(response.read())
        log.info("ingested %s: %s", category, result)
        return result

    ingest.expand(category=CATEGORIES)


arxiv_ingest()
