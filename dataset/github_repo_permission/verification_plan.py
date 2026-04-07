"""
GitHub Repository Permissions — Verification Plan

Checks:
  - 5 ceiling/safety (pull, push, edit_issue, delete_issue, add_reader)
  - 2 floor/correctness (writer_edit, reporter_delete)
  - 2 liveness (push, edit_issue)
"""
import os

REFS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "references")


def get_checks():
    return [
        # === Ceiling checks (candidate ≤ ceiling) ===
        {
            "name": "pull_safety",
            "description": "Pull access only for readers (or members of reader group)",
            "type": "implies",
            "principal_type": "User",
            "action": 'Action::"pull"',
            "resource_type": "Repository",
            "reference_path": os.path.join(REFS, "ceiling_pull.cedar"),
        },
        {
            "name": "push_safety",
            "description": "Push access only for writers, blocked if repo is archived",
            "type": "implies",
            "principal_type": "User",
            "action": 'Action::"push"',
            "resource_type": "Repository",
            "reference_path": os.path.join(REFS, "ceiling_push.cedar"),
        },
        {
            "name": "edit_issue_safety",
            "description": "Edit issue only if (reader + reporter) OR writer",
            "type": "implies",
            "principal_type": "User",
            "action": 'Action::"edit_issue"',
            "resource_type": "Issue",
            "reference_path": os.path.join(REFS, "ceiling_edit_issue.cedar"),
        },
        {
            "name": "delete_issue_safety",
            "description": "Delete issue only if (reader + reporter) OR maintainer",
            "type": "implies",
            "principal_type": "User",
            "action": 'Action::"delete_issue"',
            "resource_type": "Issue",
            "reference_path": os.path.join(REFS, "ceiling_delete_issue.cedar"),
        },
        {
            "name": "add_reader_safety",
            "description": "Add reader only if admin, blocked if repo is archived",
            "type": "implies",
            "principal_type": "User",
            "action": 'Action::"add_reader"',
            "resource_type": "Repository",
            "reference_path": os.path.join(REFS, "ceiling_add_reader.cedar"),
        },

        # === Floor checks (floor ≤ candidate) ===
        {
            "name": "writer_edit_floor",
            "description": "Writers MUST be able to edit issues they did NOT report (writer path independent of reporter)",
            "type": "floor",
            "principal_type": "User",
            "action": 'Action::"edit_issue"',
            "resource_type": "Issue",
            "floor_path": os.path.join(REFS, "floor_writer_edit.cedar"),
        },
        {
            "name": "reporter_delete_floor",
            "description": "Readers who are the reporter MUST be able to delete their own issue (without maintainer role)",
            "type": "floor",
            "principal_type": "User",
            "action": 'Action::"delete_issue"',
            "resource_type": "Issue",
            "floor_path": os.path.join(REFS, "floor_reporter_delete.cedar"),
        },

        # === Liveness checks ===
        {
            "name": "liveness_push",
            "description": "Push policy is not trivially deny-all",
            "type": "always-denies-liveness",
            "principal_type": "User",
            "action": 'Action::"push"',
            "resource_type": "Repository",
        },
        {
            "name": "liveness_edit_issue",
            "description": "Edit issue policy is not trivially deny-all",
            "type": "always-denies-liveness",
            "principal_type": "User",
            "action": 'Action::"edit_issue"',
            "resource_type": "Issue",
        },
    ]
