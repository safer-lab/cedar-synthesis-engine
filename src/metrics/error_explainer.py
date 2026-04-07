from __future__ import annotations

import re


def explain_validation_error(message: str) -> dict:
    text = message.strip()
    lowered = text.lower()

    if "unexpected token `{`" in text and "when {" in text and "expected `(`" in text:
        return {
            "category": "syntax",
            "summary": "The policy likely ended before a `when` clause was attached.",
            "likely_cause": (
                "A `permit` or `forbid` statement was probably terminated with `;` "
                "before `when { ... }` was written."
            ),
            "suggested_fix": (
                "Attach `when { ... }` directly to the `permit (...)` or `forbid (...)` "
                "statement, and place the final `;` only at the end."
            ),
        }

    if "unexpected end of input" in lowered and "expected `;`" in text:
        return {
            "category": "syntax",
            "summary": "The generated Cedar is missing a terminating semicolon.",
            "likely_cause": "At least one statement was not closed with `;`.",
            "suggested_fix": "Ensure each full Cedar policy statement ends with `;`.",
        }

    if "failed to parse policy set" in lowered:
        return {
            "category": "syntax",
            "summary": "Cedar could not parse the generated policy.",
            "likely_cause": (
                "The statement structure is malformed, such as misplaced `when`, "
                "missing punctuation, or invalid Cedar syntax."
            ),
            "suggested_fix": (
                "Check statement boundaries, parentheses, braces, and semicolons. "
                "Keep `when` clauses attached to the same policy statement."
            ),
        }

    attr_match = re.search(r"attribute `([^`]+)` on entity type `([^`]+)` not found", text)
    if attr_match:
        attr_name, entity_type = attr_match.groups()
        return {
            "category": "schema",
            "summary": f"The policy references an attribute not defined on `{entity_type}`.",
            "likely_cause": (
                f"The model used `{attr_name}`, but that attribute does not exist on `{entity_type}` "
                f"in the schema."
            ),
            "suggested_fix": (
                f"Replace `{attr_name}` with a real attribute from the schema for `{entity_type}`."
            ),
        }

    action_match = re.search(r"action `([^`]+)` .* not found", text)
    if action_match:
        action_name = action_match.group(1)
        return {
            "category": "schema",
            "summary": f"The policy references an action not present in the schema: `{action_name}`.",
            "likely_cause": "The model hallucinated an action name or used the wrong task action.",
            "suggested_fix": "Use the exact action identifiers defined in the schema.",
        }

    entity_match = re.search(r"entity type `([^`]+)` not found", text)
    if entity_match:
        entity_type = entity_match.group(1)
        return {
            "category": "schema",
            "summary": f"The policy references an entity type not present in the schema: `{entity_type}`.",
            "likely_cause": "The model hallucinated an entity type or used the wrong one.",
            "suggested_fix": "Use the exact entity type names defined in the schema.",
        }

    if "policy set validation failed" in lowered:
        return {
            "category": "schema",
            "summary": "The policy parses, but it does not ground correctly to the schema.",
            "likely_cause": (
                "The model likely used a missing identifier, wrong type, or invalid appliesTo combination."
            ),
            "suggested_fix": "Compare every entity type, action, and attribute against the schema exactly.",
        }

    return {
        "category": "unknown",
        "summary": "The validator returned an error that is not yet mapped to a custom explanation.",
        "likely_cause": "Inspect the raw Cedar validation output.",
        "suggested_fix": "Use the raw error text and schema to diagnose the issue.",
    }
