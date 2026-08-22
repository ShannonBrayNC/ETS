# Microsoft P0 connector identity boundary v1

Parent: #543

The hosted Microsoft connector family uses separate user-assigned managed identities for distinct
source authorities. Identity selection is server-owned. Connector configuration cannot substitute a
client ID, token audience, credential locator, tenant, or source scope.

## Identity profiles

| Profile | Credential reference | Token audience | Allowed application permissions |
| --- | --- | --- | --- |
| Approved SharePoint-backed drive | `azure-mi://microsoft-graph` | `https://graph.microsoft.com/.default` | Existing `Sites.Selected` plus the existing site-specific read grant |
| Entra directory delta | `azure-mi://microsoft-graph/directory` | `https://graph.microsoft.com/.default` | `User.Read.All`, `Group.Read.All` |
| Purview audit activity | `azure-mi://office-365-management/purview` | `https://manage.office.com/.default` | `ActivityFeed.Read` |

The directory identity must not receive `Directory.Read.All`, any Graph write permission, Azure
RBAC, or SharePoint site permission. Although Microsoft currently lists a group-nesting write
permission as the nominal least-privileged permission for `groups/delta`, ETS selects the
non-writing `Group.Read.All` application role because the P0 collector requires group metadata and
must never mutate directory state.

The Purview identity must not receive `ActivityFeed.ReadDlp`, `ServiceHealth.Read`, Microsoft Graph
permissions, Azure RBAC, or SharePoint site permission. The P0 feed is restricted to approved audit
content types. DLP content is deferred.

## OneDrive scope

RC1 qualifies metadata/delta for the approved SharePoint/OneDrive for Business site drive already
bounded by `Sites.Selected`. It does not grant `Files.Read.All` and does not claim tenant-wide access
to users' personal OneDrive drives.

## Runtime requirements

- Every opaque credential reference maps to exactly one configured client ID and one HTTPS
  `/.default` audience.
- Unconfigured references fail before managed-identity token acquisition.
- A connector cannot provide or override its client ID or audience.
- Token material exists only in a short-lived zeroizable credential lease.
- Identity initialization and token failures expose bounded classifications without provider
  exception text or token material.
- Shutdown closes each initialized managed-identity transport exactly once.

## Operator bootstrap

Provisioning is preview-first and resolves service principals and app roles by immutable app ID and
role value. Apply mode must fail on missing, disabled, ambiguous, duplicate, or broader assignments.
It must reread every assignment after mutation and retain only tenant-domain verification,
managed-identity identifiers, exact role IDs/values, outcomes, and non-retention flags.

Admin-consent credentials are operator bootstrap material only. They are not stored by ETS and are
not evidence that the runtime identity can acquire or use its source token.

## Qualification

Live qualification must independently prove:

1. each UAMI acquires only its configured audience;
2. a cross-profile client-ID or audience substitution fails closed;
3. the directory identity can execute bounded users/groups delta and cannot write;
4. the Purview identity can list approved audit subscriptions/content and cannot request DLP; and
5. retained evidence contains no reusable credentials, source payload bodies, user/group names, or
   customer identifiers.

The identity boundary does not start the soak clock and does not authorize public hostname
activation.

## Microsoft references

- [User delta permissions](https://learn.microsoft.com/graph/api/user-delta?view=graph-rest-1.0)
- [Group delta permissions](https://learn.microsoft.com/graph/api/group-delta?view=graph-rest-1.0)
- [DriveItem delta permissions](https://learn.microsoft.com/graph/api/driveitem-delta?view=graph-rest-1.0)
- [Office 365 Management Activity API](https://learn.microsoft.com/office/office-365-management-api/office-365-management-activity-api-reference)
