# M365 Gate 2 Stage 1 Windows regression

## Observed failure

The first authorized Stage 1 operator execution on PowerShell 7 for Windows failed before any Entra application mutation.

Two Windows/PowerShell behaviors were exposed:

1. the Azure CLI `az.cmd` wrapper interpreted the ampersand joining Graph `$filter` and `$select` query parameters as a command separator;
2. an empty or single PowerShell function result was not forced into an array before `.Count` was evaluated under strict mode.

The failed execution therefore did **not** create the destination multitenant application.

## Correction

The Stage 1 apply script now:

- keeps Graph GET URLs to one query parameter at a time;
- first resolves exact application candidates, then reads each candidate's full guarded shape separately;
- checks Azure CLI native exit codes before parsing JSON;
- forces initial and post-create application results into arrays before using `.Count`;
- checks the application-create native exit code before post-create verification;
- preserves all existing fail-closed shape checks and the one-mutation boundary.

## Scope unchanged

The authorized Stage 1 mutation remains limited to creating one destination Entra application named `ETS Gateway SharePoint Cross-Tenant` with `AzureADMultipleOrgs`. No FIC, resource-tenant service principal, Graph permission, SharePoint permission, Azure RBAC, replica, DNS, source fence, writer, or cutover change is included.
