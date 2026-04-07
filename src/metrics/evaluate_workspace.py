from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


THIS_FILE = Path(__file__).resolve()
SRC_DIR = THIS_FILE.parent.parent
sys.path.insert(0, str(SRC_DIR))

from metrics.policy_generation_evaluator import evaluate_workspace


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate a Cedar policy workspace for syntax, schema grounding, and semantic alignment"
    )
    parser.add_argument("workspace", type=Path, help="Workspace path containing candidate.cedar and verification artifacts")
    parser.add_argument(
        "--prompt-variant",
        default="unknown",
        help="Optional label used in the metrics record",
    )
    args = parser.parse_args()

    bundle = evaluate_workspace(args.workspace, prompt_variant=args.prompt_variant)
    print(json.dumps(bundle.__dict__, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
