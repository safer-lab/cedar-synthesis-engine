# CedarForge Experiments

This directory contains the experiment scaffolding for Cedar policy generation with open-source models.

The research plan is staged:

1. build a strong single-model baseline
2. measure the capability boundary under different prompting strategies
3. use the verified baseline as the reference point for later multi-agent systems

## Why Single-Model First

Before introducing a multi-agent system, we need to understand what a single model can and cannot do.

The baseline question is:

> Given a policy description and a Cedar schema, under what prompting conditions can a single open-source model produce a Cedar policy that is syntax-correct and semantically aligned?

## Core Evaluation Targets

- `syntax correctness`
  Verified with Cedar validation against the schema.

- `schema correctness`
  Verified by checking whether the generated policy grounds correctly to the given schema.

- `semantic alignment`
  Verified with ceiling/floor/liveness checks through the existing symbolic verification pipeline.

## Current Track

- [single_model_baselines/](single_model_baselines): prompt variants, experiment matrix, and runnable baseline harness
- [system_design.md](system_design.md): staged research plan and multi-agent design principles

## Supporting Evaluation Code

The experiment code relies on reusable metrics under:

- [../metrics/](../metrics)

These metrics are shared across:

- single-model prompt studies
- future verifier-guided repair loops
- future multi-agent CedarForge systems

## Planned Next Track

After the single-model baseline is stable, the next step is a structured multi-agent system with:

- planning and grounding split into separate stages
- explicit role assignment across agents
- structured communication instead of free-form discussion
- external Cedar knowledge injection
- alignment checks between agent outputs
