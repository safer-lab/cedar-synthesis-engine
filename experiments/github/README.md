# GitHub Repository Permissions — Experiment Description

## What This Scenario Models

This experiment models a simplified version of GitHub's real permission system. Users belong to organizations that contain repositories, and repositories have issues. There are five role tiers that control what a user can do:

| Role | What they can do |
|------|-----------------|
| **Reader** | Pull code, fork repos, edit/delete their own issues |
| **Triager** | Assign issues to other users |
| **Writer** | Push code, edit any issue |
| **Maintainer** | Delete any issue |
| **Admin** | Add/remove users from any role |

There is also one deny rule: **archived repositories** block all write operations (push, adding users to roles), but still allow reads (pull, fork).

## Why This Is a Good Fit for Our Experiment

### 1. It's a real-world system people understand

GitHub's permission model is familiar to most developers. When we present this in a paper, reviewers immediately grasp the domain — no need to explain a contrived scenario. The ground-truth policies come directly from AWS's official Cedar examples repository (`cedar-policy/cedar-examples`).

### 2. It exercises diverse Cedar features without exotic constructs

| Feature | How it appears | Why it matters |
|---------|---------------|----------------|
| Entity group membership | `principal in resource.readers` | The most common Cedar pattern — the solver must reason about who is "in" which group |
| Cross-entity traversal | `principal in resource.repo.triagers` | Issue → Repository → UserGroup chain — tests the solver's ability to follow entity references |
| Entity equality | `principal == resource.reporter` | Tests whether the solver can distinguish "same entity" from "different entity" |
| Boolean attributes | `resource.isArchived` | Simple attribute-based conditions that create permit/forbid interaction |
| Action groups | `action in [Action::"add_reader", ...]` | Multiple actions governed by one rule |

Critically, it avoids problematic constructs like `containsAll`, `has` on optional fields, or `datetime` extensions that can cause solver timeouts.

### 3. It has interesting dual-path permissions

The `edit_issue` and `delete_issue` actions each have **two independent paths** to authorization:

```
edit_issue:
  Path A: user is a Writer          → can edit ANY issue
  Path B: user is a Reader AND the reporter → can edit THEIR OWN issue

delete_issue:
  Path A: user is a Maintainer      → can delete ANY issue
  Path B: user is a Reader AND the reporter → can delete THEIR OWN issue
```

This is exactly where LLMs make mistakes. A common bug is implementing only one path (e.g., only Writer can edit) and forgetting the self-edit path for reporters. The **ceiling** alone won't catch this — Writer ⊂ (Writer ∪ Reporter) — so a writer-only policy passes the upper bound. You need the **floor** to verify that the reporter path also works.

### 4. It demonstrates the forbid/permit interaction

The `isArchived` flag creates a natural deny rule:

```
forbid (principal, action == Action::"push", resource)
when { resource.isArchived };
```

This interacts with the permit rules — a user might have writer access but still be denied because the repo is archived. The ceiling for `push` encodes this: `principal in resource.writers && !resource.isArchived`. If the candidate forgets the archive check, the solver finds a counterexample with `isArchived: true`.

### 5. It scales well for comparative evaluation

With 9 verification checks (5 ceiling, 2 floor, 2 liveness) across 2 resource types (Repository, Issue) and 11 distinct actions, this scenario provides enough complexity to measure meaningful differences between:

- **Model tiers**: How many iterations does GPT-4 need vs. Claude Sonnet vs. a smaller model?
- **With/without counterexamples**: Does the solver feedback actually help, or would blind retries converge too?
- **Reference policy quality**: What happens if the floor is too loose or the ceiling is too tight?

## What's in this directory

```
experiments/github/
├── schema.cedarschema       # Entity types + actions (adapted from dataset, added isArchived)
├── policy_spec.md           # Natural language requirements (6 rules)
├── verification_plan.py     # 9 checks: 5 ceiling, 2 floor, 2 liveness
├── references/
│   ├── ceiling_pull.cedar         # Reader can pull
│   ├── ceiling_push.cedar         # Writer can push (not if archived)
│   ├── ceiling_edit_issue.cedar   # Writer OR reporter+reader can edit
│   ├── ceiling_delete_issue.cedar # Maintainer OR reporter+reader can delete
│   ├── ceiling_add_reader.cedar   # Admin can add reader (not if archived)
│   ├── floor_writer_edit.cedar    # Writers MUST edit even non-own issues
│   └── floor_reporter_delete.cedar # Reporters MUST delete own issues
├── candidate.cedar          # The synthesized policy (Agent B output)
├── policy_store.cedar       # Accumulates verified policies
└── README.md                # This file
```

## Running the experiment

```bash
CVC5=~/.local/bin/cvc5 python orchestrator.py --workspace experiments/github
```
