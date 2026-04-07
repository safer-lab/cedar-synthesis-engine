from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI


THIS_FILE = Path(__file__).resolve()
BASELINE_DIR = THIS_FILE.parent
EXPERIMENTS_DIR = BASELINE_DIR.parent
CEDARFORGE_DIR = EXPERIMENTS_DIR.parent.parent
REPO_ROOT = CEDARFORGE_DIR.parent
RUNS_DIR = BASELINE_DIR / "runs"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(CEDARFORGE_DIR / "src"))

from metrics.policy_generation_evaluator import evaluate_workspace  # noqa: E402
from metrics.policy_generation_metrics import (  # noqa: E402
    RunMetricRecord,
    aggregate_by_prompt_variant,
    strategy_summary_to_dict,
)


PROMPT_VARIANTS = [
    "zero_shot_direct",
    "structured_instruction",
    "cot",
    "few_shot_grounded",
]
PROMPT_STRATEGY_DIR = BASELINE_DIR / "prompt_strategies"


@dataclass
class RunRecord:
    run_id: str
    task_id: str
    task_path: str
    prompt_variant: str
    model: str
    base_url: str
    syntax_pass: bool
    verification_pass: bool
    loss: int
    failed_checks: list[str]
    failed_check_types: list[str]
    duration_s: float
    metrics: dict
    raw_output_path: str
    candidate_path: str
    workspace_path: str
    log_path: str


def _load_json(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def _load_text(path: Path) -> str:
    with path.open() as f:
        return f.read().strip()


def _extract_cedar(text: str) -> str:
    text = text.strip()
    tagged = re.search(r"<cedar_policy>\s*(.*?)\s*</cedar_policy>", text, re.DOTALL | re.IGNORECASE)
    if tagged:
        return tagged.group(1).strip()
    block = re.search(r"```(?:cedar)?\s*(.*?)\s*```", text, re.DOTALL)
    if block:
        return block.group(1).strip()
    return text


def _copy_task_workspace(task_path: Path, dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def _load_task_registry() -> dict[str, dict]:
    data = _load_json(BASELINE_DIR / "tasks.json")
    return {task["id"]: task for task in data["tasks"]}


def _task_abs_path(task_rel_path: str) -> Path:
    return (REPO_ROOT / task_rel_path).resolve()


def _load_assets() -> dict[str, str]:
    assets_dir = BASELINE_DIR / "prompt_assets"
    return {
        "cheat_sheet": _load_text(assets_dir / "cedar_syntax_cheat_sheet.md"),
        "skeleton": _load_text(assets_dir / "policy_skeleton.cedar"),
        "positive": _load_text(assets_dir / "few_shot_positive_example.md"),
    }


def _load_prompt_template(variant: str) -> str:
    prompt_path = PROMPT_STRATEGY_DIR / f"{variant}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt strategy file not found: {prompt_path}")
    return _load_text(prompt_path)


def _build_prompt(variant: str, schema: str, policy_spec: str, assets: dict[str, str]) -> str:
    template = _load_prompt_template(variant)
    return template.format(
        CEDAR_SCHEMA=schema,
        POLICY_SPEC=policy_spec,
        CEDAR_SYNTAX_CHEAT_SHEET=assets["cheat_sheet"],
        POLICY_SKELETON=assets["skeleton"],
        FEW_SHOT_POSITIVE_EXAMPLE=assets["positive"],
    )


def _load_task_inputs(task_path: Path) -> tuple[str, str]:
    schema_path = task_path / "schema.cedarschema"
    if not schema_path.exists():
        schema_path = task_path / "policies.cedarschema"

    spec_path = task_path / "policy_spec.md"
    if not schema_path.exists():
        raise FileNotFoundError(f"No schema found in {task_path}")
    if not spec_path.exists():
        raise FileNotFoundError(f"No policy_spec.md found in {task_path}")

    return _load_text(schema_path), _load_text(spec_path)


def _call_model(base_url: str, model: str, prompt: str, temperature: float, max_tokens: int) -> str:
    client = OpenAI(base_url=base_url, api_key="EMPTY")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a careful Cedar policy generator. Output only final Cedar code."
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        extra_body={
            "chat_template_kwargs": {
                "enable_thinking": False,
            },
        },
    )
    return response.choices[0].message.content or ""


def _append_log(log_lines: list[str], line: str = "") -> None:
    log_lines.append(line)


def _print_and_log(log_lines: list[str], line: str = "") -> None:
    print(line)
    _append_log(log_lines, line)


def _shorten(text: str, max_len: int = 500) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "\n...[truncated]..."


def _link_or_copy(src: Path, dst: Path) -> None:
    if dst.exists() or dst.is_symlink():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    try:
        if src.is_dir():
            os.symlink(src, dst, target_is_directory=True)
        else:
            os.symlink(src, dst)
    except OSError:
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)


def _prepare_eval_workspace(task_path: Path, eval_workspace: Path, candidate_text: str) -> Path:
    if eval_workspace.exists():
        shutil.rmtree(eval_workspace)
    eval_workspace.mkdir(parents=True, exist_ok=True)

    for name in ("schema.cedarschema", "policies.cedarschema", "policy_spec.md", "verification_plan.py", "policy_store.cedar"):
        src = task_path / name
        if src.exists():
            dst_name = "schema.cedarschema" if name == "policies.cedarschema" else name
            _link_or_copy(src, eval_workspace / dst_name)

    refs_src = task_path / "references"
    if refs_src.exists():
        _link_or_copy(refs_src, eval_workspace / "references")

    (eval_workspace / "candidate.cedar").write_text(candidate_text)
    return eval_workspace


def run_once(
    task_id: str,
    task_path: Path,
    variant: str,
    model: str,
    base_url: str,
    temperature: float,
    max_tokens: int,
    run_root: Path,
    keep_eval_workspace: bool,
) -> RunRecord:
    schema, policy_spec = _load_task_inputs(task_path)
    assets = _load_assets()
    prompt = _build_prompt(variant, schema, policy_spec, assets)

    run_dir = run_root / f"{task_id}_{variant}"
    _copy_task_workspace(task_path, run_dir)
    log_path = run_dir / "run.log"
    log_lines: list[str] = []

    _print_and_log(log_lines, "=" * 72)
    _print_and_log(log_lines, f"RUN START")
    _print_and_log(log_lines, f"task:     {task_id}")
    _print_and_log(log_lines, f"strategy: {variant}")
    _print_and_log(log_lines, f"model:    {model}")
    _print_and_log(log_lines, f"base_url: {base_url}")
    _print_and_log(log_lines, "=" * 72)
    _print_and_log(log_lines, "")
    _print_and_log(log_lines, "--- Prompt ---")
    _print_and_log(log_lines, prompt)

    t0 = time.monotonic()
    raw_output = _call_model(base_url, model, prompt, temperature, max_tokens)
    candidate = _extract_cedar(raw_output)

    raw_output_path = run_dir / "raw_model_output.txt"
    candidate_path = run_dir / "candidate.cedar"
    prompt_path = run_dir / "prompt.txt"

    raw_output_path.write_text(raw_output)
    candidate_path.write_text(candidate)
    prompt_path.write_text(prompt)

    _print_and_log(log_lines, "")
    _print_and_log(log_lines, "--- Raw Model Output ---")
    _print_and_log(log_lines, raw_output)
    _print_and_log(log_lines, "")
    _print_and_log(log_lines, "--- Extracted Candidate ---")
    _print_and_log(log_lines, candidate)

    eval_workspace = _prepare_eval_workspace(
        task_path=task_path,
        eval_workspace=run_dir / "_eval_workspace",
        candidate_text=candidate,
    )

    bundle = evaluate_workspace(eval_workspace, prompt_variant=variant)
    duration_s = round(time.monotonic() - t0, 3)

    verification_path = run_dir / "verification_result.json"
    verification_path.write_text(json.dumps(bundle.verification, indent=2))
    (run_dir / "evaluation_bundle.json").write_text(json.dumps(bundle.__dict__, indent=2))

    _print_and_log(log_lines, "")
    _print_and_log(log_lines, "--- Evaluation ---")
    for stage in bundle.stages:
        _print_and_log(log_lines, f"[{stage['name'].upper()}]")
        _print_and_log(
            log_lines,
            f"status={stage['status']} passed={stage['passed']}",
        )
        _print_and_log(log_lines, f"message: {stage['message']}")
        details = stage.get("details", {})
        if stage["name"] == "semantic" and details.get("checks"):
            _print_and_log(log_lines, f"total_checks: {details.get('total_checks', 0)}")
            if "solver_time_s" in details:
                _print_and_log(log_lines, f"solver_time_s: {details['solver_time_s']}")
            _print_and_log(log_lines, "")
            _print_and_log(log_lines, "semantic check results:")
            for check in details["checks"]:
                status = "PASS" if check["passed"] else "FAIL"
                _print_and_log(
                    log_lines,
                    f"  - {check['name']} [{check['type']}] {status}",
                )
                _print_and_log(log_lines, f"    description: {check['description']}")
                if not check["passed"] and check.get("counterexample"):
                    _print_and_log(log_lines, "    counterexample:")
                    _print_and_log(log_lines, _shorten(check["counterexample"], 700))
            other_details = {k: v for k, v in details.items() if k != "checks"}
            if other_details.get("failed_checks"):
                _print_and_log(log_lines, f"failed_checks: {', '.join(other_details['failed_checks'])}")
        elif details:
            explanation = details.get("explanation")
            if explanation:
                _print_and_log(log_lines, "explanation:")
                _print_and_log(log_lines, f"  summary: {explanation.get('summary', '')}")
                _print_and_log(log_lines, f"  likely_cause: {explanation.get('likely_cause', '')}")
                _print_and_log(log_lines, f"  suggested_fix: {explanation.get('suggested_fix', '')}")
            if details.get("error"):
                _print_and_log(log_lines, "raw_error:")
                _print_and_log(log_lines, _shorten(details["error"], 1200))
            remaining = {
                k: v for k, v in details.items()
                if k not in {"explanation", "error"}
            }
            if remaining:
                _print_and_log(log_lines, json.dumps(remaining, indent=2))
        _print_and_log(log_lines, "")

    _print_and_log(log_lines, "--- Metrics ---")
    _print_and_log(log_lines, f"SyntaxPass:        {bundle.syntax_pass}")
    _print_and_log(log_lines, f"SchemaPass:        {bundle.schema_pass}")
    _print_and_log(log_lines, f"SemanticAccuracy:  {bundle.semantic_accuracy}")
    _print_and_log(log_lines, f"VerificationPass:  {bundle.verification_pass}")
    _print_and_log(log_lines, f"Loss:              {bundle.loss}")
    if bundle.failed_checks:
        _print_and_log(log_lines, f"FailedChecks:      {', '.join(bundle.failed_checks)}")
    _print_and_log(log_lines, f"DurationSec:       {duration_s}")
    _print_and_log(log_lines, "")
    _print_and_log(log_lines, f"log saved to: {log_path}")
    log_path.write_text("\n".join(log_lines) + "\n")

    if not keep_eval_workspace and eval_workspace.exists():
        shutil.rmtree(eval_workspace)

    return RunRecord(
        run_id=run_root.name,
        task_id=task_id,
        task_path=str(task_path),
        prompt_variant=variant,
        model=model,
        base_url=base_url,
        syntax_pass=bundle.syntax_pass,
        verification_pass=bundle.verification_pass,
        loss=bundle.loss,
        failed_checks=bundle.failed_checks,
        failed_check_types=bundle.failed_check_types,
        duration_s=duration_s,
        metrics=bundle.metrics,
        raw_output_path=str(raw_output_path),
        candidate_path=str(candidate_path),
        workspace_path=str(eval_workspace),
        log_path=str(log_path),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CedarForge single-model baseline experiments")
    parser.add_argument("--task", required=True, help="Task id from tasks.json")
    parser.add_argument("--variant", choices=PROMPT_VARIANTS, help="Single prompt variant to run")
    parser.add_argument("--all-variants", action="store_true", help="Run all prompt variants")
    parser.add_argument("--model", required=True, help="OpenAI-compatible model id")
    parser.add_argument("--base-url", required=True, help="OpenAI-compatible base URL")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=2048, help="Max completion tokens")
    parser.add_argument("--run-id", default=None, help="Optional run id")
    parser.add_argument(
        "--keep-eval-workspace",
        action="store_true",
        help="Keep the temporary internal evaluation workspace in the run directory",
    )
    args = parser.parse_args()

    if not args.variant and not args.all_variants:
        parser.error("Specify --variant or --all-variants")

    registry = _load_task_registry()
    if args.task not in registry:
        raise SystemExit(f"Unknown task id: {args.task}")

    task_entry = registry[args.task]
    task_path = _task_abs_path(task_entry["path"])
    if not task_path.exists():
        raise SystemExit(f"Task path does not exist: {task_path}")

    variants = PROMPT_VARIANTS if args.all_variants else [args.variant]
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_root = RUNS_DIR / run_id
    run_root.mkdir(parents=True, exist_ok=True)

    results = []
    for variant in variants:
        record = run_once(
            task_id=args.task,
            task_path=task_path,
            variant=variant,
            model=args.model,
            base_url=args.base_url,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            run_root=run_root,
            keep_eval_workspace=args.keep_eval_workspace,
        )
        results.append(asdict(record))
        print(
            f"[{variant}] syntax_pass={record.syntax_pass} "
            f"verification_pass={record.verification_pass} loss={record.loss} "
            f"duration={record.duration_s}s"
        )

    aggregated_metrics = aggregate_by_prompt_variant(
        [RunMetricRecord(**r["metrics"]) for r in results]
    )

    summary = {
        "run_id": run_id,
        "task_id": args.task,
        "task_path": str(task_path),
        "model": args.model,
        "base_url": args.base_url,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "results": results,
        "metrics_by_prompt_variant": [strategy_summary_to_dict(s) for s in aggregated_metrics],
    }
    (run_root / "summary.json").write_text(json.dumps(summary, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
