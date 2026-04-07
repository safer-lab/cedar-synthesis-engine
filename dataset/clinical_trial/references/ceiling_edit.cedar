// Ceiling: maximum permissive boundary for Edit.
// Same constraints as View (per spec, View and Edit share the same rules).

permit (
    principal,
    action == Action::"Edit",
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
