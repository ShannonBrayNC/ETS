from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COLLECTOR = ROOT / "scripts" / "ai_witness" / "collect_platform_evidence.sh"
QUOTE = ROOT / "scripts" / "ai_witness" / "request_tpm_quote.sh"
VERIFY = ROOT / "scripts" / "ai_witness" / "verify_tpm_quote.sh"
HARDWARE = ROOT / "docs" / "product" / "ETS_AI_WITNESS_REFERENCE_HARDWARE.md"
SIGNER = ROOT / "docs" / "spec" / "ETS_AI_WITNESS_SIGNER_PROFILE.md"

FORBIDDEN_MUTATIONS = (
    "tpm2_clear",
    "tpm2_changeauth",
    "tpm2_changeeps",
    "tpm2_changepps",
    "tpm2_evictcontrol",
    "tpm2_hierarchycontrol",
    "tpm2_nvdefine",
    "tpm2_nvundefine",
    "tpm2_pcrallocate",
)


def read(path: Path) -> str:
    assert path.is_file(), f"missing AI Witness qualification asset: {path}"
    return path.read_text(encoding="utf-8")


def test_harness_scripts_are_strict_bash_and_non_destructive() -> None:
    for path in (COLLECTOR, QUOTE, VERIFY):
        text = read(path)
        assert text.startswith("#!/usr/bin/env bash\nset -euo pipefail\n")
        assert "umask 077" in text
        for command in FORBIDDEN_MUTATIONS:
            assert command not in text


def test_platform_collector_captures_required_tpm_and_boot_evidence() -> None:
    text = read(COLLECTOR)
    for capability in ("properties-fixed", "algorithms", "ecc-curves", "pcrs"):
        assert f"tpm2_getcap {capability}" in text
    assert "tpm2_pcrread sha256" in text
    assert "mokutil --sb-state" in text
    assert "/sys/kernel/security/tpm0/binary_bios_measurements" in text
    assert "manifest.sha256" in text


def test_quote_request_requires_nonce_and_selected_pcrs() -> None:
    text = read(QUOTE)
    assert "NONCE_HEX" in text
    assert "tpm2_quote" in text
    assert '-q "$nonce_hex"' in text
    assert '-l "$pcr_selection"' in text
    assert "sha256:0,2,4,7" in text
    assert "quote.msg" in text
    assert "quote.sig" in text
    assert "quote.pcrs" in text


def test_quote_verifier_binds_nonce_pcrs_and_ak_public_key() -> None:
    text = read(VERIFY)
    assert "tpm2_checkquote" in text
    assert '-u "$ak_public"' in text
    assert '-q "$nonce_hex"' in text
    assert '-l "$pcr_selection"' in text
    assert '-m "$quote_dir/quote.msg"' in text
    assert '-s "$quote_dir/quote.sig"' in text
    assert '-f "$quote_dir/quote.pcrs"' in text


def test_reference_hardware_doc_freezes_named_pilot_boundaries() -> None:
    text = read(HARDWARE)
    assert "ThinkCentre M90q Gen 6" in text
    assert "Dell Pro Micro QCM1250" in text
    assert "Ubuntu Server 24.04 LTS" in text
    assert "ECDSA P-256/SHA-256" in text
    assert "1 TB high-endurance" in text
    assert "32 GiB" in text
    assert "seven-day soak" in text


def test_signer_profile_preserves_v1_and_requires_algorithm_bound_v2() -> None:
    text = read(SIGNER)
    assert "ets.ai-witness.record.v1" in text
    assert "ets.ai-witness.record.v2" in text
    assert "ecdsa-p256-sha256" in text
    assert "canonical low-S" in text
    assert "MUST NOT expose or return a private key" in text
