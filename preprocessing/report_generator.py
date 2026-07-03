"""Generate preprocessing reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.constants import PROJECT_ROOT
from utils.file_utils import ensure_parent_directory


class ReportGenerator:
    """Write structured preprocessing reports to disk."""

    def generate(
        self,
        report_path: Path,
        pipeline_metadata: dict[str, Any],
        dataset_statistics: dict[str, Any],
    ) -> dict[str, Any]:
        report = {
            "report_type": "preprocessing",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pipeline": pipeline_metadata,
            "dataset_statistics": dataset_statistics,
        }
        ensure_parent_directory(report_path)
        with report_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
        return report

    @staticmethod
    def relative_path(path: Path) -> str:
        try:
            return str(path.relative_to(PROJECT_ROOT))
        except ValueError:
            return str(path)
