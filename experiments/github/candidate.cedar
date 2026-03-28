// === GitHub Candidate — Iteration 2 ===
// Planted bugs:
// 1. Missing isArchived check on push (should be forbidden for archived repos)
// 2. Missing reporter self-edit for edit_issue (only writer path)
// 3. Missing reporter self-delete for delete_issue (only maintainer path)

// --- Reader: pull ---
permit (
    principal is User,
    action == Action::"pull",
    resource is Repository
) when {
    principal in resource.readers
};

// --- Reader: fork ---
permit (
    principal is User,
    action == Action::"fork",
    resource is Repository
) when {
    principal in resource.readers
};

// --- Writer: push (FIXED: added archive check) ---
permit (
    principal is User,
    action == Action::"push",
    resource is Repository
) when {
    principal in resource.writers &&
    !resource.isArchived
};

// --- Triager: assign_issue ---
permit (
    principal is User,
    action == Action::"assign_issue",
    resource is Issue
) when {
    principal in resource.repo.triagers
};

// --- edit_issue: writer edit any OR reader self-edit (FIXED) ---
permit (
    principal is User,
    action == Action::"edit_issue",
    resource is Issue
) when {
    principal in resource.repo.writers
};

permit (
    principal is User,
    action == Action::"edit_issue",
    resource is Issue
) when {
    principal in resource.repo.readers &&
    principal == resource.reporter
};

// --- delete_issue: maintainer delete any OR reader self-delete (FIXED) ---
permit (
    principal is User,
    action == Action::"delete_issue",
    resource is Issue
) when {
    principal in resource.repo.maintainers
};

permit (
    principal is User,
    action == Action::"delete_issue",
    resource is Issue
) when {
    principal in resource.repo.readers &&
    principal == resource.reporter
};

// --- Admin: add roles ---
permit (
    principal is User,
    action in [Action::"add_reader", Action::"add_triager",
               Action::"add_writer", Action::"add_maintainer",
               Action::"add_admin"],
    resource is Repository
) when {
    principal in resource.admins &&
    !resource.isArchived
};
