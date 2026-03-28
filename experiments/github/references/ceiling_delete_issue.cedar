// Ceiling: delete_issue — reporter+reader OR maintainer can delete
permit (
    principal is User,
    action == Action::"delete_issue",
    resource is Issue
) when {
    (principal in resource.repo.readers && principal == resource.reporter) ||
    principal in resource.repo.maintainers
};
