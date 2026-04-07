# Cedar Syntax Cheat Sheet

Use only valid Cedar syntax.

## Basic Permit Rule

```cedar
permit (
    principal is User,
    action == Action::"view",
    resource is Document
) when {
    principal.department == resource.department
};
```

## Basic Forbid Rule

```cedar
forbid (
    principal is User,
    action == Action::"edit",
    resource is Document
) when {
    resource.isLocked
};
```

## Common Patterns

### Group membership

```cedar
principal in resource.readers
principal in resource.repo.writers
principal in Role::"Admin"
```

### Equality

```cedar
principal == resource.owner
principal != resource.reporter
```

### Boolean conditions

```cedar
!resource.isArchived
context.isCompliantDevice
principal.clearanceLevel > 3
```

### Action groups

```cedar
action in [Action::"add_reader", Action::"add_writer"]
```

## Important Rules

- Cedar denies by default.
- `forbid` overrides `permit`.
- Use exact entity names, action names, and attributes from the schema.
- Output only Cedar policy code.
- End each policy statement with `;`.

