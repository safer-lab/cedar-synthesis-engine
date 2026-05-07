# Synthesis-Difficulty Distribution

Honest grading of all 221 CedarBench scenarios on a 1–5 synthesis-difficulty
scale, per the rubric in `docs/HITL_PRODUCTION_AGENT_PLAN.md` §2.2.

**Rubric:**

| Grade | Label                  | What it means |
|-------|------------------------|---------------|
| 1     | Trivial transcription  | Numbered list, each bullet → one Cedar rule, no ambiguity, <10 lines. |
| 2     | Easy transcription     | Larger transcription, ≤1 optional attribute or set-membership check. One-pass. |
| 3     | Moderate composition   | Multiple interacting rules; some risk of getting bound wrong. |
| 4     | Genuinely hard         | Cedar verifier quirk territory (§8.x). Without the harness mechanism, model would stall. |
| 5     | Verifier-quirk hard    | Specifically required §8.x intervention. Surfaced new mechanism when first run. |

## Distribution

| Grade | Count | % of total |
|-------|------:|-----------:|
| 1     |   9   |   4.1%     |
| 2     |  56   |  25.3%     |
| 3     | 115   |  52.0%     |
| 4     |  38   |  17.2%     |
| 5     |   3   |   1.4%     |
| **Total** | **221** |  |

## Distribution by source

| Grade | Mutation (79) | Realworld (142) |
|-------|--------------:|----------------:|
| 1     |   7 |   2 |
| 2     |  31 |  25 |
| 3     |  39 |  76 |
| 4     |   1 |  37 |
| 5     |   1 |   2 |

## Reading the distribution

The Phase 0 framing in `docs/HITL_PRODUCTION_AGENT_PLAN.md` predicts ~60% Grade 1–2,
~30% Grade 3, ~8% Grade 4, ~2–3% Grade 5. The actual distribution above is
interpreted as: most CedarBench scenarios are transcription tasks where the spec
names the schema attributes inline and the synthesizer's job is mostly to compose
Cedar syntax correctly. The Grade 4–5 scenarios are where the v1 harness's signal
layer (§8.1–§8.11 of `docs/harness_fix_log.md`) actually does load-bearing work.

The two confirmed Grade 5 scenarios in the original 121 set:

- **`tags_sensitivity_and_owner`** — surfaced §8.11 (ternary-operator detector).
  Owner bypass + per-role sensitivity forbids + approval gate compose into a
  shape that LLMs reach for as `cond ? a : b`, which Cedar rejects.
- **`group_chat_moderator`** — surfaced §8.10 (entity-graph membership liveness).
  `principal in resource` is opaque to `cedar symcc`; the fix is
  `resource.members.contains(principal)` over a `Set<Entity>` attribute.

The Grade 5 entry from the v2-extension batches (`regression_battery_all_traps`)
is engineered: a single scenario constructed so that every documented harness
contribution must fire for synthesis to converge. It is not yet harness-tested.
