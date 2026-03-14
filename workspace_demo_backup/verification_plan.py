"""
Verification Plan for the Cedar Synthesis Engine.

This defines the list of checks to run against the candidate policy.
Each check maps to a `cedar symcc` command.

Agent A generates this file from the NL policy spec.
The human reviews it before the synthesis loop begins.
"""
import os

WORKSPACE = os.path.dirname(os.path.abspath(__file__))


def get_checks() -> list[dict]:
    """
    Returns a list of verification check descriptors.

    Each check has:
      - "name": identifier
      - "description": human-readable
      - "type": "implies" | "always-denies-liveness" | "never-errors"
      - "principal_type": Cedar entity type
      - "action": Cedar action UID
      - "resource_type": Cedar entity type
      - "reference_path": (for implies only) path to reference policy file
    """
    checks = []

    # --- Safety: candidate must not be more permissive than the ceiling ---
    # Ceiling: Engineering can delete unlocked resources
    checks.append({
        "name": "engineering_only_delete",
        "description": "Only Engineering users may delete; locked resources must be denied delete",
        "type": "implies",
        "principal_type": "User",
        "action": 'Action::"delete"',
        "resource_type": "Resource",
        "reference_path": os.path.join(WORKSPACE, "references", "ceiling_delete.cedar"),
    })

    # --- Liveness: the policy must not trivially deny all deletes ---
    checks.append({
        "name": "liveness_delete",
        "description": "At least one delete operation must be allowed",
        "type": "always-denies-liveness",
        "principal_type": "User",
        "action": 'Action::"delete"',
        "resource_type": "Resource",
    })

    # --- Sanity: no runtime errors ---
    checks.append({
        "name": "no_errors_delete",
        "description": "Policy must not produce runtime errors for delete requests",
        "type": "never-errors",
        "principal_type": "User",
        "action": 'Action::"delete"',
        "resource_type": "Resource",
    })

    checks.append({
        "name": "no_errors_read",
        "description": "Policy must not produce runtime errors for read requests",
        "type": "never-errors",
        "principal_type": "User",
        "action": 'Action::"read"',
        "resource_type": "Resource",
    })

    return checks
