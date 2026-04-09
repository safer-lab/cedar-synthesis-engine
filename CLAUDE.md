# CLAUDE.md — Cedar Synthesis Engine

Project orientation for future Claude Code sessions. This file auto-loads.
Keep it under ~300 lines; move deep detail to `docs/`.

## What this project is

A two-phase CEGIS harness that synthesizes Cedar access-control policies
from natural-language specifications. Phase 1 (planner) produces a
verification plan + reference policies (ceilings/floors/liveness); Phase 2
(synthesizer, small model = Haiku 4.5) iteratively proposes candidates
checked by `cedar symcc` + `cedar validate`. The central thesis: a
structured signal layer uplifts a small cheap model into producing correct
Cedar at production cost.

Two artifacts are being built:
1. **CedarBench** — a large benchmark of Cedar policy scenarios
   (`cedarbench/scenarios/`). First large-scale Cedar evaluation dataset.
2. **The harness** — `eval_harness.py` + `orchestrator.py` + `solver_wrapper.py`,
   documented as nine novel contributions in `docs/harness_fix_log.md`.

We are targeting **two papers**:
- **Workshop paper** — CedarBench as a dataset (target ≥120 scenarios).
  Venue: LangSec or PLAS.
- **Main-track paper** — the harness + its signal-layer contributions.

## Key files and directories

```
eval_harness.py          # main CLI entry (run_scenario, main, CEGIS loop)
orchestrator.py          # per-check verification orchestration
solver_wrapper.py        # cedar validate / cedar symcc invocation
                         # CEDAR_PATH pins /private/tmp/cedar/target/release/cedar
docs/harness_fix_log.md  # READ FIRST — §3–§8 document all harness rules
                         # §8.1–§8.9 = the nine novel contributions
docs/cegis_algorithm.md  # high-level CEGIS algorithm description
cedarbench/scenarios/    # 79 mutation scenarios (e.g. github_*, clinical_*)
cedarbench/scenarios/realworld/  # hand-designed production patterns
cedarbench/scenarios/realworld/README.md  # dataset index / taxonomy / citation
cedarbench/README.md     # top-level dataset README
```

## Scenario file layout

Every scenario (mutation OR realworld) is a directory with exactly:
```
policy_spec.md         # NL spec with YAML frontmatter (realworld only, so far)
schema.cedarschema     # Cedar schema defining entities/actions/context
verification_plan.py   # get_checks() returning list of dicts
references/*.cedar     # one per check: ceiling/floor reference bounds
```

Realworld `policy_spec.md` frontmatter:
```yaml
---
pattern: <short pattern name>
difficulty: easy | medium | hard | hard (planning)
features:
  - <feature 1>
  - <feature 2>
domain: <vertical>
---
```

Check types in `verification_plan.py`:
- `implies` — ceiling: candidate ⇒ reference. Candidate must be NO MORE permissive.
- `floor` — candidate ⇐ reference. Candidate must be AT LEAST as permissive.
- `always-denies-liveness` — at least one request must be permitted.

## Running a scenario

The harness needs `ANTHROPIC_API_KEY`. Copy `.env.example` to `.env`,
fill it in (the file is gitignored). Then source it in-shell and run
via `uv`:

```bash
set -a && . ./.env && set +a
uv run python eval_harness.py \
  --scenario cedarbench/scenarios/realworld/<name> \
  --no-review \
  --phase1-model claude-opus-4-6 \
  --phase2-model claude-haiku-4-5-20251001 \
  --max-iters 20
```

(Note: `uv run --env-file .env` does NOT forward the key through to
the subprocess — use shell-sourcing instead.)

Output lands in `eval_runs/<timestamp>/`. Exit code is informational.

**Worktree note:** git worktrees don't share `.env`. Symlink it in
from the main repo root once per worktree:
`ln -s /path/to/main-repo/.env .env`. The symlink is gitignored.

## Authoring workflow (Phase 1 manually, Phase 2 = Haiku)

Since streaming, **Phase 1 is done by hand** (Claude acting as security
engineer), not by an API call. The scenario's references + verification_plan
constitute the "plan." Phase 2 is Haiku under test — if Haiku stalls,
the bug is in the harness signal layer, not the model.

Per-scenario checklist:
1. Write `policy_spec.md` with YAML frontmatter and unambiguous requirements.
2. Write `schema.cedarschema`. Validate it: `cedar validate --schema X --policies /dev/null`.
3. Write `verification_plan.py` enumerating ceilings + floors + liveness.
4. Write one `references/<check_name>.cedar` per non-liveness check.
5. Validate every reference: `cedar validate --schema X --policies references/Y.cedar`.
6. Run the harness. Expect convergence in 1–3 iters if rules below are followed.
7. If Haiku stalls: investigate whether it's a missing harness signal (new
   §8.x contribution) or a genuine spec problem. Never lower the bar.

## Phase 1 planning rules (condensed from harness_fix_log.md)

These are the rules you, as the planner, must follow when writing references.
Breaking them reproduces known failure modes from §8.x.

**§8.6 Role-intersection trap.** Cedar entities can be in MULTIPLE roles.
"Role X is blocked from R" should NOT be encoded as `forbid when principal in
Role::"X"` because a user in both X and Y hits the forbid even if Y's floor
permits them. Correct encoding: exclude R from the permit for X.

**§8.8 Floor-bound consistency.** Every floor must be jointly satisfiable with
every global forbid / sibling ceiling. When writing a floor, walk every global
forbid in the spec and add `!global_forbid_condition` exclusions to the floor's
`when` clause. Example: a `floor_owner_read` should say
`principal == resource.owner && !(principal in resource.owner.blocked) && ...`,
not just `principal == resource.owner`.

**§8.9 Cedar datetime/duration syntax.** `datetime("...")` uses ISO 8601
(`"2025-03-02T20:00:00Z"`); `duration("...")` uses **Go-style**
(`"21h"`, `"-24h"`, `"1h30m"`, `"1d"`) and REJECTS ISO 8601 (`"PT21H"`, `"P1D"`).

**Negated-`has` trap (§5.4/§8.3).** Cedar's type-checker does NOT propagate
negation through `has`. Writing `!(context has targetUser) || context.targetUser.role == "X"`
is rejected. Correct guard:
`(!(context has targetUser) || (context has targetUser && context.targetUser.role == "X"))`.

**Optional attributes.** Declared with `?` in schema. MUST be `has`-guarded
before any read. `context has activeGrant && context.activeGrant.grantee == principal`.

**Property-based plans (§5.2).** References encode orthogonal properties
(e.g. "target must be same org," "approver role must be ≥ manager"), not
per-role splits. Bounds compose via conjunction.

**Symbolic-analysis limits.** `cedar symcc` ignores Cedar `template`-linked
policies — they appear as empty to the analyzer. Do NOT write scenarios
that rely on templates for verification; use the delegation pattern
(optional context attribute pre-validated by the host app) as the workaround.

## Commit hygiene

- Commits for scenarios go as batches of 3–6 related additions.
- **Commit before moving to the next batch** — the previous session lost
  ~1 scenario's work to a crash mid-batch. Don't hold work uncommitted for
  long stretches.
- Commit message style: `Add N <pattern> realworld scenarios (...)` or
  `Update harness_fix_log: §X.Y <contribution>`.

## Dataset state (update on every commit)

**Total scenarios: 110** (79 mutation + 31 realworld)
**Total PASS: 85/85** (github 14, clinical 11, doccloud 10, streaming 10,
tax 8, realworld 31 — plus hundred_check_scale 157 checks)

Realworld scenarios (31, all PASS):
1. emergency_break_glass — PASS
2. approval_chain_workflow — PASS
3. multi_tenant_saas — PASS
4. contextual_mfa_elevation — PASS
5. legal_hold_override_expiry — PASS
6. delegation_temporary_grant — PASS
7. pii_data_classification — PASS
8. payroll_separation_of_duties — PASS
9. api_key_scoped_access — PASS
10. string_prefix_domain_match — PASS
11. intentional_planner_contradiction — PASS
12. hundred_check_scale — PASS (157 checks)
13. nested_namespaces — PASS 2 iters
14. deep_entity_hierarchy — PASS 1 iter (one-shot)
15. policy_annotations — PASS 1 iter (one-shot)
16. set_contains_any — PASS 2 iters
17. gdpr_data_retention — PASS 2 iters
18. audit_log_immutability — PASS 1 iter
19. content_moderation_escalation — PASS 10 iters (hardest)
20. resource_budget_enforcement — PASS 1 iter
21. backup_restore_asymmetric — PASS 2 iters
22. iot_device_auth — PASS 2 iters
23. conference_room_booking — PASS 2 iters
24. group_chat_moderator — PASS 2 iters
25. incident_response_war_room — PASS 2 iters
26. educational_gradebook — PASS 2 iters
27. medical_prescription_workflow — PASS 2 iters
28. loan_approval_workflow — PASS 2 iters
29. matter_based_legal_access — PASS 1 iter
30. shared_inbox_delegation — PASS 1 iter
31. data_lineage_ancestry — PASS 3 iters

## Known symcc limitations

- **Entity-graph `in` membership:** `cedar symcc` cannot prove liveness
  for `principal in resource` (entity-graph membership). Use attribute-based
  `resource.members.contains(principal)` instead. Discovered in
  `group_chat_moderator`.
- **Cedar templates:** `cedar symcc` ignores template-linked policies.
  Use optional context attributes as the workaround for delegation patterns.

## Remaining opportunities

**Metadata backfill** — add YAML frontmatter to the 79 mutation scenarios
(pattern / difficulty / features / domain), for dataset filterability.

**Additional Tier C adversarial:** mega_scale_500, ambiguous_spec_guidance,
redundant_rules, missing_liveness_trap — defer unless harness paper needs
ablation data.

## User collaboration notes

- The user is publishing this as a dataset contribution to the community.
- **Breadth over depth** — coverage of real-world patterns > deep harness
  testing, within reason.
- The user's session tends to hit "prompt is too long" errors on very long
  runs. Be disciplined about committing.
- Do not batch commits beyond a handful of scenarios. Preserve progress.
