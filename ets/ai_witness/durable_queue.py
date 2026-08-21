"""Encrypted, restart-safe local queue for the ETS AI Witness appliance profile."""

from __future__ import annotations

import json
import secrets
import sqlite3
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from ets.ai_witness.models import SignedWitnessRecord

_QUEUE_SCHEMA = "ets.ai-witness.queue.v1"
_KEY_CHECK_PLAINTEXT = b"ets-ai-witness-queue-key-check-v1"
_KEY_DERIVATION_INFO = b"ets.ai-witness.queue.aes256gcm.v1"


class WitnessQueueError(RuntimeError):
    """Base error for durable Witness queue failures."""


class DuplicateWitnessRecord(WitnessQueueError):
    """Raised when an immutable record digest is enqueued more than once."""


class QueueIntegrityError(WitnessQueueError):
    """Raised when queue storage or encrypted content fails integrity validation."""


class EncryptedWitnessQueue:
    """SQLite/WAL queue that encrypts complete witness records with AES-256-GCM."""

    def __init__(self, path: Path, *, key_material_hex: str, key_id: str):
        if not key_id or len(key_id) > 256:
            raise WitnessQueueError("queue key_id must contain 1-256 characters")
        self.path = path
        self.key_id = key_id
        self._key = _derive_queue_key(key_material_hex)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.row_factory = sqlite3.Row
        self._configure_database()
        self._initialize_schema()
        self._validate_database_integrity()
        self._validate_or_create_key_check()

    def __enter__(self) -> EncryptedWitnessQueue:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        self._db.close()

    def enqueue(self, record: SignedWitnessRecord) -> int:
        serialized = record.model_dump_json().encode("utf-8")
        nonce = secrets.token_bytes(12)
        aad = _aad(record.record_digest, self.key_id)
        ciphertext = AESGCM(self._key).encrypt(nonce, serialized, aad)
        try:
            with self._db:
                cursor = self._db.execute(
                    """
                    INSERT INTO witness_queue(record_digest, nonce, ciphertext)
                    VALUES (?, ?, ?)
                    """,
                    (record.record_digest, nonce, ciphertext),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateWitnessRecord(
                f"record digest is already queued: {record.record_digest}"
            ) from exc
        row_id = cursor.lastrowid
        if row_id is None:
            raise WitnessQueueError("SQLite did not return a queue row id")
        return int(row_id)

    def peek(self, *, limit: int = 1) -> tuple[SignedWitnessRecord, ...]:
        if limit < 1 or limit > 1_000:
            raise WitnessQueueError("queue peek limit must be between 1 and 1000")
        rows = self._db.execute(
            """
            SELECT record_digest, nonce, ciphertext
            FROM witness_queue
            ORDER BY id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        records: list[SignedWitnessRecord] = []
        for row in rows:
            records.append(self._decrypt_row(row))
        return tuple(records)

    def ack(self, record_digest: str) -> bool:
        with self._db:
            cursor = self._db.execute(
                "DELETE FROM witness_queue WHERE record_digest = ?",
                (record_digest,),
            )
        return cursor.rowcount == 1

    def depth(self) -> int:
        row = self._db.execute("SELECT COUNT(*) AS count FROM witness_queue").fetchone()
        if row is None:
            raise WitnessQueueError("unable to read queue depth")
        return int(row["count"])

    def _configure_database(self) -> None:
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute("PRAGMA busy_timeout=5000")

    def _initialize_schema(self) -> None:
        with self._db:
            self._db.execute(
                """
                CREATE TABLE IF NOT EXISTS queue_meta(
                    name TEXT PRIMARY KEY,
                    value BLOB NOT NULL
                )
                """
            )
            self._db.execute(
                """
                CREATE TABLE IF NOT EXISTS witness_queue(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_digest TEXT NOT NULL UNIQUE,
                    nonce BLOB NOT NULL,
                    ciphertext BLOB NOT NULL
                )
                """
            )
            self._db.execute(
                "INSERT OR IGNORE INTO queue_meta(name, value) VALUES ('schema', ?)",
                (_QUEUE_SCHEMA.encode("ascii"),),
            )
            self._db.execute(
                "INSERT OR IGNORE INTO queue_meta(name, value) VALUES ('key_id', ?)",
                (self.key_id.encode("utf-8"),),
            )

        schema = self._meta_value("schema").decode("ascii")
        stored_key_id = self._meta_value("key_id").decode("utf-8")
        if schema != _QUEUE_SCHEMA:
            raise QueueIntegrityError("unsupported AI Witness queue schema")
        if stored_key_id != self.key_id:
            raise QueueIntegrityError("AI Witness queue key_id does not match persisted metadata")

    def _validate_database_integrity(self) -> None:
        row = self._db.execute("PRAGMA integrity_check").fetchone()
        if row is None or row[0] != "ok":
            raise QueueIntegrityError("SQLite integrity_check failed")

    def _validate_or_create_key_check(self) -> None:
        row = self._db.execute(
            "SELECT value FROM queue_meta WHERE name = 'key_check'"
        ).fetchone()
        if row is None:
            nonce = secrets.token_bytes(12)
            ciphertext = AESGCM(self._key).encrypt(
                nonce,
                _KEY_CHECK_PLAINTEXT,
                _QUEUE_SCHEMA.encode("ascii"),
            )
            payload = json.dumps(
                {"nonce": nonce.hex(), "ciphertext": ciphertext.hex()},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("ascii")
            with self._db:
                self._db.execute(
                    "INSERT INTO queue_meta(name, value) VALUES ('key_check', ?)",
                    (payload,),
                )
            return

        try:
            payload = json.loads(bytes(row["value"]).decode("ascii"))
            nonce = bytes.fromhex(str(payload["nonce"]))
            ciphertext = bytes.fromhex(str(payload["ciphertext"]))
            plaintext = AESGCM(self._key).decrypt(
                nonce,
                ciphertext,
                _QUEUE_SCHEMA.encode("ascii"),
            )
        except (
            InvalidTag,
            KeyError,
            TypeError,
            UnicodeDecodeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raise QueueIntegrityError("AI Witness queue key validation failed") from exc
        if plaintext != _KEY_CHECK_PLAINTEXT:
            raise QueueIntegrityError("AI Witness queue key validation failed")

    def _meta_value(self, name: str) -> bytes:
        row = self._db.execute(
            "SELECT value FROM queue_meta WHERE name = ?",
            (name,),
        ).fetchone()
        if row is None:
            raise QueueIntegrityError(f"missing queue metadata: {name}")
        return bytes(row["value"])

    def _decrypt_row(self, row: sqlite3.Row) -> SignedWitnessRecord:
        record_digest = str(row["record_digest"])
        try:
            plaintext = AESGCM(self._key).decrypt(
                bytes(row["nonce"]),
                bytes(row["ciphertext"]),
                _aad(record_digest, self.key_id),
            )
            record = SignedWitnessRecord.model_validate_json(plaintext)
        except (InvalidTag, ValueError) as exc:
            raise QueueIntegrityError(
                f"queued record failed authenticated decryption: {record_digest}"
            ) from exc
        if record.record_digest != record_digest:
            raise QueueIntegrityError("queued record digest does not match storage index")
        return record


def _derive_queue_key(key_material_hex: str) -> bytes:
    try:
        source = bytes.fromhex(key_material_hex.strip())
    except ValueError as exc:
        raise WitnessQueueError("queue key material must be hexadecimal") from exc
    if len(source) != 32:
        raise WitnessQueueError("queue key material must contain exactly 32 bytes")
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=_KEY_DERIVATION_INFO,
    ).derive(source)


def _aad(record_digest: str, key_id: str) -> bytes:
    return f"{_QUEUE_SCHEMA}:{key_id}:{record_digest}".encode()
