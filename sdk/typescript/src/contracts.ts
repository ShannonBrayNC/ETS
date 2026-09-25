export const ETS_APPLICATION_SDK_CONTRACT = "ets.application.sdk.v1" as const;
export const ETS_API_VERSION = "v1" as const;

export interface ServiceVersion {
  name: string;
  version: string;
  api_version: string;
}

export interface ServiceHealth {
  status: string;
  version: string;
}

export interface TreeHead {
  tree_size: number;
  root_hash: string;
  created_at_utc: string;
  log_id: string;
  signature_alg: string | null;
  signature: string | null;
  public_key_id: string | null;
}

export interface EventAppendWireResponse {
  event_id: string;
  log_index: number;
  event_hash: string;
  tree_head: TreeHead;
  inclusion_proof_url: string;
}

export interface EventCommitReceipt extends EventAppendWireResponse {
  schema_version: "ets.sdk.event_commit_receipt.v1";
  commitment_state: "committed_local";
}
