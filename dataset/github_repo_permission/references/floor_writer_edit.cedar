// Floor: A writer who is also the reporter of an issue MUST be able to edit it
// (Ensures the writer path doesn't accidentally get blocked by the reporter check)
permit (
    principal is User,
    action == Action::"edit_issue",
    resource is Issue
) when {
    principal in resource.repo.writers &&
    principal != resource.reporter
};
