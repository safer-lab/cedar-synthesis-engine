# Policy Specification

Write a Cedar policy that enforces the following rules:

## Access Control Requirements

1. **Delete Protection**: Only users in the Engineering department may delete production resources. Users in any other department (HR, Sales, etc.) must be denied delete access to production.

2. **Lock Enforcement**: No user — regardless of department — may delete a locked resource (`is_locked == true`).

3. **Liveness**: The policy must actually permit at least one delete operation. A trivial "deny everything" policy is not acceptable.

## Context

- The schema defines `User` entities with a `department` attribute and `Resource` entities with `environment` and `is_locked` attributes.
- Three actions exist: `read`, `write`, `delete`.
- An existing policy store already grants read access to non-locked resources.
