// Existing organizational policy: all users can read non-locked resources
permit (
    principal,
    action == Action::"read",
    resource
) unless { resource.is_locked };
