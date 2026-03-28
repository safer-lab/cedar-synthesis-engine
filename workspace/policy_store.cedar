// No pre-existing policies. All access control must come from the candidate.

// --- Verified and appended ---
// === Clinical Trial Candidate Policy — Verified ===

// --- Permit: ClinicalResearcher View ---
permit (
    principal in Role::"ClinicalResearcher",
    action == Action::"View",
    resource
) when {
    resource.projectStatus == "Active" &&
    principal.clearanceLevel > 3 &&
    resource.classification != "HighlyRestricted"
};

// --- Permit: ClinicalResearcher Edit ---
permit (
    principal in Role::"ClinicalResearcher",
    action == Action::"Edit",
    resource
) when {
    resource.projectStatus == "Active" &&
    principal.clearanceLevel > 3 &&
    resource.classification != "HighlyRestricted"
};

// --- Permit: PrincipalInvestigator View ---
permit (
    principal in Role::"PrincipalInvestigator",
    action == Action::"View",
    resource
) when {
    resource.projectStatus == "Active" &&
    context.networkRiskScore < 20 &&
    context.isCompliantDevice
};

// --- Permit: PrincipalInvestigator Edit ---
permit (
    principal in Role::"PrincipalInvestigator",
    action == Action::"Edit",
    resource
) when {
    resource.projectStatus == "Active" &&
    context.networkRiskScore < 20 &&
    context.isCompliantDevice
};

// --- Forbid: Cross-Departmental Block ---
// GlobalAuditor is exempt via unless clause
forbid (
    principal,
    action,
    resource
) when {
    principal.department != resource.projectManagingDepartment
} unless {
    principal in Role::"GlobalAuditor"
};
