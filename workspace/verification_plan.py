"""
Verification Plan — Clinical Trial Data Platform.

10 checks:
- 2 ceiling implies (candidate ≤ ceiling, one per action)
- 2 floor implies (floor ≤ candidate, auditor loophole, one per action)
- 2 liveness (not trivially denied, one per action)
"""
import os

WORKSPACE = os.path.dirname(os.path.abspath(__file__))


def get_checks() -> list[dict]:
    checks = []

    # ===== SAFETY: ceiling implies (candidate must not exceed ceiling) =====

    checks.append({
        "name": "view_safety",
        "description": "View access must not exceed ceiling: role-gated, clearance/classification or context checks, Active project, dept match or auditor",
        "type": "implies",
        "principal_type": "User",
        "action": 'Action::"View"',
        "resource_type": "Document",
        "reference_path": os.path.join(WORKSPACE, "references", "ceiling_view.cedar"),
    })

    checks.append({
        "name": "edit_safety",
        "description": "Edit access must not exceed ceiling (same constraints as View per spec)",
        "type": "implies",
        "principal_type": "User",
        "action": 'Action::"Edit"',
        "resource_type": "Document",
        "reference_path": os.path.join(WORKSPACE, "references", "ceiling_edit.cedar"),
    })

    # ===== CORRECTNESS: floor implies (candidate must allow at least this) =====

    checks.append({
        "name": "auditor_loophole_view",
        "description": "GlobalAuditor must bypass cross-departmental block for View (floor ≤ candidate)",
        "type": "floor",
        "principal_type": "User",
        "action": 'Action::"View"',
        "resource_type": "Document",
        "floor_path": os.path.join(WORKSPACE, "references", "floor_auditor_view.cedar"),
    })

    checks.append({
        "name": "auditor_loophole_edit",
        "description": "GlobalAuditor must bypass cross-departmental block for Edit (floor ≤ candidate)",
        "type": "floor",
        "principal_type": "User",
        "action": 'Action::"Edit"',
        "resource_type": "Document",
        "floor_path": os.path.join(WORKSPACE, "references", "floor_auditor_edit.cedar"),
    })

    # ===== LIVENESS: policy must not trivially deny all =====

    checks.append({
        "name": "liveness_view",
        "description": "At least one View operation must be permitted",
        "type": "always-denies-liveness",
        "principal_type": "User",
        "action": 'Action::"View"',
        "resource_type": "Document",
    })

    checks.append({
        "name": "liveness_edit",
        "description": "At least one Edit operation must be permitted",
        "type": "always-denies-liveness",
        "principal_type": "User",
        "action": 'Action::"Edit"',
        "resource_type": "Document",
    })

    return checks
