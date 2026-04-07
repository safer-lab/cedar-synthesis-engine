# Metrics

This folder contains reusable evaluation code for Cedar policy generation.

The evaluation is a 3-step pipeline:

1. `Syntax`
   Use Cedar validation to check whether the generated policy is valid Cedar DSL.

2. `Schema`
   Use Cedar validation diagnostics to determine whether the generated policy grounds correctly to the provided schema.

3. `Semantic`
   Use `verification_plan.py`, `references/*.cedar`, `cedar symcc`, and `cvc5` to test whether the candidate is semantically aligned.

## Main Entry Points

- [policy_generation_metrics.py](policy_generation_metrics.py)
  Metric definitions and prompt-strategy aggregation.

- [policy_generation_evaluator.py](policy_generation_evaluator.py)
  Reusable workspace evaluator for syntax, schema, and semantic alignment.

- [evaluate_workspace.py](evaluate_workspace.py)
  CLI wrapper for evaluating a prepared workspace.

- [summarize_prompt_strategies.py](summarize_prompt_strategies.py)
  Summarize prompt-variant performance from a run summary.

## Main Reported Metrics

- `SyntaxPassRate`
- `SchemaPassRate`
- `SemanticAccuracy`

These are intended to be shared across:

- single-model baselines
- verifier-guided repair loops
- future multi-agent CedarForge systems

