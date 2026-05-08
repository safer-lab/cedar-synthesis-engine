"""HITL production agent for Cedar policy authoring.

See ``docs/HITL_STEP_B_PLAN.md`` for the implementation contract.
The package is organized as:

- ``atoms``: dataclasses for schema and property atoms (Stage 1 / Stage 2).
- ``property_elicitor``: Stage 2 (sugar compile-down).
- ``grounding``: symbolic verification + adversarial-example pipeline.
- ``schema_atomizer``: Stage 1 (LLM-driven; integrated in Step C).
- ``critic``: Stage 3 quality scorer with strict prompt boundary.
- ``corpus``: session log writer.
- ``pipeline``: orchestrates Stages 1, 1.5, 2, 1.75, 3, 2.5.
- ``ui``: terminal review UI and persistence.

The package never modifies ``eval_harness.py``, ``orchestrator.py``, or
``solver_wrapper.py`` — the v1 harness contract is frozen.
"""

__version__ = "0.1.0-step-b"
