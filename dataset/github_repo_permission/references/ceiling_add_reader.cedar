// Ceiling: add_reader — admin only, not if archived
permit (
    principal is User,
    action == Action::"add_reader",
    resource is Repository
) when {
    principal in resource.admins &&
    !resource.isArchived
};
