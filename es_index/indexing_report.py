"""Generate indexing and performance reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.constants import PROJECT_ROOT
from utils.file_utils import ensure_parent_directory


class IndexingReportGenerator:
    """Write indexing and performance reports to disk."""

    def generate(
        self,
        indexing_report_path: Path,
        performance_report_path: Path,
        metadata: dict[str, Any],
        performance: dict[str, Any],
    ) -> dict[str, Any]:
        generated_at = datetime.now(timezone.utc).isoformat()
        indexing_report = {
            "report_type": "indexing",
            "generated_at": generated_at,
            "pipeline": metadata,
        }
        performance_report = {
            "report_type": "indexing_performance",
            "generated_at": generated_at,
            "metrics": performance,
            "pipeline": metadata,
        }

        ensure_parent_directory(indexing_report_path)
        ensure_parent_directory(performance_report_path)
        with indexing_report_path.open("w", encoding="utf-8") as handle:
            json.dump(indexing_report, handle, indent=2)
        with performance_report_path.open("w", encoding="utf-8") as handle:
            json.dump(performance_report, handle, indent=2)

        return {"indexing_report": indexing_report, "performance_report": performance_report}
