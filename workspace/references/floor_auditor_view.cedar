// Floor: minimum that MUST be allowed for the auditor loophole.
// If the candidate denies these, the GlobalAuditor exception is broken.
//
// Scenario: A GlobalAuditor+ClinicalResearcher from a DIFFERENT department
// accesses a non-HighlyRestricted doc in an Active project.

// CR auditor, cross-department
permit (
    principal,
    action == Action::"View",
    resource
) when {
    principal in Role::"GlobalAuditor" &&
    principal in Role::"ClinicalResearcher" &&
    principal.clearanceLevel > 3 &&
    resource.classification != "HighlyRestricted" &&
    resource.projectStatus == "Active" &&
    principal.department != resource.projectManagingDepartment
};

// PI auditor, cross-department
permit (
    principal,
    action == Action::"View",
    resource
) when {
    principal in Role::"GlobalAuditor" &&
    principal in Role::"PrincipalInvestigator" &&
    context.networkRiskScore < 20 &&
    context.isCompliantDevice &&
    resource.projectStatus == "Active" &&
    principal.department != resource.projectManagingDepartment
};
