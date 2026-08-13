export type VerificationState =
  | "verified"
  | "unverified"
  | "verification_failed"
  | "degraded"
  | "unknown";

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
