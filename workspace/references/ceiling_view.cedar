// Ceiling: maximum permissive boundary for View.
// Encodes: Active project + (dept match OR GlobalAuditor) +
//          (ClinicalResearcher path OR PrincipalInvestigator path)

permit (
    principal,
    action == Action::"View",
    resource
) when {
    resource.projectStatus == "Active" &&
    (principal.department == resource.projectManagingDepartment ||
     principal in Role::"GlobalAuditor") &&
    (
        (principal in Role::"ClinicalResearcher" &&
         principal.clearanceLevel > 3 &&
         resource.classification != "HighlyRestricted")
        ||
        (principal in Role::"PrincipalInvestigator" &&
         context.networkRiskScore < 20 &&
         context.isCompliantDevice)
    )
};
