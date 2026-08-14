# ETS Gateway File/Drop Host Profile

Status: G1E-D candidate  
Parent: #248  
Implements: #261  
Depends on: qualified G1E-A, G1E-B, and G1E-C

## Purpose

Define the concrete bounded Gateway host for explicit file/drop submissions. This host assembles the qualified streamed digest, race-resistant filesystem boundary, and shared Gateway commit path without claiming operating-system watcher completeness or exactly-once discovery.

## Entry point

The G1E-D reference host exposes an explicit asynchronous submission contract. A submission contains:

- normalized relative path beneath the configured intake root;
- bounded transport/host `delivery_id` used only for retry correlation;
- optional bounded filename and content-type claims;
- optional bounded correlation id.

The reference slice intentionally does not start a filesystem watcher. Watcher/discovery products may be added later behind this explicit submission boundary, but their completeness and loss semantics must be qualified separately.

## Authorization order

The host resolves the authenticated principal through the server-side `StaticSourceRegistry` **before any filesystem read**. An unauthorized principal cannot use the host to read or hash an object even if the supplied relative path is otherwise valid.

File names, paths, content-type claims, and file metadata never grant tenant/workspace/source authority.

## Filesystem and digest path

After authorization and bounded admission, the host delegates object resolution and hashing to the qualified G1E-B `digest_filesystem_object()` boundary, which uses the G1E-A bounded streaming digest.

Traversal, unsafe link/reparse behavior, replacement/truncation instability, unsupported secure traversal, declared-size mismatch, and object-size overflow fail before Gateway commitment.

The host does not retain raw bytes after the read boundary.

## Shared commitment

A qualified `FilesystemObjectDigest` is passed to the G1E-C `GatewayFileIngressService`, which uses the existing Gateway `_commit_capture()` lifecycle for:

- stable event/evidence identity;
- retry reconciliation and conflict detection;
- pre-commit synchronization capacity reservation;
- public ETS Core append;
- durable sync enqueue;
- partial-commit receipts and idempotent recovery.

G1E-D introduces no new Core, Merkle, proof, signer, or synchronization implementation.

## Resource bounds

`GatewayFileDropPolicy` declares:

- maximum concurrent submissions;
- admission timeout;
- maximum object bytes;
- read chunk size;
- graceful shutdown duration;
- bounded recent-status history.

A saturated admission window fails explicitly. Object-size overflow is classified as a filesystem rejection rather than being allowed to escape as an unclassified stream-digest exception.

## Operational states

The host records bounded status transitions using only non-content metadata. Status stages are:

- `discovered` — submission admitted and authorized;
- `reading` — qualified resolver/digest is active;
- `rejected` — object, authorization, backpressure, conflict, or capture boundary rejected the submission;
- `committed_local` — local ETS commitment succeeded but no queued sync state is asserted;
- `sync_queued` — local commitment succeeded and durable synchronization is queued;
- `partial_commit` — local commitment succeeded but sync enqueue failed and requires idempotent retry.

Rejection codes are bounded classifications and do not echo raw file content or reusable credentials.

## Shutdown and drain

Shutdown first disables new admission. Already-admitted tasks may continue within the configured grace window. If the window expires, admitted coroutine tasks are cancelled and their operational status is changed to a bounded `shutdown_timeout` rejection. Cancellation prevents the submission coroutine from progressing into ETS commitment after the grace window.

Because Python thread cancellation cannot forcibly stop an already-running host filesystem read, the underlying bounded read operation may finish in its worker thread after coroutine cancellation; its result is discarded and cannot enter the G1E-C commit path. The profile therefore makes no claim of instantaneous physical I/O cancellation.

## Qualification

The deployed qualification covers:

- valid, empty, exact-bound, and one-byte-over-bound objects;
- authorization before file read;
- parent traversal and symlink escape rejection;
- identical retry and conflicting delivery identity;
- local-commit/sync-enqueue partial failure and retry recovery;
- raw-marker absence from status, event, and sync surfaces;
- bounded concurrent submission saturation;
- shutdown preserving admitted work while refusing new submissions;
- architecture scan proving no Gateway File/Drop dependency on ETS Edge or Core internals.

G1E-B separately qualifies replacement/truncation/change races through the same resolver used here.

## Nonclaims

G1E-D does not claim:

- OS watcher completeness;
- exactly-once discovery;
- source-content truth;
- distributed filesystem consistency;
- malware scanning or safety verdicts;
- durable raw-object retention;
- immediate cancellation of an already-running kernel/filesystem read;
- upstream synchronization acknowledgment from local queue state.

## Exit gate

The G1E parent is complete when this concrete host and the preceding G1E slices pass exact-head CI, Security Audit, Formal Specs, Benchmarks, Apalache, Lean, deployed integration qualification, and independent LanternProtocol review.
