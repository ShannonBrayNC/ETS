# ETS Fleet Physical TPM A5 Qualification

Status: Implementation profile  
Date: 2026-08-21  
Parent: #511 / FLEET-A #481  
Depends on: #510 / FLEET-A4

## 1. Purpose

FLEET-A5 is the end-to-end physical Fleet enrollment/revocation qualification. It proves
that one physical Edge R1 can:

1. provision through Azure DPS using the TPM identity qualified in A4;
2. authenticate to the assigned IoT Hub while ETS authorizes the device;
3. retain connectivity when only DPS is disabled, demonstrating that DPS state alone is
   not connection revocation;
4. lose IoT Hub authentication after the Hub device identity is disabled;
5. fail a forced DPS reprovision attempt while the DPS enrollment remains disabled; and
6. remain denied by ETS independently of Azure provider state.

ETS remains authoritative for canonical device identity, tenant/workspace scope, lifecycle,
standing, and authorization. Azure DPS and IoT Hub are provider boundaries only.

## 2. Reference device client

The reference physical qualification adapter is Azure IoT Edge 1.6 LTS with the Azure IoT
Identity Service TPM provisioning path.

The device-side configuration is limited to:

```toml
auto_reprovisioning_mode = "Dynamic"

[provisioning]
source = "dps"
global_endpoint = "https://global.azure-devices-provisioning.net"
id_scope = "<DPS-ID-SCOPE>"

[provisioning.attestation]
method = "tpm"
registration_id = "<EK-DERIVED-PROVIDER-ALIAS>"
```

A second qualification-only configuration uses
`auto_reprovisioning_mode = "AlwaysOnStartup"` for the final reprovision-denial probe.

The IoT Edge runtime is a qualification adapter. It is not an ETS protocol dependency and
does not become the source of ETS identity or lifecycle semantics.

## 3. Why revocation has two provider layers

Disabling a DPS individual enrollment prevents subsequent provisioning or reprovisioning.
It does not remove an already provisioned device identity from IoT Hub.

A5 therefore has two distinct provider controls:

- **DPS disabled**: future provision/reprovision is denied.
- **IoT Hub device identity disabled**: an existing device identity cannot authenticate to
  the assigned Hub.

The A5 negative control deliberately disables DPS first while leaving the Hub identity
enabled. The physical device must still pass the cached-identity reconnect probe. This
proves why DPS disablement cannot be treated as connection revocation.

Only after that negative control passes is the IoT Hub identity disabled.

## 4. Truth sources

A5 uses four independent truth sources:

1. ETS authorization decision for the canonical `device_id`;
2. DPS individual enrollment state;
3. DPS service-side registration record and assigned IoT Hub;
4. physical R1 identity-service probes.

Azure IoT Hub `connectionState` is not used as qualification truth because provider
documentation notes that it can lag and is not intended as a production connectivity
signal. The physical device probe is used instead.

## 5. Security boundary

The R1 receives only:

- DPS global endpoint;
- DPS ID Scope;
- EK-derived provider registration alias;
- TPM provisioning method.

The R1 never receives:

- Azure management credentials;
- DPS policy keys;
- IoT Hub policy keys;
- SAS tokens;
- IoT Hub device connection strings;
- reusable shared device keys.

Operator-side Azure CLI commands use Microsoft Entra data-plane authentication with
`--auth-type login`.

The qualification scripts never request or retain device connection strings or shared
access keys.

## 6. Device preparation

After A5 `enable` emits `a5-enable-result.json`, prepare the two R1 qualification configs:

```bash
./scripts/fleet/prepare_physical_tpm_a5_device.sh \
  ./fleet-a5-device \
  <DPS-ID-SCOPE> \
  <EK-DERIVED-PROVIDER-REGISTRATION-ID>
```

This command only creates local configuration files and a public-safe manifest. It does
not modify `/etc/aziot/config.toml`.

## 7. Positive provisioning phase

The operator first validates the A4 retained-disabled handoff and enables only that
individual TPM enrollment:

```bash
python scripts/fleet/qualify_physical_tpm_a5.py enable \
  --a4-result <A4-AZURE-RESULT> \
  --output-dir <A5-OPERATOR-EVIDENCE>
```

On the R1, use the Dynamic configuration:

```bash
./scripts/fleet/run_physical_tpm_a5_probe.sh \
  authorized \
  <DEVICE-PROBE-DIR> \
  <CONFIG-DYNAMIC-TOML>
```

The probe:

- backs up an existing `/etc/aziot/config.toml` only to a root-only file on the device;
- installs the qualification TPM configuration;
- applies IoT Edge configuration;
- restarts the IoT Edge system;
- runs `aziotctl check`;
- runs `iotedge check`;
- retains raw command output only in the local private probe directory; and
- emits a public-safe result containing only exit codes and output hashes.

The operator verifies the DPS service registration and assigned IoT Hub:

```bash
python scripts/fleet/qualify_physical_tpm_a5.py verify-positive \
  --a4-result <A4-AZURE-RESULT> \
  --device-probe <AUTHORIZED-DEVICE-PROBE> \
  --output-dir <A5-OPERATOR-EVIDENCE>
```

A successful positive phase requires:

- DPS enrollment enabled;
- DPS registration status assigned;
- exact canonical ETS device ID;
- bounded assigned IoT Hub hostname;
- matching IoT Hub device identity enabled; and
- successful physical identity-service probe after restart.

## 8. ETS-authoritative revocation

Before any Azure provider revocation, the canonical Fleet lifecycle must already deny the
device. The operator supplies a retained ETS authorization decision with:

- exact canonical device ID;
- `allowed=false`; and
- reason `quarantined`, `revoked`, or `decommissioned`.

Provider state can never cause ETS to infer a lifecycle transition.

## 9. DPS-only negative control

Disable the DPS individual enrollment only:

```bash
python scripts/fleet/qualify_physical_tpm_a5.py disable-dps \
  --a4-result <A4-AZURE-RESULT> \
  --ets-decision <ETS-DENIAL-DECISION> \
  --output-dir <A5-OPERATOR-EVIDENCE>
```

Do not disable the IoT Hub identity yet.

Run the R1 reconnect probe while the Dynamic configuration remains active:

```bash
./scripts/fleet/run_physical_tpm_a5_probe.sh \
  dps-disabled-hub-enabled \
  <DEVICE-PROBE-DIR> \
  <CONFIG-DYNAMIC-TOML>
```

The identity check is expected to succeed because the existing IoT Hub device identity is
still enabled.

Retain that negative control:

```bash
python scripts/fleet/qualify_physical_tpm_a5.py verify-dps-only \
  --device-probe <DPS-ONLY-DEVICE-PROBE> \
  --output-dir <A5-OPERATOR-EVIDENCE>
```

## 10. IoT Hub revocation

After the DPS-only negative control, disable the assigned IoT Hub device identity:

```bash
python scripts/fleet/qualify_physical_tpm_a5.py disable-hub \
  --a4-result <A4-AZURE-RESULT> \
  --ets-decision <ETS-DENIAL-DECISION> \
  --positive-result <A5-POSITIVE-RESULT> \
  --output-dir <A5-OPERATOR-EVIDENCE>
```

The operator command verifies the exact assigned Hub and canonical device identity before
changing status.

Run the reconnect denial probe:

```bash
./scripts/fleet/run_physical_tpm_a5_probe.sh \
  hub-disabled-reconnect \
  <DEVICE-PROBE-DIR> \
  <CONFIG-DYNAMIC-TOML>
```

The physical identity check must fail.

## 11. Forced reprovision denial

Use the qualification-only AlwaysOnStartup configuration:

```bash
./scripts/fleet/run_physical_tpm_a5_probe.sh \
  dps-disabled-reprovision \
  <DEVICE-PROBE-DIR> \
  <CONFIG-ALWAYS-ON-STARTUP-TOML>
```

Because the DPS enrollment remains disabled, the identity check must fail after the
forced reprovision attempt.

## 12. Final verification

Finalize A5 only when all provider and device evidence agrees:

```bash
python scripts/fleet/qualify_physical_tpm_a5.py verify-final \
  --a4-result <A4-AZURE-RESULT> \
  --ets-decision <ETS-DENIAL-DECISION> \
  --positive-result <A5-POSITIVE-RESULT> \
  --reconnect-probe <HUB-DISABLED-DEVICE-PROBE> \
  --reprovision-probe <DPS-REPROVISION-DEVICE-PROBE> \
  --output-dir <A5-OPERATOR-EVIDENCE>
```

The final result requires:

- ETS authorization denied;
- DPS enrollment disabled;
- IoT Hub identity disabled;
- physical reconnect denied; and
- forced reprovision denied.

## 13. Evidence retention

Public-safe evidence may contain:

- canonical ETS device/enrollment identifiers;
- provider registration alias;
- DPS and IoT Hub names/status;
- assigned IoT Hub hostname;
- tool versions;
- exit codes;
- hashes of private local probe output;
- ETS authorization reason code;
- timestamps.

Do not retain in public evidence:

- TPM private material;
- raw TPM-derived device credentials;
- Azure bearer tokens;
- DPS or IoT Hub policy keys;
- SAS tokens;
- connection strings;
- customer payloads.

## 14. Recovery boundary

A5 intentionally leaves the qualification device revoked/disabled. Recovery is not part
of A5.

A future recovery operation must independently revalidate ETS standing before any DPS or
IoT Hub provider identity is re-enabled. An out-of-band Azure re-enable must never cause
ETS authorization to become allowed.
