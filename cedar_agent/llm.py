"""Thin Anthropic SDK wrapper for cedar_agent.

See ``docs/HITL_STEP_C_PLAN.md`` for the implementation contract.
Per §2 of that plan:

- Default model is ``claude-opus-4-7`` (the ``claude-api`` skill's
  non-negotiable default). Configurable per-deployment.
- Adaptive thinking is on; ``effort`` defaults to ``"high"``.
- The system prompt + the spec text are sent as cache-controlled
  blocks so repeated calls in one session amortize the input-token
  cost. Per-turn user content stays uncached.
- The constructor accepts an optional ``client`` (an
  ``anthropic.Anthropic`` instance or any object with the same
  ``messages.parse`` shape) so tests inject a mock without touching
  the network. The minimum cacheable prefix on Opus 4.7 is 4096
  tokens — short specs will silently bypass caching, which is fine.

Structured output is provided via Pydantic schemas at this layer; the
schemas are then translated into the existing dataclasses in
``cedar_agent.atoms`` so the rest of the pipeline (sugar compile-down,
grounding, etc.) stays unchanged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, Field

from cedar_agent.atoms import (
    ActionAtom,
    AttributeAtom,
    EntityAtom,
    TypeAliasAtom,
)


# ---------------------------------------------------------------------------
# Module defaults.
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "claude-opus-4-7"
DEFAULT_MAX_TOKENS = 16000
DEFAULT_EFFORT = "high"


def _load_prompt(name: str) -> str:
    """Load a prompt template from ``cedar_agent/prompts/<name>``."""
    path = Path(__file__).resolve().parent / "prompts" / name
    return path.read_text()


# ---------------------------------------------------------------------------
# Pydantic schemas for LLM-side structured output.
#
# These are deliberately a separate layer from ``cedar_agent.atoms``: the
# LLM gets a clean, discriminator-tagged shape; the rest of the pipeline
# keeps the dataclasses with sugar-specific validation in __post_init__.
# Translation lives in ``_translate_*`` helpers further down.
# ---------------------------------------------------------------------------


class _LLMContextAttribute(BaseModel):
    """Context-attribute fragment owned by an ActionAtom."""

    field_name: str
    cedar_type: str
    optional: bool = False
    rationale: str = ""
    plain_english_summary: str = ""


class _LLMEntityAtom(BaseModel):
    kind: Literal["entity"]
    name: str
    rationale: str
    plain_english_summary: str
    source_excerpt: str
    members_of: list[str] = Field(default_factory=list)
    enum_values: Optional[list[str]] = None


class _LLMAttributeAtom(BaseModel):
    kind: Literal["attribute"]
    name: str
    rationale: str
    plain_english_summary: str
    source_excerpt: str
    on_entity: str
    field_name: str
    cedar_type: str
    optional: bool = False
    alternatives_considered: list[str] = Field(default_factory=list)


class _LLMActionAtom(BaseModel):
    kind: Literal["action"]
    name: str
    rationale: str
    plain_english_summary: str
    source_excerpt: str
    principal_types: list[str] = Field(default_factory=list)
    resource_types: list[str] = Field(default_factory=list)
    context_attributes: list[_LLMContextAttribute] = Field(default_factory=list)
    parent_groups: list[str] = Field(default_factory=list)


class _LLMTypeAliasAtom(BaseModel):
    kind: Literal["type_alias"]
    name: str
    rationale: str
    plain_english_summary: str
    source_excerpt: str
    cedar_type: str


_LLMStage1Atom = Annotated[
    Union[_LLMEntityAtom, _LLMAttributeAtom, _LLMActionAtom, _LLMTypeAliasAtom],
    Field(discriminator="kind"),
]


class SchemaAtomsResponse(BaseModel):
    """Top-level structured response for schema atomization."""

    atoms: list[_LLMStage1Atom]


class SchemaFixResponse(BaseModel):
    """Top-level structured response for schema-fix retries."""

    fixed_schema_text: str
    explanation: str


# Translated atom types (returned by ``LLMClient.propose_schema_atoms``).
Stage1Atom = Union[EntityAtom, AttributeAtom, ActionAtom, TypeAliasAtom]


# ---------------------------------------------------------------------------
# Translation: Pydantic LLM atoms → cedar_agent.atoms dataclasses.
# ---------------------------------------------------------------------------


def _translate_entity(llm: _LLMEntityAtom) -> EntityAtom:
    return EntityAtom(
        name=llm.name,
        rationale=llm.rationale,
        plain_english_summary=llm.plain_english_summary,
        source_excerpt=llm.source_excerpt,
        members_of=list(llm.members_of),
        enum_values=list(llm.enum_values) if llm.enum_values is not None else None,
    )


def _translate_attribute(llm: _LLMAttributeAtom) -> AttributeAtom:
    return AttributeAtom(
        name=llm.name,
        rationale=llm.rationale,
        plain_english_summary=llm.plain_english_summary,
        source_excerpt=llm.source_excerpt,
        on_entity=llm.on_entity,
        field_name=llm.field_name,
        cedar_type=llm.cedar_type,
        optional=llm.optional,
        alternatives_considered=list(llm.alternatives_considered),
    )


def _translate_action(llm: _LLMActionAtom) -> ActionAtom:
    context_attrs: dict[str, AttributeAtom] = {}
    for ca in llm.context_attributes:
        # Context attributes are not owned by any entity; we still create an
        # AttributeAtom for them so the data model is uniform.
        context_attrs[ca.field_name] = AttributeAtom(
            name=f"{llm.name}__context__{ca.field_name}",
            rationale=ca.rationale or f"context attribute on action {llm.name}",
            plain_english_summary=ca.plain_english_summary,
            source_excerpt=llm.source_excerpt,
            on_entity="",
            field_name=ca.field_name,
            cedar_type=ca.cedar_type,
            optional=ca.optional,
        )
    return ActionAtom(
        name=llm.name,
        rationale=llm.rationale,
        plain_english_summary=llm.plain_english_summary,
        source_excerpt=llm.source_excerpt,
        principal_types=list(llm.principal_types),
        resource_types=list(llm.resource_types),
        context_attributes=context_attrs,
        parent_groups=list(llm.parent_groups),
    )


def _translate_type_alias(llm: _LLMTypeAliasAtom) -> TypeAliasAtom:
    return TypeAliasAtom(
        name=llm.name,
        rationale=llm.rationale,
        plain_english_summary=llm.plain_english_summary,
        source_excerpt=llm.source_excerpt,
        cedar_type=llm.cedar_type,
    )


def _translate_atom(llm_atom: Any) -> Stage1Atom:
    if isinstance(llm_atom, _LLMEntityAtom):
        return _translate_entity(llm_atom)
    if isinstance(llm_atom, _LLMAttributeAtom):
        return _translate_attribute(llm_atom)
    if isinstance(llm_atom, _LLMActionAtom):
        return _translate_action(llm_atom)
    if isinstance(llm_atom, _LLMTypeAliasAtom):
        return _translate_type_alias(llm_atom)
    raise TypeError(f"unknown LLM atom kind: {type(llm_atom).__name__}")


# ---------------------------------------------------------------------------
# LLMClient — the dependency-injection seam.
# ---------------------------------------------------------------------------


class LLMClient:
    """Thin wrapper around the Anthropic SDK for cedar_agent.

    Construction:
      - ``client``: an ``anthropic.Anthropic`` instance (or any object
        exposing ``.messages.parse(**kwargs)``). When omitted, a default
        ``anthropic.Anthropic()`` is constructed, which reads
        ``ANTHROPIC_API_KEY`` from the environment.
      - ``model``: model identifier; defaults to ``claude-opus-4-7``.
      - ``max_tokens``: per-call ceiling; defaults to 16000.
      - ``effort``: ``"low" | "medium" | "high" | "max"``; defaults to
        ``"high"`` per the skill guidance for intelligence-sensitive
        workloads.

    Tests pass a mock ``client`` whose ``.messages.parse(...)`` returns
    a hand-crafted response with ``.parsed_output`` populated. No
    network access required.
    """

    def __init__(
        self,
        *,
        client: Optional[Any] = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        effort: str = DEFAULT_EFFORT,
    ) -> None:
        if client is None:
            # Lazy-import the SDK so tests can run without ANTHROPIC_API_KEY
            # set; only the live path requires it.
            import anthropic

            client = anthropic.Anthropic()
        self._client = client
        self._model = model
        self._max_tokens = max_tokens
        self._effort = effort

    # ------------------------------------------------------------------
    # Stage 1: schema atom proposal.
    # ------------------------------------------------------------------

    def propose_schema_atoms(self, spec_text: str) -> list[Stage1Atom]:
        """Ask the LLM to propose Stage 1 atoms for a prose spec.

        The system prompt + spec block are marked ``cache_control``
        ``ephemeral`` so repeated calls in the same session amortize
        the input-token cost (per skill §Prompt Caching). The minimum
        cacheable prefix on Opus 4.7 is 4096 tokens — short specs will
        silently bypass the cache, which is harmless.
        """
        system_prompt = _load_prompt("schema_atomization.md")
        response = self._call_parse(
            system_prompt=system_prompt,
            spec_text=spec_text,
            user_turn=(
                "Propose the Stage 1 schema atoms for the spec above. "
                "Order them so each AttributeAtom appears AFTER the "
                "EntityAtom it lives on, and so ActionAtoms appear "
                "after the entities they reference."
            ),
            output_format=SchemaAtomsResponse,
        )
        return [_translate_atom(a) for a in response.parsed_output.atoms]

    # ------------------------------------------------------------------
    # Stage 1 fix: ask the LLM to fix a cedar-validate failure.
    # ------------------------------------------------------------------

    def answer_question_about_atom(
        self,
        atom: Stage1Atom,
        question: str,
        spec_text: str,
    ) -> str:
        """Answer a user's free-text question about one Stage 1 atom.

        Used by the interactive review loop's ``[Q]`` key. The atom is
        rendered as JSON in the user turn so the model has the full
        context (rationale, plain English, source excerpt, fields).
        Returns plain text — no structured output needed.
        """
        from cedar_agent.atoms import to_dict as _atom_to_dict

        atom_json = _atom_to_dict(atom)
        user_turn = (
            f"The user is reviewing this Stage 1 atom:\n\n"
            f"```json\n{atom_json}\n```\n\n"
            f"They ask: {question}\n\n"
            "Answer their question in 1–3 sentences. Stay focused on "
            "this atom and the spec; do not propose changes unless the "
            "user explicitly asks for one."
        )
        response = self._call_text(
            system_prompt=_load_prompt("schema_atomization.md"),
            spec_text=spec_text,
            user_turn=user_turn,
        )
        return response

    def propose_alternative_atom(
        self,
        rejected_atom: Stage1Atom,
        user_reason: str,
        spec_text: str,
    ) -> Optional[Stage1Atom]:
        """Propose a replacement for an atom the user rejected.

        Used by the interactive review loop's ``[R]`` key. Returns the
        first atom in the LLM's response (always re-using the same
        ``SchemaAtomsResponse`` schema for consistency), or ``None`` if
        the LLM declined to propose an alternative.
        """
        from cedar_agent.atoms import to_dict as _atom_to_dict

        atom_json = _atom_to_dict(rejected_atom)
        user_turn = (
            "The user rejected this Stage 1 atom:\n\n"
            f"```json\n{atom_json}\n```\n\n"
            f"Their reason: {user_reason}\n\n"
            "Propose ONE replacement atom of the same kind that "
            "addresses the user's concern. Return your proposal in "
            "the same SchemaAtomsResponse format (atoms list with a "
            "single entry). If you cannot improve on the rejected "
            "atom, return an empty atoms list."
        )
        response = self._call_parse(
            system_prompt=_load_prompt("schema_atomization.md"),
            spec_text=spec_text,
            user_turn=user_turn,
            output_format=SchemaAtomsResponse,
        )
        atoms = response.parsed_output.atoms
        if not atoms:
            return None
        return _translate_atom(atoms[0])

    def fix_schema(
        self,
        schema_text: str,
        cedar_error_message: str,
        spec_text: str,
    ) -> str:
        """Ask the LLM to fix a schema that ``cedar validate`` rejected.

        Returns the corrected schema text. The schema-fix prompt is a
        separate template; we keep the cache-controlled (system + spec)
        block consistent across calls so the cache continues to hit
        across propose/fix turns.
        """
        system_prompt = _load_prompt("schema_atomization.md")
        user_turn = (
            "The schema you proposed failed `cedar validate`. The "
            "validator error is:\n\n"
            f"```\n{cedar_error_message}\n```\n\n"
            "The current schema is:\n\n"
            f"```cedarschema\n{schema_text}\n```\n\n"
            "Produce a corrected schema. Keep the entity, attribute, "
            "action, and type-alias structure as close as possible to "
            "what you proposed previously — fix only what the validator "
            "rejected."
        )
        response = self._call_parse(
            system_prompt=system_prompt,
            spec_text=spec_text,
            user_turn=user_turn,
            output_format=SchemaFixResponse,
        )
        return response.parsed_output.fixed_schema_text

    # ------------------------------------------------------------------
    # Internal: shared parse helper.
    # ------------------------------------------------------------------

    def _call_parse(
        self,
        *,
        system_prompt: str,
        spec_text: str,
        user_turn: str,
        output_format: type[BaseModel],
    ) -> Any:
        """Call ``messages.parse`` with cache-controlled system+spec block.

        Caching layout (per skill §Prompt Caching):

          render order: tools → system → messages

          system: [
            {"type": "text", "text": <stable system prompt>},
            {"type": "text", "text": <spec wrapped in <spec> tags>,
             "cache_control": {"type": "ephemeral"}},   ← cache breakpoint
          ]
          messages: [{"role": "user", "content": <per-turn request>}]
                                                       ← uncached, varies

        Only one breakpoint is needed; the system+spec is the entire
        cached prefix.
        """
        return self._client.messages.parse(
            model=self._model,
            max_tokens=self._max_tokens,
            thinking={"type": "adaptive"},
            output_config={
                "effort": self._effort,
            },
            system=[
                {"type": "text", "text": system_prompt},
                {
                    "type": "text",
                    "text": f"<spec>\n{spec_text}\n</spec>",
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[{"role": "user", "content": user_turn}],
            output_format=output_format,
        )

    def _call_text(
        self,
        *,
        system_prompt: str,
        spec_text: str,
        user_turn: str,
    ) -> str:
        """Call ``messages.create`` for plain-text output (no Pydantic schema).

        Used by ``answer_question_about_atom``. The cache layout is
        identical to ``_call_parse`` so the system+spec cache is shared
        across propose / fix / answer calls in one session.
        """
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            thinking={"type": "adaptive"},
            output_config={
                "effort": self._effort,
            },
            system=[
                {"type": "text", "text": system_prompt},
                {
                    "type": "text",
                    "text": f"<spec>\n{spec_text}\n</spec>",
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[{"role": "user", "content": user_turn}],
        )
        # Extract the first text block (skip any thinking blocks).
        for block in response.content:
            if getattr(block, "type", None) == "text":
                return block.text
        return ""
