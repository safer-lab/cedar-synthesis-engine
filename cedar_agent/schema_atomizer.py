"""Stage 1 — schema atomization.

See ``docs/HITL_STEP_B_PLAN.md`` §7.2 for context. The atom-proposal
logic (LLM-driven) lands in Step C. Step B implements the
schema-composition primitive ``compose_schema`` so Stage 1's output
can be fed into ``cedar validate`` and into Stage 2's grounding
pipeline.
"""

from __future__ import annotations

from cedar_agent.atoms import (
    ActionAtom,
    AttributeAtom,
    EntityAtom,
    SchemaDraft,
    TypeAliasAtom,
)


def _render_attribute(attr: AttributeAtom, indent: str = "    ") -> str:
    optional_marker = "?" if attr.optional else ""
    return f"{indent}{attr.field_name}{optional_marker}: {attr.cedar_type},"


def _render_entity(entity: EntityAtom) -> str:
    """Emit an ``entity X { ... };`` block.

    Falls back to ``entity X;`` (no body) when the atom has no
    attributes, members_of, or enum values.
    """
    lines: list[str] = []
    in_clause = ""
    if entity.members_of:
        in_clause = f" in [{', '.join(entity.members_of)}]"
    if entity.enum_values is not None:
        # Enumerated entity: `entity X enum ["a", "b", ...];`
        values = ", ".join(f'"{v}"' for v in entity.enum_values)
        return f"entity {entity.name} enum [{values}];"
    if not entity.attributes:
        return f"entity {entity.name}{in_clause};"
    lines.append(f"entity {entity.name}{in_clause} {{")
    for attr in entity.attributes.values():
        lines.append(_render_attribute(attr))
    lines.append("};")
    return "\n".join(lines)


def _render_action(action: ActionAtom) -> str:
    """Emit an ``action X appliesTo { ... };`` block."""
    parts: list[str] = []
    parts.append(f"action {action.name} appliesTo {{")
    if action.principal_types:
        parts.append(
            f"    principal: [{', '.join(action.principal_types)}],"
        )
    if action.resource_types:
        parts.append(
            f"    resource: [{', '.join(action.resource_types)}],"
        )
    if action.context_attributes:
        parts.append("    context: {")
        for attr in action.context_attributes.values():
            parts.append(_render_attribute(attr, indent="        "))
        parts.append("    },")
    parts.append("};")
    return "\n".join(parts)


def _render_type_alias(alias: TypeAliasAtom) -> str:
    return f"type {alias.name} = {alias.cedar_type};"


def compose_schema(draft: SchemaDraft) -> str:
    """Render a ``SchemaDraft`` to ``.cedarschema`` text.

    Output ordering: type aliases first, then entities, then actions —
    so forward references inside entity attributes resolve to the
    aliases declared above. Within each section, items appear in
    insertion order (not sorted) so authors can control ordering.
    """
    blocks: list[str] = []
    for alias in draft.type_aliases.values():
        blocks.append(_render_type_alias(alias))
    for entity in draft.entities.values():
        blocks.append(_render_entity(entity))
    for action in draft.actions.values():
        blocks.append(_render_action(action))
    return "\n\n".join(blocks) + "\n"
