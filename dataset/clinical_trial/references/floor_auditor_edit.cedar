// Floor for Edit auditor loophole (same scenarios as View).

// CR auditor, cross-department
permit (
    principal,
    action == Action::"Edit",
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
    action == Action::"Edit",
    resource
) when {
    principal in Role::"GlobalAuditor" &&
    principal in Role::"PrincipalInvestigator" &&
    context.networkRiskScore < 20 &&
    context.isCompliantDevice &&
    resource.projectStatus == "Active" &&
    principal.department != resource.projectManagingDepartment
};
