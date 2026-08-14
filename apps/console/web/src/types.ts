export type VerificationState =
  | "verified"
  | "unverified"
  | "verification_failed"
  | "degraded"
  | "unknown";

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type AuthRole =
  | "viewer"
  | "evidence_producer"
  | "operator"
  | "auditor"
  | "administrator";

export type AuthCapability =
  | "evidence.read"
  | "evidence.create"
  | "evidence.verify"
  | "evidence.export"
  | "connector.read"
  | "connector.manage"
  | "audit.read"
  | "admin.read"
  | "admin.manage";

export interface GatewayAuthorizationContext {
  schema_version: "ets.gateway.authorization_context.v2";
  mode: string;
  subject: string;
  tenant_id: string;
  workspace_id: string;
  roles: AuthRole[];
  capabilities: AuthCapability[];
  authorization_profile: "local_nonproduction" | "production";
}

export interface TenantScope {
  tenantId: string;
  workspaceId: string;
}

export interface ArtifactReceipt {
  artifact_id: string;
  artifact_hash: string;
  event_id: string;
  block_number: number;
  timestamp_utc: string;
  proof_url: string;
}

export interface ArtifactRecord {
  artifact_id: string;
  artifact_hash: string;
  reference_uri: string;
  content_type: string;
  byte_size: number;
  metadata: Record<string, unknown>;
  ingestion_timestamp_utc: string;
  event_id: string;
  log_index: number;
}

export interface TreeHead {
  log_id?: string;
  tree_size?: number;
  root_hash?: string;
  timestamp_utc?: string;
  signature?: string | null;
  key_id?: string | null;
  [key: string]: unknown;
}

export interface ProofBundle {
  [key: string]: unknown;
}

export interface HealthSnapshot {
  health: "ok" | "degraded" | "unknown";
  ready: boolean;
  version: string;
}

export interface ConsoleEvidenceItem {
  artifact: ArtifactRecord;
  verificationState: VerificationState;
}

export type ConnectorDeliveryMode = "push" | "poll";
export type ConnectorImplementationClass = "native" | "enterprise_api" | "generic" | "third_party";
export type ConnectorHealthState = "healthy" | "degraded" | "failed" | "unknown";
export type ConnectorOperationCode =
  | "ok"
  | "unsupported"
  | "invalid_config"
  | "authentication_failed"
  | "authorization_failed"
  | "throttled"
  | "retryable_error"
  | "terminal_error"
  | "gap_detected"
  | "unknown_observation"
  | "incompatible_version";
export type ConnectorObservationState =
  | "healthy_observation"
  | "degraded_observation"
  | "collection_gap"
  | "unknown_observation";

export interface ConnectorCapabilities {
  delivery_modes: ConnectorDeliveryMode[];
  authentication_methods: string[];
  discovery: boolean;
  checkpointing: boolean;
  reconciliation: boolean;
  normalization: boolean;
  health: boolean;
}

export interface ConnectorDefinition {
  schema_version: "ets.connector.definition.v1";
  connector_id: string;
  display_name: string;
  description: string;
  implementation_class: ConnectorImplementationClass;
  source_classes: string[];
  adapter_version: string;
  sdk_contract_version: "ets.connector.sdk.v1";
  capture_envelope_versions: string[];
  gateway_host_versions: string[];
  capabilities: ConnectorCapabilities;
  configuration_schema: {
    instance_schema: "ets.connector.instance.v1";
    settings_schema_ref: string | null;
  };
}

export interface ConnectorInstance {
  schema_version: "ets.connector.instance.v1";
  instance_id: string;
  connector_id: string;
  connector_version: string;
  enabled: boolean;
  scope: {
    tenant_id: string;
    workspace_id: string;
  };
  source: {
    name: string;
    environment: string;
  };
  authentication: {
    method: string;
    credential_ref: string | null;
  };
  collection: {
    mode: ConnectorDeliveryMode;
    interval_seconds: number | null;
    batch_size: number;
  };
  checkpoint: {
    strategy: "none" | "source_cursor" | "time_window" | "source_sequence";
    durable: boolean;
  };
  policy: {
    capture_profile: string;
    normalization_profile: string;
  };
  retry: {
    max_attempts: number;
    backoff: "fixed" | "exponential";
    max_age_seconds: number;
  };
  gap_detection: {
    enabled: boolean;
  };
  settings: Record<string, JsonValue>;
}

export interface ConnectorInstanceRecord {
  schema_version: "ets.connector.instance_record.v1";
  instance: ConnectorInstance;
  revision: number;
  created_at_utc: string;
  updated_at_utc: string;
}

export interface ConnectorCheckpoint {
  schema_version: "ets.connector.checkpoint.v1";
  cursor: string | null;
  sequence: number | string | null;
  observed_through_utc: string | null;
}

export interface ConnectorRuntimeState {
  schema_version: "ets.connector.runtime.v1";
  instance_id: string;
  checkpoint: ConnectorCheckpoint | null;
  checkpoint_revision: number;
  retry_count: number;
  next_attempt_at_utc: string | null;
  last_success_at_utc: string | null;
  observation_state: ConnectorObservationState;
  gap_open: boolean;
  lease_owner: string | null;
  lease_expires_at_utc: string | null;
  updated_at_utc: string;
}

export interface ConnectorHealth {
  schema_version: "ets.connector.health.v1";
  state: ConnectorHealthState;
  code: ConnectorOperationCode;
  message: string;
  retry_after_seconds: number | null;
}

export interface ConnectorInstanceListResponse {
  items: ConnectorInstanceRecord[];
}

export interface ConnectorSettingField {
  key: string;
  label: string;
  type: "text" | "number" | "select";
  required?: boolean;
  placeholder?: string;
  min?: number;
  max?: number;
  step?: number;
  options?: string[];
  help?: string;
}
