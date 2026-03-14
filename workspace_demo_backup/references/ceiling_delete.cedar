// Ceiling for delete operations:
// Only Engineering users may delete, and only unlocked resources.
// `check_implies(candidate, ceiling)` verifies the candidate
// never allows more than this.
permit (
    principal,
    action == Action::"delete",
    resource
) when {
    principal.department == "Engineering" && !resource.is_locked
};
