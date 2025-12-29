"""Prometheus metrics."""

from prometheus_client import Counter, Histogram, generate_latest
from prometheus_client.core import CollectorRegistry

registry = CollectorRegistry()

indexed_documents_total = Counter(
    "gdrive_rag_indexed_documents_total",
    "Total number of documents indexed",
    ["source_id"],
    registry=registry,
)

indexed_chunks_total = Counter(
    "gdrive_rag_indexed_chunks_total",
    "Total number of chunks indexed",
    ["source_id"],
    registry=registry,
)

search_requests_total = Counter(
    "gdrive_rag_search_requests_total",
    "Total number of search requests",
    ["status"],
    registry=registry,
)

search_latency_seconds = Histogram(
    "gdrive_rag_search_latency_seconds",
    "Search request latency in seconds",
    buckets=[0.1, 0.25, 0.5, 0.75, 1.0, 2.0, 5.0],
    registry=registry,
)


def get_metrics() -> bytes:
    return generate_latest(registry)
