# CedarBench: 100 Proposed Hard Scenarios (v2 Extension)

A design document for 100 adversarial scenarios intended to stress the
harness beyond the current 121/121 PASS baseline. Each scenario is
grounded in either (a) a Cedar language feature we haven't pushed to
its limits, (b) a real compliance framework requirement, or (c) an
authorization pattern documented in production systems.

All scenarios are designed to be **faithful to Cedar's actual
semantics**. Where a feature has known symcc limitations (e.g., entity
tags, entity-graph liveness), we note it and propose the attribute-based
workaround.

## Research basis

This document draws on:

- [Cedar data types reference](https://docs.cedarpolicy.com/policies/syntax-datatypes.html) — decimal, ipaddr, datetime, duration, Long ranges, Set homogeneity
- [Cedar operators reference](https://docs.cedarpolicy.com/policies/syntax-operators.html) — if-then-else, like, has, in, method vs constructor syntax, no division
- [Cedar validation reference](https://docs.cedarpolicy.com/policies/validation.html) — known validation limitations, overflow not caught, entity existence not checked
- [Cedar entity tags RFC 0082](https://github.com/cedar-policy/rfcs/blob/main/text/0082-entity-tags.md) — hasTag/getTag, Set-of-Set type
- [Cedar symcc paper](https://arxiv.org/pdf/2403.04651) — decidability properties, verified properties (always-allows, always-denies, subsumption, equivalence, disjointness)
- [HIPAA Minimum Necessary Rule](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/minimum-necessary-requirement/index.html) — purpose-bound access, role-based minimum
- [HIPAA break-glass requirements](https://hipaa.yale.edu/security/break-glass-procedure-granting-emergency-access-critical-ephi-systems) — emergency access with audit
- [SOX separation of duties](https://www.conductorone.com/guides/sox-access-controls-separation-of-duties-and-best-practices/) — trader/settlement/audit segregation
- [GDPR purpose limitation (Art. 5.1.b)](https://www.auditfront.com/frameworks/gdpr/principles/art-5-1b/) — purpose tagging + access control
- [PCI-DSS tokenization scope boundaries](https://www.pcisecuritystandards.org/documents/Tokenization_Guidelines_Info_Supplement.pdf) — CDE vs out-of-scope
- [ITAR/EAR deemed export rules](https://exportcontrol.lbl.gov/training/export-control-overview/) — US persons, controlled tech data
- [FERPA rights transition at 18](https://epic.org/family-educational-rights-and-privacy-act-ferpa/) — parent/student rights transfer
- [COPPA verifiable parental consent](https://www.ftc.gov/business-guidance/resources/complying-coppa-frequently-asked-questions) — under-13 rules
- [AML/KYC tiered due diligence](https://www.neotas.com/risk-based-approach-to-aml-for-customer-due-diligence-in-kyc-aml-operations/) — risk-based EDD
- [NIST SP 800-162 ABAC](https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-162.pdf) — attribute-based access control
- [OAuth 2.0 RAR (RFC 9396)](https://datatracker.ietf.org/doc/draft-ietf-oauth-rar/12/) — fine-grained authorization_details
- [Zero Trust continuous authorization](https://www.strongdm.com/blog/continuous-zero-trust-authorization) — context-aware, real-time policy
- [Data residency post-Schrems II](https://www.kiteworks.com/gdpr-compliance/eu-data-sovereignty-gdpr-compliance/) — cross-border transfer restrictions

---

## Scenario categorization

Each scenario is tagged with:

- **Stress axis**: what the scenario primarily stresses (feature, scale, semantics, composition, meta)
- **Primary harness contribution it targets**: which §8.x might be challenged or may need to evolve
- **Why it's hard**: concrete reason Haiku should struggle

---

## Batch 1: Cedar Feature Completeness (scenarios 1–10)

Push the specific Cedar features we haven't exercised deeply.

### 1. `decimal_currency_comparison`
- **Feature**: Cedar's `decimal` extension with `.lessThan()`/`.greaterThan()` method syntax (not `<`/`>`)
- **Pattern**: currency amounts in a payment system with thresholds at decimal boundaries
- **Why hard**: LLMs default to `<`/`>` operators. `decimal` requires method-style comparison, which is §8.11-class syntax mismatch. Also: decimal has 4-digit precision ceiling (`922337203685477.5807`), values near boundary will error.
- **Representative property**: "Transactions above $10,000.0000 require additional approval."

### 2. `ipaddr_corporate_network`
- **Feature**: `ipaddr` extension with `.isInRange()` method and CIDR notation
- **Pattern**: access permitted only from corporate subnets (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) EXCLUDING a known compromised range (10.50.0.0/16)
- **Why hard**: Requires combining `.isInRange()` with negation across 4 CIDR blocks. Model priors default to string comparison on IP addresses.

### 3. `ipaddr_ipv6_mixed`
- **Feature**: `ipaddr` extension with IPv6 CIDR (`ip("1:2:3:4::/48")`)
- **Pattern**: dual-stack data center access with both IPv4 and IPv6 ranges
- **Why hard**: LLMs rarely produce IPv6 examples; `.isIpv4()` / `.isIpv6()` discrimination required.

### 4. `if_then_else_decision_tree`
- **Feature**: Cedar's `if ... then ... else` expression operator (distinct from policy-level `when`)
- **Pattern**: nested 3-level decision tree encoding incident severity routing
- **Why hard**: LLMs may use the `&&`/`||` desugaring instead of the native `if` operator, or confuse expression-level `if` with `when` clause. §8.11 analog but requires the *correct* use of a feature, not avoidance.

### 5. `enumerated_status_entity`
- **Feature**: enumerated entity types — `entity Status in [Status::"active", Status::"pending", Status::"archived"]`
- **Pattern**: resource lifecycle with status transitions governed by role
- **Why hard**: enumerated entities have NO attributes, NO ancestors, NO tags. LLMs trained on string-typed status will try to add them. Validator rejects invalid enum literals but only if validation is strict.

### 6. `common_type_definitions`
- **Feature**: Cedar schema `type <Id> = <Type>` common type definitions
- **Pattern**: shared `Address` and `ContactInfo` record types used across 5 entity types
- **Why hard**: LLMs inline types repeatedly instead of using common type references. Also tests that reserved type names (Bool, Long, Set, etc.) are avoided.

### 7. `union_principal_types`
- **Feature**: action with multiple principal types `appliesTo { principal: [User, ApiKey, ServiceAccount] }`
- **Pattern**: API gateway where any of 3 principal types can call certain actions, each with different rules
- **Why hard**: single policy must branch on `principal is User` vs `principal is ApiKey` vs `principal is ServiceAccount` with correct has-guarding per type (each type has different attributes).

### 8. `action_group_multi_inheritance`
- **Feature**: action hierarchy — `action Read in [ReadOnly, SafeOperations]` (multiple parent groups)
- **Pattern**: action belongs to two overlapping groups (e.g., "read-only" AND "audit-logged")
- **Why hard**: `action in Group::"X"` transitivity across multiple parents; policy must not assume tree structure.

### 9. `entity_tags_with_hastag`
- **Feature**: Cedar entity tags (RFC 0082) with `hasTag` / `getTag` operators
- **Pattern**: resources tagged with `Set<String>` values per key; user-tag intersection determines access
- **Why hard**: this is a recent Cedar feature. LLMs don't know `hasTag`/`getTag` exists and default to `.contains()` on an attribute, which doesn't work for dynamically-keyed tags.

### 10. `long_arithmetic_overflow_avoidance`
- **Feature**: Cedar `Long` arithmetic with `+`/`-`/`*` and the critical limitation: no overflow detection at validation time
- **Pattern**: budget tracking where `context.spent + context.requested` must stay under a ceiling
- **Why hard**: naive encoding can overflow at runtime even when validation passes. Planner must structure the comparison to avoid intermediate overflow (rewrite `a + b > c` as `a > c - b` when b < c, etc.).

---

## Batch 2: Temporal Complexity (scenarios 11–20)

Push datetime and duration to their limits.

### 11. `rolling_rate_limit_window`
- **Feature**: `duration` arithmetic with context-provided counter for "requests in last N minutes"
- **Pattern**: API rate limit "max 100 requests in last 60 minutes"
- **Why hard**: The counter must be supplied by the host app via context. Policy verifies the attestation but can't count events itself. Multi-attribute correlation between `context.now`, `context.window_start`, and `context.count_in_window`.

### 12. `business_hours_user_timezone`
- **Feature**: datetime comparison with user-provided timezone offset as `duration`
- **Pattern**: access permitted during business hours in user's local timezone (user has `timezoneOffset: duration`)
- **Why hard**: `context.now.offset(user.timezoneOffset).toTime() >= duration("9h")`. Requires understanding `.toTime()` returns a duration-of-day, and datetime arithmetic composition.

### 13. `grace_period_three_tier`
- **Feature**: four-tier temporal logic: pre-warning, warning, grace, denied
- **Pattern**: cert expires at T; warning from T-7d; grace (with logging) T to T+30d; hard deny after T+30d
- **Why hard**: three datetime comparisons with matching durations. Each property (`permit_warning`, `permit_grace_with_audit`, `forbid_post_grace`) has bounded overlap with others. §8.8 floor-consistency stressed.

### 14. `recurring_maintenance_window`
- **Feature**: datetime modulo arithmetic (implemented via duration math)
- **Pattern**: access denied every Sunday 02:00-04:00 UTC (recurring weekly)
- **Why hard**: Cedar has no modulo operator. Must encode as "(now - epoch_sunday_0200) mod 7d < 2h" using offset and subtraction. Edge case: what if `now < epoch_sunday_0200`?

### 15. `age_verification_leap_years`
- **Feature**: `datetime.durationSince()` with year arithmetic at day granularity
- **Pattern**: user must be ≥18 at request time, computed from DOB
- **Why hard**: Cedar has no year arithmetic. Must use `context.now.durationSince(user.dob).toDays() >= 6575` (~18 years). The `6575` figure is exact only on average; leap year edge cases mean some 18-year-olds get denied if the math is wrong.

### 16. `multi_cert_chain_validity`
- **Feature**: multiple datetime windows with interval intersection
- **Pattern**: user cert valid [A, B], org cert valid [C, D], CA cert valid [E, F]; access permitted during `[max(A,C,E), min(B,D,F)]`
- **Why hard**: 3-way interval intersection requires 6 datetime comparisons. Naive encoding with `||` instead of `&&` produces wrong semantics.

### 17. `delegation_chain_expiry`
- **Feature**: nested time-bounded delegations
- **Pattern**: owner delegates to A at T1 for 30d; A delegates to B at T2 for 7d; B's permission valid only during `[max(T1,T2), min(T1+30d, T2+7d)]`
- **Why hard**: two optional context attributes (`firstGrant`, `secondGrant`), each a record with expiry fields. Must has-guard both, compute interval intersection.

### 18. `cascading_session_expiry`
- **Feature**: parent-child session relationship with cascading expiry
- **Pattern**: child session expires when parent does, even if child's own expiry is later
- **Why hard**: must encode `effectiveExpiry = min(parent.expiry, self.expiry)`. Cedar has no `min` — must use `if p < s then p else s` or `(p <= s && cond(p)) || (s < p && cond(s))`.

### 19. `embargo_by_region`
- **Feature**: region-indexed datetime lookup
- **Pattern**: content release datetime varies by region; user's region attribute determines applicable embargo
- **Why hard**: resource has `releaseByRegion: { us: datetime, eu: datetime, apac: datetime }` (nested record). User has `region: String`. Policy must pick the right datetime for the user's region — Cedar records don't have dynamic key access. Must explicitly branch on user.region value.

### 20. `duration_arithmetic_composition`
- **Feature**: multi-step duration arithmetic with sign handling
- **Pattern**: "expiration is 90 days from today, minus any grace already used"
- **Why hard**: `duration("90d") - (context.now.durationSince(user.graceStart))` — needs correct type arithmetic. Negative durations valid but subtle.

---

## Batch 3: Complex Role Interactions (scenarios 21–30)

Push the §8.6 role-intersection trap beyond 2-way.

### 21. `five_way_role_intersection`
- **Feature**: user in 5 roles {admin, auditor, dev, qa, support}, each with overlapping permits
- **Pattern**: specific action requires specific role combinations (admin OR (auditor AND dev))
- **Why hard**: §8.6 was tested at 2-way. 5-way has 2^5 = 32 role combinations. Current trap detector must correctly identify offending clauses when 5 forbids are in play.

### 22. `anti_transitive_delegation`
- **Feature**: delegation chain with depth limit
- **Pattern**: owner can delegate to agent; agent CANNOT delegate further
- **Why hard**: encode without role-keyed forbid (§8.6 violation). Solution: delegation only valid when `context.delegationDepth == 1`. Requires planner to structure the attestation correctly.

### 23. `three_way_mutual_exclusion`
- **Feature**: 3 actions pairwise mutually exclusive for same principal
- **Pattern**: same person cannot {submit, approve, audit} — any pair forbidden
- **Why hard**: naive encoding needs C(3,2) = 3 forbids. Each forbid must be written to avoid blocking valid multi-role users who do different actions on different resources.

### 24. `context_scoped_admin`
- **Feature**: "admin" permissions only apply within assigned tenant
- **Pattern**: user has `adminOf: Set<Tenant>` attribute; admin powers only when `resource.tenant in principal.adminOf`
- **Why hard**: cross-tenant admin attempts must be denied even if user.role == "admin". Must encode per-tenant permit, not blanket admin permit.

### 25. `role_elevation_with_attestation`
- **Feature**: temporary role elevation requiring context-supplied justification
- **Pattern**: role X → role Y requires `context.elevationJustification` to be non-empty
- **Why hard**: Cedar strings can be empty but "non-empty" isn't a primitive check. Must use `context.elevationJustification != ""` or `context.elevationJustification like "?*"` — LLMs won't know the idiomatic form.

### 26. `hierarchical_override_three_levels`
- **Feature**: role hierarchy with per-level overrides
- **Pattern**: `junior` inherits from `senior` except on `criticalAction`; `senior` inherits from `lead` except on `restrictedAction`
- **Why hard**: 3-level role hierarchy with exception paths. Must avoid double-blocking when both levels would override.

### 27. `priority_based_role_resolution`
- **Feature**: numeric priority attribute on role; highest-priority matching rule wins
- **Pattern**: role entities have `priority: Long`; when user in multiple roles, highest priority rule applies
- **Why hard**: Cedar's permit/forbid semantics are union/intersection, not priority-based. Must simulate priority with explicit `!(higher_priority_role_matches)` guards on every permit.

### 28. `cert_required_role_activation`
- **Feature**: role active only when valid cert present
- **Pattern**: `context.cert?: Cert` (optional); role X active only when cert present, validated, and claims role X
- **Why hard**: nested optional check; must has-guard cert, then check cert.validUntil > now, then check cert.claimedRole == "X". Triple `has`-guard chain.

### 29. `role_composition_from_attributes`
- **Feature**: effective role is computed, not declared
- **Pattern**: role = f(employmentStatus, seniority, certifications) — e.g. "manager" = (seniority >= 5 AND certs contains "MGMT-101")
- **Why hard**: role is implicit in attribute combination, not explicit. Policy must not check `principal.role` but compute equivalent conditions inline.

### 30. `dual_owner_joint_consent`
- **Feature**: resource with 2 owners; action requires consent from both
- **Pattern**: resource.owner1 and resource.owner2; any action requires context-supplied attestation from both
- **Why hard**: must encode as "context has consent1 AND consent1.signer == owner1 AND context has consent2 AND consent2.signer == owner2". Four-way conjunction on optional attributes.

---

## Batch 4: Conflict and Precedence (scenarios 31–40)

### 31. `four_level_unless_chain`
- **Feature**: deeply nested conditional denials
- **Pattern**: "forbid X unless A, unless B, unless C, unless D" (4-level exception chain)
- **Why hard**: Cedar has no `unless unless` syntax. Must use boolean: `!X || (!A || (!B || (!C || D)))`. Easy to mangle precedence.

### 32. `five_orthogonal_forbids`
- **Feature**: 5 independent forbid rules, each with different condition
- **Pattern**: blocked users, archived resources, off-hours, non-MFA, rate-limited
- **Why hard**: every floor must be disjoint from all 5 forbids (§8.8 stressed 5-way instead of 2-way).

### 33. `default_scope_mismatch`
- **Feature**: implicit default at one scope, explicit override at another
- **Pattern**: tenant-level "default deny write" vs user-level "permit admin write" — which wins?
- **Why hard**: Cedar is permit-union + forbid-intersect. Tenant default as forbid with user override needs exception encoded carefully.

### 34. `exception_to_exception`
- **Feature**: 3-level nested emergency override
- **Pattern**: normal lockout → break-glass override → security-team lockdown overrides the break-glass
- **Why hard**: 3-layer conditional that's easy to encode as just 2 layers. Must track all 3 separately.

### 35. `conflicting_attestation_sources`
- **Feature**: two attributes that can disagree
- **Pattern**: `resource.claimedOwner` (in resource data) vs `context.currentOwner` (in request context) — if they disagree, deny
- **Why hard**: equality check on two entity references, with both being potentially absent (resource attribute could be null-equivalent via optional).

### 36. `whitelist_and_blacklist`
- **Feature**: conjunction of positive and negative membership
- **Pattern**: must be in whitelist Set AND NOT in blacklist Set
- **Why hard**: §8.6 prevents `!(principal in Role::"X")` patterns. Set-based whitelist/blacklist uses `.contains()` which is different from entity `in`. Must distinguish.

### 37. `union_semantics_adversarial`
- **Feature**: two permit rules that individually are fine but together permit unintended access
- **Pattern**: permit1 for group A, permit2 for action X; user in group A acting on action X gets both permits — the intersection of their conditions
- **Why hard**: Cedar permits union (OR), so the access is granted if EITHER permit matches. Planner must ensure no accidental overlap.

### 38. `forbid_with_specific_exception`
- **Feature**: global forbid with narrowly-scoped exception
- **Pattern**: "deny all access to archived resources UNLESS the principal is the resource owner AND action is `view`"
- **Why hard**: exception-to-forbid cannot be encoded as a permit (permits don't override forbids in Cedar). Must weaken the forbid condition: `forbid ... when { resource.archived && !(principal == resource.owner && action == view) }`.

### 39. `n_of_m_signature_withdrawal`
- **Feature**: threshold signature with withdrawable signatures
- **Pattern**: 3-of-5 signers approve via `context.activeSigners: Set<User>`; signers can withdraw
- **Why hard**: must compute `context.activeSigners.size() >= 3` BUT Cedar has no `.size()` operator on sets. Must use `.containsAll(knownThreeSigners)` across multiple permits.

### 40. `revocation_cascade_reinstatement`
- **Feature**: parent revocation cascades to derived permissions; re-approval re-derives
- **Pattern**: access via `context.grantChain: Set<Grant>` where one revoked grant invalidates all derived
- **Why hard**: any grant in chain having `revoked == true` invalidates all; must use `.containsAny` with set of revoked grants or equivalent.

---

## Batch 5: Scale and Stress (scenarios 41–50)

### 41. `mega_scale_500_checks`
- **Stress**: 500 verification properties (3x hundred_check_scale)
- **Pattern**: 25 roles × 20 actions RBAC matrix
- **Why hard**: conversation trimming, feedback size, solver batching. The harness must handle 500-property verification output without truncation.

### 42. `mega_scale_1000_checks`
- **Stress**: 1000 verification properties
- **Pattern**: 50 roles × 20 actions matrix
- **Why hard**: this is the ceiling of what single-pass symcc can handle. Tests whether the harness can split or batch verification.

### 43. `twenty_action_workflow`
- **Stress**: 20 distinct actions in a single scenario
- **Pattern**: procurement workflow (request, review, approve, reject, escalate, delegate, cancel, resubmit, audit, close, reopen, archive, export, sign, countersign, annotate, comment, notify, cc, bcc)
- **Why hard**: cross-action interactions; per-action rules; large action group inheritance.

### 44. `fifty_role_matrix`
- **Stress**: 50 roles, 10 actions = 500 matrix cells
- **Pattern**: auto-generated but with non-uniform role-action permissions
- **Why hard**: planner must produce 500 references without mistakes; validator must handle long policy set.

### 45. `ten_level_hierarchy`
- **Stress**: 10-level deep entity hierarchy (Org → Co → Region → Div → Dept → Team → Squad → Group → Pair → Individual)
- **Pattern**: transitive `in` across 10 levels
- **Why hard**: max symcc hierarchy support; deep chains may hit recursion limits.

### 46. `five_namespace_coordination`
- **Stress**: 5 top-level namespaces with cross-namespace entity references
- **Pattern**: `Identity::User`, `Billing::Invoice`, `Catalog::Product`, `Shipping::Address`, `Audit::Event` — policies span all five
- **Why hard**: qualified names throughout; namespace precedence; potential `__cedar` collisions.

### 47. `long_permit_body_25_conditions`
- **Stress**: single permit with 25+ conditions in `when` clause
- **Pattern**: enterprise policy with many attestations required simultaneously
- **Why hard**: line-length, readability, and hash-oscillation avoidance.

### 48. `fifteen_optional_context_attrs`
- **Stress**: 15 optional context attributes, many interdependent
- **Pattern**: 15 different attestation tokens, subsets required based on action
- **Why hard**: has-guarding discipline across 15 attributes; §8.3 stress test.

### 49. `wide_set_specific_elements`
- **Stress**: Set<String> attribute with 50 specific element predicates
- **Pattern**: tag-based with 50 specific tags that each map to specific permission
- **Why hard**: `resource.tags.contains("env:prod") && !resource.tags.contains("region:restricted") && ...` — 50 such clauses.

### 50. `hundred_tenant_isolation`
- **Stress**: 100 distinct tenants with different ACL patterns per tenant
- **Pattern**: multi-tenant SaaS with per-tenant custom rules
- **Why hard**: tenant-scoped rule generation; planner must not over-generalize.

---

## Batch 6: Realistic Compliance (scenarios 51–60)

Each cites a real regulatory framework.

### 51. `hipaa_minimum_necessary`
- **Framework**: [HIPAA Privacy Rule §164.502(b)](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/minimum-necessary-requirement/index.html)
- **Pattern**: role-based access to specific PHI field categories; disclosure limited to declared purpose
- **Why hard**: encode "only fields needed for stated purpose" — requires `context.declaredPurpose` and `resource.fieldsByPurpose: { treatment: Set<String>, billing: Set<String>, research: Set<String> }`. Purpose-to-field lookup via branching on purpose value (no dynamic record keys).

### 52. `pci_dss_cde_boundary`
- **Framework**: [PCI DSS Tokenization Guidelines](https://www.pcisecuritystandards.org/documents/Tokenization_Guidelines_Info_Supplement.pdf)
- **Pattern**: PAN (primary account number) access only by systems in the CDE; token access unrestricted
- **Why hard**: requires modeling CDE membership as resource.cdeMember: Bool and enforcing that access to `PAN_FIELD` requires `principal.cdeAuthorized && resource.cdeMember`; tokens have neither requirement.

### 53. `gdpr_purpose_limitation`
- **Framework**: [GDPR Art. 5.1.b](https://gdpr-info.eu/art-5-gdpr/)
- **Pattern**: data tagged with collection purpose; access context must declare purpose matching
- **Why hard**: `context.declaredPurpose` must be in `resource.allowedPurposes: Set<String>`. Cross-purpose access requires additional attestation (`context.compatibleUseApproval: Bool`).

### 54. `sox_three_role_sod`
- **Framework**: [SOX separation of duties](https://www.conductorone.com/guides/sox-access-controls-separation-of-duties-and-best-practices/) for banking: trader, settlement, audit
- **Pattern**: no single principal can perform actions from any two of {trade, settle, audit}
- **Why hard**: requires tracking principal identity across actions; context-supplied attestations of "who performed the previous step." Must encode that `context.prevStepActor != principal` for each transition.

### 55. `itar_us_persons_only`
- **Framework**: [ITAR deemed export](https://exportcontrol.lbl.gov/training/export-control-overview/) rules
- **Pattern**: controlled technical data accessible only by US persons (citizens + LPRs)
- **Why hard**: `principal.citizenshipStatus in ["US_CITIZEN", "LPR"]` — note `Set<String>` isn't right here (it's membership in a literal set). Must use `principal.citizenshipStatus == "US_CITIZEN" || principal.citizenshipStatus == "LPR"`. Also: EAR country-of-destination check via context.

### 56. `ccpa_do_not_sell`
- **Framework**: CCPA opt-out of sale
- **Pattern**: user's `optedOut: Bool` attribute controls all "sale" actions on their data
- **Why hard**: "sale" is a category of actions; must enforce across multiple actions via action group. Also distinguish "sale" from "service provider sharing" (out of scope for opt-out).

### 57. `ferpa_age_18_transition`
- **Framework**: [FERPA rights transfer at 18](https://epic.org/family-educational-rights-and-privacy-act-ferpa/)
- **Pattern**: parent has access to student records BEFORE student's 18th birthday, NOT after; student has access ON OR AFTER 18th birthday
- **Why hard**: datetime comparison between `context.now` and `student.dob.offset(duration("6574d"))` with strict vs non-strict boundary. Parent and student paths must be disjoint at the boundary day.

### 58. `coppa_under_13`
- **Framework**: [COPPA 16 CFR Part 312](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-312)
- **Pattern**: for users under 13, certain data collections require parental consent attestation
- **Why hard**: age computed from DOB; under-13 triggers additional consent requirement; consent itself is an optional context attribute that must be has-guarded AND verified.

### 59. `aml_kyc_tiered`
- **Framework**: [AML risk-based due diligence](https://www.neotas.com/risk-based-approach-to-aml-for-customer-due-diligence-in-kyc-aml-operations/)
- **Pattern**: low-risk → Simplified DD; medium → Standard DD; high → Enhanced DD. Action permitted only if customer's DD tier meets action's requirement.
- **Why hard**: numeric risk score (0-100) with three tier boundaries; EDD requires additional attestations (UBO verified, adverse media clean).

### 60. `gdpr_dpia_required`
- **Framework**: GDPR Art. 35 DPIA requirement
- **Pattern**: processing of "high risk" data types requires valid DPIA on file
- **Why hard**: resource.riskLevel determines DPIA requirement; DPIA validity is a datetime window; processing action blocked without valid DPIA attestation.

---

## Batch 7: Hard Semantics (scenarios 61–70)

### 61. `purpose_bound_field_access`
- **Feature**: data-minimization via purpose-specific field masks
- **Pattern**: `resource.purposeFieldMap: { treatment: Set<String>, billing: Set<String> }`; access to field X requires declared purpose P and X in purposeFieldMap[P]
- **Why hard**: dynamic record key lookup (Cedar doesn't have this natively). Must branch on purpose value explicitly: `if context.purpose == "treatment" then resource.purposeFieldMap.treatment.contains(field) else ...`.

### 62. `consent_version_validity`
- **Pattern**: user's consent has `consentedVersion: Long`; data-use permitted only when `consentedVersion >= resource.requiredConsentVersion`
- **Why hard**: version drift scenario — older consent doesn't cover newer data uses. Integer comparison simple, but interaction with expiry and withdrawal adds complexity.

### 63. `atomic_multi_step_workflow`
- **Pattern**: step 2 only permitted after step 1 recorded (context.previousStepCompleted == true); step 3 after step 2
- **Why hard**: Cedar is stateless. Must encode sequence via context attestations from the host app. Planner must specify which attestations are required at each step.

### 64. `transactional_consistency_snapshot`
- **Pattern**: read during transaction must see snapshot-consistent view (context.txnId tagged with snapshot timestamp)
- **Why hard**: snapshot correctness requires `context.snapshotTime <= resource.lastModified.offset(staleness_limit)`. Also: `transactionId` must be in `resource.committedTxns: Set<TxnId>` or equivalent.

### 65. `quorum_attestation`
- **Pattern**: action permitted when `context.attestations: Set<Attestation>` has ≥3 distinct trusted attesters
- **Why hard**: distinct-count on sets is hard in Cedar — no `.distinct()`. Must use `.containsAll(threeKnownAttesters)` across multiple permits, one per possible quorum.

### 66. `causal_predecessor_chain`
- **Pattern**: action B requires action A to have been previously permitted (encoded as `context.predecessorAuthorized: Attestation`)
- **Why hard**: attestation must have correct signer, correct action type, correct timestamp ordering.

### 67. `stale_cache_invalidation`
- **Pattern**: cached authorization valid only within `staleness_window`; otherwise re-authenticate
- **Why hard**: `context.authCacheTimestamp` must satisfy `context.now.durationSince(context.authCacheTimestamp) < duration("5m")`.

### 68. `inverted_default_permit`
- **Pattern**: unusual — default permit with explicit deny-list
- **Why hard**: goes against Cedar's natural deny-by-default. Must encode as broad permit with narrowly-scoped forbid; planner prompt will default to deny-by-default model.

### 69. `compound_attestation_multi_signer`
- **Pattern**: 3 independent attestations each required, from different signers, each with its own validity window
- **Why hard**: 3 × (has-guard + signer check + datetime window) = 9 conjoined clauses, with no single point of failure for the has-guards.

### 70. `nonce_replay_prevention`
- **Pattern**: context.nonce must be present and must be in resource.validNonces; after use, should be removed (host app concern)
- **Why hard**: distinguishes "nonce missing" (deny) from "nonce present but invalid" (deny) from "nonce present and valid" (permit). Requires careful has-guarding order.

---

## Batch 8: Specification-Level Traps (scenarios 71–80)

These stress the planner (Phase 1) more than the synthesizer.

### 71. `ambiguous_spec_most_restrictive`
- **Pattern**: spec says "admins can usually access, except under special circumstances" — ambiguity about "usually" and "special"
- **Why hard**: planner must commit to an interpretation. Most-restrictive reading is the safe choice but may over-deny.

### 72. `contradicting_requirements_literal`
- **Pattern**: spec literally contains two requirements that conflict (e.g., "X must be denied" AND "owner can always access X")
- **Why hard**: planner must identify the contradiction and produce bounds that stress §8.8 floor-consistency. Test whether planner signals the contradiction or silently picks one.

### 73. `missing_edge_case_empty_set`
- **Pattern**: spec doesn't specify what happens when resource.tags is empty
- **Why hard**: planner must pick safe default (deny on empty set). Easy to accidentally permit when `set.containsAny(empty)` returns false.

### 74. `implicit_deny_by_default`
- **Pattern**: spec assumes deny-by-default convention without stating it
- **Why hard**: tests whether planner correctly infers absence of explicit rule means deny.

### 75. `partial_spec_pattern_extrapolation`
- **Pattern**: spec describes "how manager permissions work" but not "how director permissions work"
- **Why hard**: planner must extrapolate from pattern. Risk: over-generalization grants director unintended powers.

### 76. `counterintuitive_admin_no_edit`
- **Pattern**: unusual requirement: "admin can VIEW everything but NOT edit anything"
- **Why hard**: LLMs' RBAC priors assume admin has all permissions. Planner and synthesizer both must resist the prior.

### 77. `priority_ordered_requirements`
- **Pattern**: spec states: "R1 overrides R2 overrides R3 when they conflict"
- **Why hard**: Cedar has no rule priority. Must simulate via explicit condition guards: R2 only applies when `!R1.condition`, R3 only when `!R1.condition && !R2.condition`.

### 78. `tacit_domain_convention`
- **Pattern**: spec uses phrase "standard RBAC" expecting the reader to know the convention
- **Why hard**: planner must infer "standard" (deny-by-default, transitive inheritance, permit via role-grant). Tests whether planner prompt instructs to ask rather than assume.

### 79. `redundant_spec_single_rule`
- **Pattern**: spec states same rule 3 times in different words
- **Why hard**: planner must encode ONCE, not three times. Duplicated bounds slow convergence.

### 80. `hypothetical_exception_unspecified`
- **Pattern**: spec says "normally access is granted, exceptions are rare"
- **Why hard**: planner must either ask for exception list OR encode "no exceptions" as a default. Tests if planner resists the temptation to invent exceptions.

---

## Batch 9: Adversarial Cedar Features (scenarios 81–90)

### 81. `like_with_escape_chars`
- **Feature**: `like` operator with literal `*` escaped as `\*`
- **Pattern**: email ACL matching `"admin@*.example.com"` and `"*-auto@system"`
- **Why hard**: LLMs default to regex-style escapes (`\\*` vs `\*`). Cedar uses `\*` for literal asterisk.

### 82. `like_anchored_edge_cases`
- **Feature**: `like` is anchored — `"user*"` matches "user" AND "userbob" but not "xuser"
- **Pattern**: username prefix matching with edge cases
- **Why hard**: LLMs often assume `.contains()` semantics; `like "user*"` doesn't match "xuserbob".

### 83. `decimal_boundary_overflow`
- **Feature**: decimal near the range boundary (-922337203685477.5808 to 922337203685477.5807)
- **Pattern**: large financial transaction amounts that could overflow at extremes
- **Why hard**: decimal construction at runtime can error on overflow. Validator can't catch this. Planner must ensure declared bounds don't exceed type limits.

### 84. `ipaddr_subnet_contains_vs_equals`
- **Feature**: `ip("10.0.0.1").isInRange(ip("10.0.0.0/8"))` vs `ip("10.0.0.1") == ip("10.0.0.0/8")`
- **Pattern**: confuse CIDR-as-address with CIDR-as-range
- **Why hard**: LLMs may confuse `isInRange` (containment) with `==` (equality). CIDR literal as address is actually invalid Cedar use.

### 85. `empty_set_vacuous_truth`
- **Feature**: `[].containsAll(anything)` returns `true` (vacuous truth)
- **Pattern**: policy "user must have all required training" where empty required set means "no requirements"
- **Why hard**: intuitive reading says "no training = deny" but Cedar says "no requirements = permit". Planner must explicitly handle empty-set edge case.

### 86. `reserved_keyword_in_attr_name`
- **Feature**: attribute name is a Cedar reserved word: `like`, `in`, `has`, `if`, `then`, `else`, `true`, `false`
- **Pattern**: schema has attribute `principal.in` (a boolean "is user currently in the office?")
- **Why hard**: Cedar rejects reserved-word attribute names. LLMs produce these thinking they're general identifiers.

### 87. `cedar_namespace_collision`
- **Feature**: `__cedar` namespace is reserved
- **Pattern**: schema tries to use `__cedar::Internal::State`
- **Why hard**: Cedar rejects but the error message is cryptic. Planner must know this reservation.

### 88. `homogeneous_set_type_mismatch`
- **Feature**: Cedar validator requires set literal elements to have same type
- **Pattern**: policy tries `[principal, resource.owner]` (same entity type OK) vs `[principal, "admin_user"]` (mixed: entity + string — invalid)
- **Why hard**: LLMs mix types in set literals from JSON/JavaScript priors.

### 89. `action_without_resource_applies_to`
- **Feature**: action that applies to no resource type — `action Logout appliesTo { principal: [User], resource: [] }`  
- **Pattern**: session-level action with no specific resource
- **Why hard**: empty resource `appliesTo` list; policies referencing this action cannot use resource attributes.

### 90. `action_in_two_groups_different_semantics`
- **Feature**: `action Read in [ReadOnly, AuditLogged]` — Read is in two groups with different implications
- **Pattern**: "read-only" group permits broad access, "audit-logged" group forces extra logging
- **Why hard**: single action with two group memberships; policies must account for both without conflict.

---

## Batch 10: Meta / Adversarial (scenarios 91–100)

These test the harness's robustness, not just Haiku's generation.

### 91. `adversarial_oscillation_bait`
- **Pattern**: constructed so naive fixes to ceiling A break floor B, and naive fixes to floor B break ceiling A — maximum oscillation potential
- **Why hard**: stresses §8.2 hash oscillation detection + §8.8 bound consistency simultaneously.

### 92. `plateau_landscape_many_equal`
- **Pattern**: many candidate policies with identical failure count but different failure identities
- **Why hard**: no local gradient for the LLM to follow; must reason globally about which direction to move.

### 93. `deceptive_progress_signal`
- **Pattern**: a change that looks like progress (one fewer violation) but is actually a regression (removes a correct permit and adds a different correct-looking one)
- **Why hard**: §8.2's set-based detector counts violations, not semantic progress. LLM may commit to the wrong direction.

### 94. `red_herring_attributes`
- **Pattern**: schema has 10 attributes, only 3 relevant to the spec. Other 7 are red herrings.
- **Why hard**: LLMs over-reference irrelevant attributes, producing polynomial blow-up in candidate size without improving correctness.

### 95. `hidden_simple_gotcha`
- **Pattern**: looks like trivial RBAC but has one subtle invariant (e.g., ownership transfer changes the effective permission model)
- **Why hard**: LLMs apply standard RBAC solution without noticing the invariant. Only the counterexample reveals it.

### 96. `specification_ambiguity_needs_counterexample`
- **Pattern**: NL spec has 2 possible interpretations; disambiguation requires seeing a specific counterexample from the verifier
- **Why hard**: tests whether the signal layer surfaces enough to clarify. The planner should produce bounds that distinguish interpretations.

### 97. `oop_prior_trap`
- **Pattern**: scenario involves entity types named like Java classes (`Account`, `User`, `Permission`) — LLMs may try to call methods, use `null`, etc.
- **Why hard**: tests whether §8.11-style syntax detectors fire on OOP idioms (`.method()` on non-extension types, `null`, `== null`).

### 98. `five_equivalent_formulations`
- **Pattern**: the correct policy can be expressed 5 semantically-equivalent ways; only 2 pass symcc type-checking cleanly
- **Why hard**: LLM may converge on a semantically-correct but type-unclean form. Must distinguish.

### 99. `decoy_trivial_properties`
- **Pattern**: verification plan includes 5 trivial properties (always PASS) mixed with 3 genuinely hard ones
- **Why hard**: ensures the LLM focuses on the hard properties. Trivial properties shouldn't cause §8.2 hash-oscillation if they constantly PASS.

### 100. `regression_battery_all_traps`
- **Pattern**: single scenario crafted to trigger §8.1, §8.4, §8.6, §8.8, §8.9, §8.11 simultaneously if any one regresses
- **Why hard**: regression test for the entire signal layer. If we ever refactor the harness, this scenario should still PASS; if any contribution breaks, this fails.

---

## Prioritization for implementation

If we can only build 30 of these, prioritize in this order:

**Top 10 (highest research value, lowest effort):**
1. #9 `entity_tags_with_hastag` — exercises a Cedar feature we haven't touched
2. #1 `decimal_currency_comparison` — method-syntax for comparison, §8.11-class mismatch
3. #2 `ipaddr_corporate_network` — ipaddr extension, first use
4. #4 `if_then_else_decision_tree` — Cedar's expression-level conditional
5. #21 `five_way_role_intersection` — §8.6 stressed beyond 2-way
6. #14 `recurring_maintenance_window` — datetime modulo via duration math
7. #51 `hipaa_minimum_necessary` — grounded compliance pattern
8. #41 `mega_scale_500_checks` — scale ceiling test
9. #91 `adversarial_oscillation_bait` — tests §8.2 limits
10. #100 `regression_battery_all_traps` — regression safety net

**Next 10 (stress specific harness components):**
11. #15 `age_verification_leap_years`
12. #22 `anti_transitive_delegation`
13. #31 `four_level_unless_chain`
14. #39 `n_of_m_signature_withdrawal`
15. #54 `sox_three_role_sod`
16. #55 `itar_us_persons_only`
17. #81 `like_with_escape_chars`
18. #86 `reserved_keyword_in_attr_name`
19. #93 `deceptive_progress_signal`
20. #97 `oop_prior_trap`

**Next 10 (compliance and realism):**
21. #57 `ferpa_age_18_transition`
22. #52 `pci_dss_cde_boundary`
23. #53 `gdpr_purpose_limitation`
24. #58 `coppa_under_13`
25. #59 `aml_kyc_tiered`
26. #60 `gdpr_dpia_required`
27. #61 `purpose_bound_field_access`
28. #69 `compound_attestation_multi_signer`
29. #67 `stale_cache_invalidation`
30. #65 `quorum_attestation`

## Expected outcomes

If we implement the top 30:
- **5-10 are likely to converge in 1-3 iterations** (standard patterns)
- **10-15 will converge in 5-12 iterations** (genuinely hard but the signal layer handles them)
- **5-10 will FAIL at 20/20 iterations**, revealing:
  - New syntax detectors needed (e.g., decimal method syntax → §8.12)
  - New structural trap detectors (e.g., 5-way role intersection → §8.13)
  - Scale limitations (mega_scale_500 may need verification batching)
  - New planner rules (e.g., purpose-to-field dynamic lookup guidance)

This would add 3-5 new novel contributions to the harness, giving us
**15+ documented signal layer contributions** and strengthening the
paper's claim that the signal-layer approach is a general framework
with discoverable components.

## Next steps

1. Pick the top 10 and build them this session (aim for 1-2 hours per scenario)
2. Run all 10 through the harness
3. Analyze failures: for each FAIL, determine if the scenario is unfair
   or if the harness needs a new contribution
4. Add new §8.x contributions as needed
5. Iterate to 30 total
6. Update `harness_fix_log.md`, `cedarbench/README.md`, realworld README
7. Rerun the full benchmark to confirm no regressions on the original 121

---

*Document generated after comprehensive research across Cedar
documentation, Cedar RFCs, compliance framework specifications, and
production authorization patterns. All 100 scenarios are faithful to
Cedar's actual semantics and grounded in real regulatory or technical
requirements.*
