"""End-to-end Elasticsearch indexing pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd
from loguru import logger

from es_index.bulk_indexer import BulkIndexer, BulkIndexingStats
from es_index.client import build_elasticsearch_client, ping_cluster
from es_index.document_mapper import DocumentMapper
from es_index.index_manager import IndexManager
from es_index.indexing_logger import setup_indexing_logging
from es_index.indexing_report import IndexingReportGenerator
from utils.constants import DEFAULT_ELASTICSEARCH_CONFIG, PROJECT_ROOT
from utils.file_utils import load_yaml_config, resolve_project_path


@dataclass
class IndexingPipelineStats:
    rows_read: int = 0
    documents_mapped: int = 0
    documents_skipped: int = 0
    indexed: int = 0
    failed: int = 0
    batches: int = 0
    retries: int = 0
    chunks_processed: int = 0
    elapsed_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


class IndexingPipeline:
    """Create index and bulk-load cleaned_dataset.csv into Elasticsearch."""

    def __init__(self, config_path: Path | None = None) -> None:
        from app_logging.logger import setup_logging

        setup_logging()
        setup_indexing_logging()
        self.config_path = config_path or DEFAULT_ELASTICSEARCH_CONFIG
        self.config = load_yaml_config(self.config_path)
        self.client = build_elasticsearch_client(self.config)
        self.index_manager = IndexManager(self.client, self.config)
        self.report_generator = IndexingReportGenerator()
        self.logger = logger.bind(module="es_index.indexing_pipeline")

    def run(self, recreate_index: bool = False) -> dict[str, Any]:
        if not ping_cluster(self.client):
            raise ConnectionError("Elasticsearch cluster is not reachable. Start Docker ES on port 9200.")

        started_at = datetime.now(timezone.utc)
        pipeline_start = perf_counter()
        stats = IndexingPipelineStats()

        indexing_config = self.config.get("indexing", {})
        input_path = resolve_project_path(
            indexing_config.get("input_dataset", "datasets/processed/final_clean_dataset.csv")
        )
        indexing_report_path = resolve_project_path(self.config["paths"]["indexing_report"])
        performance_report_path = resolve_project_path(self.config["paths"]["performance_report"])

        index_result = self.index_manager.create_index(recreate=recreate_index)
        self.logger.info("Index setup complete | index={} | created={}", index_result["index"], index_result["created"])

        mapper = DocumentMapper(
            id_field=indexing_config.get("id_field", "address_hash"),
            fallback_id_prefix=indexing_config.get("fallback_id_prefix", "row"),
        )
        bulk_indexer = BulkIndexer(
            client=self.client,
            index_name=self.index_manager.index_name,
            batch_size=int(indexing_config.get("batch_size", 2000)),
            max_retries=int(indexing_config.get("max_retries", 3)),
            retry_backoff_seconds=float(indexing_config.get("retry_backoff_seconds", 2)),
            progress_every_batches=int(indexing_config.get("progress_every_batches", 5)),
        )

        read_chunk_size = int(indexing_config.get("read_chunk_size", 20000))
        row_offset = 0
        aggregate_bulk_stats = BulkIndexingStats()

        self.logger.info("Starting bulk indexing from {}", input_path)
        for chunk in pd.read_csv(input_path, dtype=str, keep_default_na=False, chunksize=read_chunk_size):
            stats.chunks_processed += 1
            stats.rows_read += len(chunk.index)

            actions = mapper.map_dataframe(chunk, start_row=row_offset)
            stats.documents_mapped += len(actions)
            stats.documents_skipped += len(chunk.index) - len(actions)
            row_offset += len(chunk.index)

            batch_stats = bulk_indexer.index_actions(actions)
            aggregate_bulk_stats.indexed += batch_stats.indexed
            aggregate_bulk_stats.failed += batch_stats.failed
            aggregate_bulk_stats.batches += batch_stats.batches
            aggregate_bulk_stats.retries += batch_stats.retries
            aggregate_bulk_stats.errors.extend(batch_stats.errors)

            self.logger.info(
                "Chunk {} complete | rows_read={} | mapped={} | indexed_total={}",
                stats.chunks_processed,
                stats.rows_read,
                stats.documents_mapped,
                aggregate_bulk_stats.indexed,
            )

        self.index_manager.refresh_index()
        index_stats = self.index_manager.get_index_stats()
        stats.indexed = aggregate_bulk_stats.indexed
        stats.failed = aggregate_bulk_stats.failed
        stats.batches = aggregate_bulk_stats.batches
        stats.retries = aggregate_bulk_stats.retries
        stats.errors = aggregate_bulk_stats.errors[:50]
        stats.elapsed_seconds = round(perf_counter() - pipeline_start, 3)

        completed_at = datetime.now(timezone.utc)
        docs_per_second = round(stats.indexed / stats.elapsed_seconds, 2) if stats.elapsed_seconds else 0.0
        performance = {
            "elapsed_seconds": stats.elapsed_seconds,
            "documents_per_second": docs_per_second,
            "rows_read": stats.rows_read,
            "documents_mapped": stats.documents_mapped,
            "documents_skipped": stats.documents_skipped,
            "indexed": stats.indexed,
            "failed": stats.failed,
            "batches": stats.batches,
            "retries": stats.retries,
            "chunks_processed": stats.chunks_processed,
            "index_document_count": index_stats.get("document_count", 0),
            "store_size_bytes": index_stats.get("store_size_bytes", 0),
        }

        metadata = {
            "pipeline": "elasticsearch_indexing",
            "version": "1.0",
            "config_path": self._relative_path(self.config_path),
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "index": self.index_manager.index_name,
            "input_dataset": self._relative_path(input_path),
            "index_created": index_result["created"],
            "statistics": asdict(stats),
            "index_stats": index_stats,
            "indexing_report": self._relative_path(indexing_report_path),
            "performance_report": self._relative_path(performance_report_path),
        }

        self.report_generator.generate(indexing_report_path, performance_report_path, metadata, performance)
        self.logger.info(
            "Indexing completed | indexed={} | failed={} | {:.1f}s | {:.0f} docs/s",
            stats.indexed,
            stats.failed,
            stats.elapsed_seconds,
            docs_per_second,
        )
        return metadata

    @staticmethod
    def _relative_path(path: Path) -> str:
        try:
            return str(path.relative_to(PROJECT_ROOT))
        except ValueError:
            return str(path)
