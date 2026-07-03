"""Bulk indexing with batching, retries, and progress reporting."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from loguru import logger


@dataclass
class BulkIndexingStats:
    total_actions: int = 0
    indexed: int = 0
    failed: int = 0
    skipped_batches: int = 0
    batches: int = 0
    retries: int = 0
    elapsed_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


class BulkIndexer:
    """Index documents in batches with retry support."""

    def __init__(
        self,
        client: Elasticsearch,
        index_name: str,
        batch_size: int = 2000,
        max_retries: int = 3,
        retry_backoff_seconds: float = 2.0,
        progress_every_batches: int = 5,
    ) -> None:
        self.client = client
        self.index_name = index_name
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.progress_every_batches = progress_every_batches
        self.logger = logger.bind(module="es_index.bulk_indexer")

    def index_actions(self, actions: list[dict[str, Any]]) -> BulkIndexingStats:
        stats = BulkIndexingStats(total_actions=len(actions))
        if not actions:
            return stats

        started = time.perf_counter()
        for batch_number, batch_start in enumerate(range(0, len(actions), self.batch_size), start=1):
            batch = actions[batch_start : batch_start + self.batch_size]
            indexed, failed, retries, batch_errors = self._index_batch(batch)
            stats.batches += 1
            stats.indexed += indexed
            stats.failed += failed
            stats.retries += retries
            stats.errors.extend(batch_errors)

            if batch_number % self.progress_every_batches == 0 or batch_start + self.batch_size >= len(actions):
                self.logger.info(
                    "Indexed batch {} | progress={}/{} | indexed={} | failed={}",
                    batch_number,
                    min(batch_start + len(batch), len(actions)),
                    len(actions),
                    stats.indexed,
                    stats.failed,
                )

        stats.elapsed_seconds = round(time.perf_counter() - started, 3)
        return stats

    def _index_batch(self, batch: list[dict[str, Any]]) -> tuple[int, int, int, list[str]]:
        bulk_actions = [
            {
                "_index": self.index_name,
                "_id": action["_id"],
                "_source": action["_source"],
            }
            for action in batch
        ]

        retries = 0
        errors: list[str] = []
        for attempt in range(1, self.max_retries + 1):
            try:
                success_count, bulk_errors = bulk(
                    self.client,
                    bulk_actions,
                    chunk_size=len(bulk_actions),
                    raise_on_error=False,
                    raise_on_exception=False,
                )
                failed_items = len(bulk_errors or [])
                if bulk_errors:
                    for item in bulk_errors[:5]:
                        errors.append(str(item))
                    if len(bulk_errors) > 5:
                        errors.append(f"... and {len(bulk_errors) - 5} more bulk errors")

                if failed_items == 0:
                    return success_count, 0, retries, errors

                if attempt < self.max_retries:
                    retries += 1
                    sleep_for = self.retry_backoff_seconds * attempt
                    self.logger.warning(
                        "Batch failed with {} errors; retry {}/{} in {:.1f}s",
                        failed_items,
                        attempt,
                        self.max_retries,
                        sleep_for,
                    )
                    time.sleep(sleep_for)
                    continue

                return success_count, failed_items, retries, errors
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))
                if attempt < self.max_retries:
                    retries += 1
                    time.sleep(self.retry_backoff_seconds * attempt)
                    continue
                return 0, len(batch), retries, errors

        return 0, len(batch), retries, errors
