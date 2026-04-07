// Floor: A reader who is the reporter MUST be able to delete their own issue
// (Ensures the reporter self-delete path works even without maintainer role)
permit (
    principal is User,
    action == Action::"delete_issue",
    resource is Issue
) when {
    principal in resource.repo.readers &&
    principal == resource.reporter &&
    !(principal in resource.repo.maintainers)
};
