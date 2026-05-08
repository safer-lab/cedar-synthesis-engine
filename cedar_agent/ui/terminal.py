"""Terminal review UI for atom approval.

See ``docs/HITL_STEP_B_PLAN.md`` §6 for the UI contract.

Step B implements the rendering helpers and the auto-approve stub
that the pipeline test uses. The interactive prompt loop (parsing
keys A/R/E/Q/S/V from stdin) is wired up in Step C.

Per §1.4, the verified-badge text is honest about what symcc proved
vs. what the user must judge:

    ✓ Formally consistent — does this match your intent?

This module renders that line; the pipeline writes both
``symbolic_verified`` and ``intent_acknowledged_by_user`` to the
corpus log so post-deployment analysis can study where users approved
despite imperfect grounding.
"""

from __future__ import annotations

from typing import Any

from cedar_agent.atoms import PropertyAtom
from cedar_agent.corpus import AtomDecision


VERIFIED_BADGE = "✓ Formally consistent — does this match your intent?"
UNVERIFIED_BADGE = "✗ Symbolic checks failed — review carefully before approving"


def render_property_atom(atom: PropertyAtom, index: int, total: int) -> str:
    """Render a property atom for terminal review (§6.1)."""
    lines: list[str] = []
    lines.append(f"[Property {index} of {total}]  {atom.constraint_type.upper()} — {atom.plain_english_summary}")
    lines.append("")
    lines.append(f"  Source excerpt: {atom.source_excerpt!r}")
    lines.append("")
    if atom.examples_adversarial:
        lines.append("  Adversarial examples (probing the boundary with plausible alternatives):")
        for ex in atom.examples_adversarial:
            lines.append(f"    {ex.description}")
            lines.append(
                f"      chosen encoding: {ex.decision_under_chosen}",
            )
            for label, dec in ex.decisions_under_alternatives.items():
                lines.append(f"      alternative '{label}': {dec}")
        lines.append("")
    badge = VERIFIED_BADGE if atom.symbolic_verified else UNVERIFIED_BADGE
    lines.append(f"  {badge}")
    if atom.symbolic_verification_log:
        log_summary = "; ".join(atom.symbolic_verification_log[:3])
        lines.append(f"    [{log_summary}]")
    lines.append("")
    lines.append("  [A]pprove  [R]eject  [E]dit  [Q]uestion  [S]ee Cedar")
    return "\n".join(lines)


def auto_approve(atom: Any) -> AtomDecision:
    """Default reviewer for non-interactive runs.

    Sets ``intent_acknowledged_by_user=True`` automatically. Use only
    for testing and batch evaluation; the production review loop
    in Step C prompts a real user.
    """
    return AtomDecision(
        atom_name=getattr(atom, "name", "?"),
        action="approve",
        intent_acknowledged_by_user=True,
        symbolic_verified=getattr(atom, "symbolic_verified", False),
    )
