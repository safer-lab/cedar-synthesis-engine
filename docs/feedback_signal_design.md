# CEGIS Feedback Signal Design

## Context

In the Decidable CEGIS loop (Phase 2), the LLM synthesizes a candidate Cedar policy, the SMT solver (CVC5 via `cedar symcc`) verifies it against ceiling/floor/liveness checks, and the verification results are fed back to the LLM as a natural language message. The design of this feedback message — what we call the **feedback signal** — directly determines whether weaker models can converge.

This document describes the original (baseline) signal and the revamped signal, with experimental evidence for the improvement.

## Baseline Feedback Signal

The original `_format_feedback` produced a flat list of pass/fail results with raw solver output:

```
## Verification Results — 2 check(s) FAILED

- view_safety (implies): **FAIL**
  Counterexample:
  ```
  <raw CVC5 solver output>
  ```
- edit_safety (implies): **FAIL**
  Counterexample:
  ```
  <raw CVC5 solver output>
  ```
- auditor_loophole_view (floor): **PASS**
- auditor_loophole_edit (floor): **PASS**
- liveness_view (always-denies (liveness)): **PASS**
- liveness_edit (always-denies (liveness)): **PASS**

Fix the policy to address every failure. Output the COMPLETE updated policy.
```

### Problems

1. **Opaque counterexamples.** The raw SMT solver output encodes a satisfying assignment (entity UIDs, attribute values, boolean flags) in a format designed for formal methods tooling, not LLMs. The model must reverse-engineer what the counterexample *means* — which condition was violated and in which direction.

2. **Missing bounds.** The model knows a ceiling check failed but never sees the ceiling policy itself. It must guess what the upper bound looks like from the counterexample alone. For compositional policies with multiple interacting conditions (department match OR auditor exemption, AND role gate, AND clearance check), this is a hard inference problem.

3. **No directionality.** An `implies` failure and a `floor` failure require opposite corrections — one means "you're too permissive" and the other means "you're too restrictive." The baseline signal reports both as generic `FAIL` with no indication of which direction to adjust.

4. **No oscillation awareness.** When the model fixes a floor violation by loosening conditions, it may break a ceiling check. On the next iteration it tightens conditions, breaking the floor again. The baseline signal treats each iteration independently — the model has no signal that it's been flip-flopping between the same two failure modes.

## Revamped Feedback Signal

The revamped signal addresses all four problems:

```
## Verification Results — 2 check(s) FAILED

**WARNING — OSCILLATION DETECTED**
You fixed: auditor_loophole_view, auditor_loophole_edit
But broke: view_safety, edit_safety
ALL checks must pass simultaneously. Do not sacrifice one bound to satisfy another.

- view_safety (implies): **FAIL**
  **Your policy is MORE permissive than the ceiling.**
  It allows something the ceiling forbids. Tighten conditions.
  Ceiling policy (your policy must not exceed this):
  ```cedar
  permit (
      principal,
      action == Action::"View",
      resource
  ) when {
      resource.projectStatus == "Active" &&
      (principal.department == resource.projectManagingDepartment ||
       principal in Role::"GlobalAuditor") &&
      (
          (principal in Role::"ClinicalResearcher" &&
           principal.clearanceLevel > 3 &&
           resource.classification != "HighlyRestricted")
          ||
          (principal in Role::"PrincipalInvestigator" &&
           context.networkRiskScore < 20 &&
           context.isCompliantDevice)
      )
  };
  ```
  Counterexample from solver:
  ```
  <raw CVC5 solver output>
  ```
- edit_safety (implies): **FAIL**
  **Your policy is MORE permissive than the ceiling.**
  ...
- auditor_loophole_view (floor): **PASS**
- auditor_loophole_edit (floor): **PASS**
- liveness_view (always-denies (liveness)): **PASS**
- liveness_edit (always-denies (liveness)): **PASS**

Fix the policy to address EVERY failure without breaking passing checks.
Output the COMPLETE updated policy.
```

### Components

#### 1. Reference policy inclusion

For each failed check, the feedback includes the full Cedar source of the reference policy (ceiling or floor) that was violated. This gives the model the **exact specification** it must satisfy — the same information a human engineer would consult.

| Check type | What's shown | Label |
|---|---|---|
| `implies` (ceiling) | The ceiling `.cedar` file | "your policy must not exceed this" |
| `floor` | The floor `.cedar` file | "your policy must allow at least this" |
| `always-denies-liveness` | No reference file | "your policy denies ALL requests" |

#### 2. Directional explanation

Each failure is annotated with a directional diagnosis:

| Check type | Annotation | Action required |
|---|---|---|
| `implies` (ceiling) | "Your policy is MORE permissive than the ceiling" | Tighten conditions |
| `floor` | "Your policy is MORE restrictive than the floor" | Loosen conditions |
| `always-denies-liveness` | "Your policy denies ALL requests for this action" | Add a permit path |

This removes the ambiguity of a generic `FAIL` — the model immediately knows whether to tighten or loosen.

#### 3. Oscillation detection

The harness tracks which checks failed on the previous iteration. If the current iteration's failures differ (some fixed, some regressed), it emits:

```
WARNING — OSCILLATION DETECTED
You fixed: <checks that were failing but now pass>
But broke: <checks that were passing but now fail>
ALL checks must pass simultaneously.
```

This is computed by set difference:

```
fixed     = prev_failed - current_failed
regressed = current_failed - prev_failed
oscillation = bool(fixed and regressed)
```

The warning appears at the top of the feedback, before individual check results, to prime the model's attention on the simultaneous-satisfaction constraint.

## Experimental Results

Scenario: Clinical Trial Data Platform (6 checks: 2 ceiling, 2 floor, 2 liveness).
Phase 1: Pre-existing reference policies (Sonnet-generated, human-reviewed).

| Phase 2 Model | Feedback Signal | Converged | Iterations | Time |
|---|---|---|---|---|
| Sonnet | Baseline | Yes | 5 | 20.0s |
| Haiku | Baseline | **No** | 10/10 (limit) | 60.3s |
| Haiku | Revamped | Yes | **2** | 5.4s |

### Failure mode analysis (Haiku + baseline)

The iteration trace shows a stable oscillation between two failure modes:

```
Iter 2:  loss=2  view_safety FAIL, edit_safety FAIL       (ceiling: too permissive)
Iter 3:  loss=4  + auditor_loophole_view/edit FAIL         (floor: too restrictive)
Iter 4:  loss=4  same
Iter 5:  loss=2  view_safety FAIL, edit_safety FAIL        (back to ceiling)
Iter 6:  loss=4  + floor failures again
...repeats until iteration limit
```

The model repeatedly overcorrects: loosening to fix the floor breaks the ceiling, tightening to fix the ceiling breaks the floor. Without seeing the reference policies, the model cannot identify the narrow valid region between the two bounds.

### Success mode analysis (Haiku + revamped)

```
Iter 1:  loss=2  view_safety FAIL, edit_safety FAIL        (ceiling: too permissive)
Iter 2:  loss=0  ALL PASS                                   (converged)
```

With the ceiling policy visible in the feedback, the model could directly compare its `when` clause against the ceiling's `when` clause and produce a structurally correct fix on the first correction attempt.

## Implementation

The feedback signal is generated by `_format_feedback()` in `eval_harness.py`. It takes:

- `vr: VerificationResult` — the current verification results
- `checks: list[dict]` — the loaded verification plan (maps check names to reference file paths)
- `prev_failed: set[str] | None` — check names that failed on the previous iteration (for oscillation detection)

Reference policies are read from disk at feedback time using the `reference_path` (ceiling) or `floor_path` (floor) from the check definition.

## Implications for Model Selection

The revamped signal narrows the capability gap between strong and weak models by offloading the "understand what the bound is" inference from the model to the harness. The model only needs to:

1. Read the ceiling/floor policy (literal Cedar code)
2. Compare it against its own candidate
3. Make a targeted structural fix

This is a **code diff** task rather than a **specification inference** task — a significantly lower cognitive bar that smaller models handle reliably.
