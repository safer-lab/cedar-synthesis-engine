from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
SRC_DIR = THIS_FILE.parent.parent
sys.path.insert(0, str(SRC_DIR))

from metrics.policy_generation_metrics import RunMetricRecord, aggregate_by_prompt_variant


def _load_summary(summary_path: Path) -> list[RunMetricRecord]:
    data = json.loads(summary_path.read_text())
    results = data.get("results", [])
    metrics = []
    for result in results:
        metrics_blob = result.get("metrics")
        if metrics_blob:
            metrics.append(RunMetricRecord(**metrics_blob))
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize CedarForge prompt-strategy metrics")
    parser.add_argument("summary_json", type=Path, help="Path to a run summary.json")
    args = parser.parse_args()

    records = _load_summary(args.summary_json)
    summaries = aggregate_by_prompt_variant(records)

    print(
        f"{'Prompt Variant':<24} {'SyntaxPass':<12} {'SchemaPass':<12} "
        f"{'SemanticAcc':<12}"
    )
    print("-" * 64)
    for summary in summaries:
        print(
            f"{summary.prompt_variant:<24} {summary.syntax_pass_rate:<12.4f} "
            f"{summary.schema_pass_rate:<12.4f} {summary.semantic_accuracy:<12.4f}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
