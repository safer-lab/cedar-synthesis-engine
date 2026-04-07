// Ceiling: pull — reader or higher can pull
permit (
    principal is User,
    action == Action::"pull",
    resource is Repository
) when {
    principal in resource.readers
};
