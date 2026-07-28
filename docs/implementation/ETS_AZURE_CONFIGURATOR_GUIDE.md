# ETS Azure Configurator

## Purpose

The ETS Azure Configurator is a PowerShell-first deployment utility that connects to a Microsoft Entra tenant and Azure subscription, validates deployment prerequisites, previews infrastructure changes, deploys a starter ETS dashboard/API footprint, and upgrades the same deployment to a production-oriented tier.

It is designed for repeatable customer onboarding rather than ad hoc portal configuration.

## Important cost boundary

The `free` tier is a **free-eligible starter configuration**, not a guarantee of a zero-dollar Azure bill. Azure Static Web Apps has a Free plan. The Functions Consumption plan includes grant-based serverless usage, but its required storage account and any usage beyond included grants may incur charges. Regional availability, subscription offers, taxes, outbound bandwidth, logs, custom domains, and future Azure pricing can also affect cost.

Before deploying for a customer:

1. Review the Azure pricing calculator and the customer's subscription offer.
2. Create a resource-group budget and cost alerts in the Azure portal or through the customer's FinOps automation.
3. Run `Plan` mode and review the Azure Resource Manager what-if output.
4. Deploy only after the customer accepts the expected footprint and cost boundary.

## Architecture

```text
Administrator workstation
        |
        | Azure CLI interactive/device-code authentication
        v
ETS Azure Configurator PowerShell
        |
        +-- discovers tenant and subscriptions
        +-- selects active subscription
        +-- registers required providers
        +-- validates or runs ARM what-if
        +-- deploys subscription-scope Bicep
        v
Customer Azure subscription
        |
        +-- ETS resource group
        +-- Azure Static Web Apps dashboard
        +-- optional Linux Azure Functions Consumption API
        +-- StorageV2 account required by Functions
```

The utility does not collect or persist administrator passwords, refresh tokens, service-principal secrets, or private keys. Authentication is delegated to Azure CLI.

## Files

- `scripts/azure/Invoke-EtsAzureConfigurator.ps1` — operator command.
- `infra/azure/configurator/main.bicep` — subscription-scope orchestration.
- `infra/azure/configurator/modules/application.bicep` — dashboard, API, plan, identity, and storage resources.
- `tests/unit/test_azure_configurator_assets.py` — static qualification tests.

## Prerequisites

Install:

- PowerShell 7 or later;
- Azure CLI;
- an account with access to the target tenant and subscription;
- permissions to create resource groups, deployments, Static Web Apps, Functions plans/apps, and Storage accounts;
- permission to register Azure resource providers when they are not already registered.

For production automation, use workload identity federation or a managed deployment identity rather than an interactive user. The current operator utility intentionally starts with interactive or device-code authentication for controlled onboarding.

## Modes

| Mode | Action |
| --- | --- |
| `Connect` | Authenticates, selects a subscription, and writes a connection result. |
| `Validate` | Runs Azure Resource Manager template validation without deployment. |
| `Plan` | Runs Azure Resource Manager what-if and writes the proposed changes. |
| `Deploy` | Deploys the selected `free` or `standard` tier. |
| `Upgrade` | Reapplies the same deployment using the `standard` tier. |

`Plan` is the default mode.

## Step-by-step deployment

### 1. Review the script

```powershell
Get-Help ./scripts/azure/Invoke-EtsAzureConfigurator.ps1 -Detailed
```

### 2. Connect to a tenant

Browser-based login:

```powershell
pwsh ./scripts/azure/Invoke-EtsAzureConfigurator.ps1 `
  -Mode Connect `
  -TenantId '<tenant-guid>'
```

Device-code login:

```powershell
pwsh ./scripts/azure/Invoke-EtsAzureConfigurator.ps1 `
  -Mode Connect `
  -TenantId '<tenant-guid>' `
  -UseDeviceCode
```

When more than one subscription is available, the tool presents a numbered selection unless `-SubscriptionId` is supplied.

### 3. Validate the template

```powershell
pwsh ./scripts/azure/Invoke-EtsAzureConfigurator.ps1 `
  -Mode Validate `
  -TenantId '<tenant-guid>' `
  -SubscriptionId '<subscription-guid>' `
  -DeploymentName 'ets-pilot' `
  -Location 'eastus2'
```

### 4. Preview changes

```powershell
pwsh ./scripts/azure/Invoke-EtsAzureConfigurator.ps1 `
  -Mode Plan `
  -Tier free `
  -TenantId '<tenant-guid>' `
  -SubscriptionId '<subscription-guid>' `
  -DeploymentName 'ets-pilot' `
  -Location 'eastus2'
```

The utility runs a subscription-scope Azure Resource Manager what-if operation. Review all creates, modifications, unsupported evaluations, and deletes before deployment.

### 5. Deploy the starter tier

```powershell
pwsh ./scripts/azure/Invoke-EtsAzureConfigurator.ps1 `
  -Mode Deploy `
  -Tier free `
  -TenantId '<tenant-guid>' `
  -SubscriptionId '<subscription-guid>' `
  -DeploymentName 'ets-pilot' `
  -Location 'eastus2' `
  -Confirm
```

Use `-SkipApi` to deploy only the dashboard shell:

```powershell
pwsh ./scripts/azure/Invoke-EtsAzureConfigurator.ps1 `
  -Mode Deploy `
  -Tier free `
  -SkipApi `
  -TenantId '<tenant-guid>' `
  -SubscriptionId '<subscription-guid>' `
  -DeploymentName 'ets-dashboard'
```

### 6. Inspect the result artifact

By default, the command writes:

```text
artifacts/azure-configurator-result.json
```

The artifact records the tenant, subscription, deployment name, location, selected tier, deployment outputs, and generated upgrade command. It must not contain credentials.

### 7. Deploy application code

The infrastructure deployment creates the hosting boundary but does not publish the ETS application package.

Follow-on release automation must:

1. build the ETS dashboard;
2. deploy static assets to the Static Web App;
3. package and deploy the Azure Functions API when enabled;
4. configure Entra application authentication;
5. configure ETS tenant/workspace settings;
6. run health, authorization, and evidence-path smoke tests.

### 8. Upgrade to Standard

Run a plan first:

```powershell
pwsh ./scripts/azure/Invoke-EtsAzureConfigurator.ps1 `
  -Mode Plan `
  -Tier standard `
  -TenantId '<tenant-guid>' `
  -SubscriptionId '<subscription-guid>' `
  -DeploymentName 'ets-pilot' `
  -Location 'eastus2'
```

Then upgrade:

```powershell
pwsh ./scripts/azure/Invoke-EtsAzureConfigurator.ps1 `
  -Mode Upgrade `
  -Tier standard `
  -TenantId '<tenant-guid>' `
  -SubscriptionId '<subscription-guid>' `
  -DeploymentName 'ets-pilot' `
  -Location 'eastus2' `
  -Confirm
```

The upgrade reuses the deterministic deployment name and resource names. This first increment upgrades Azure Static Web Apps from Free to Standard while preserving the Consumption Functions architecture. Dedicated API compute, private endpoints, zone redundancy, premium messaging, production databases, and customer-managed keys belong to subsequent production modules.

## Security controls

The starter module enforces:

- HTTPS-only Function App access;
- TLS 1.2 minimums;
- disabled FTP deployment;
- disabled public blob access;
- system-assigned managed identity on the Function App;
- deterministic resource tags identifying the ETS deployment and tier;
- what-if support before changes;
- PowerShell `ShouldProcess` support;
- no secrets in command parameters or result artifacts.

The Function host storage connection currently uses an ARM-generated storage key because Azure Functions requires host storage. Production hardening should replace this with identity-based host storage where supported by the selected Functions configuration and operational requirements.

## Validation

Run the repository unit test:

```bash
python -m pytest tests/unit/test_azure_configurator_assets.py
```

Validate Bicep through Azure CLI:

```powershell
pwsh ./scripts/azure/Invoke-EtsAzureConfigurator.ps1 -Mode Validate -TenantId '<tenant-guid>' -SubscriptionId '<subscription-guid>'
```

Run an infrastructure preview:

```powershell
pwsh ./scripts/azure/Invoke-EtsAzureConfigurator.ps1 -Mode Plan -TenantId '<tenant-guid>' -SubscriptionId '<subscription-guid>'
```

## Production backlog

Before presenting the Standard tier as fully production-qualified, add:

- Entra app registration and role automation;
- federated CI/CD deployment identity;
- API Management or Front Door/WAF module;
- identity-based Functions host storage;
- Key Vault and certificate lifecycle;
- connector Event Hubs/Service Bus modules;
- database and evidence-store modules;
- private networking and Private Link;
- budget and action-group parameters;
- regional deployment stamps;
- backup, restore, rollback, and disaster-recovery tests;
- post-deployment health and tenant-isolation tests;
- customer offboarding and resource-lock strategy.
