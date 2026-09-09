from __future__ import annotations

from dataclasses import replace
import unittest

from reconstruction_factory.errors import ValidationError
from reconstruction_factory.ontology import (
    ArtifactRef,
    ClaimType,
    Coverage,
    OracleResult,
    OracleRole,
    Verdict,
)
from reconstruction_factory.oracle_receipts import (
    AttestationLevel,
    ClaimBinding,
    Coldness,
    ComponentObservation,
    InvocationBinding,
    InvocationStage,
    OracleReceipt,
    SourceBinding,
    StageExecution,
    TargetBinding,
    ToolchainBinding,
    verify_receipt_integrity,
)


SHA_A = "a" * 64
SHA_B = "b" * 64
ARTIFACT = ArtifactRef(
    id="artifact:sha256:" + SHA_A,
    sha256=SHA_A,
    media_type="application/json",
    size=2,
    retention_class="oracle-evidence",
    producer="test",
)


def receipt(*, verdict: Verdict = Verdict.PASS, coldness: Coldness = Coldness.FORCED_RECOMPILE) -> OracleReceipt:
    source = SourceBinding("1" * 40, "2" * 40, ".", SHA_A, 3, True, 1)
    result = OracleResult(
        id="result:test",
        oracle_id="windows.msvc7.function-exact",
        oracle_version=SHA_B,
        role=OracleRole.ACCEPTANCE,
        claim_id="claim:test",
        claim_type=ClaimType.CODEGEN_EXACT,
        target_identity_id="target:test",
        toolchain_identity_id="toolchain:test",
        source_tree=SHA_A,
        coverage=Coverage("subject-extents", 1, 1, True),
        verdict=verdict,
        evidence_refs=(ARTIFACT.id,),
    )
    stage = InvocationStage("compare", ("python3", "scripts/compare.py"), ".", SHA_A)
    execution = StageExecution("compare", 0, False, 5, ARTIFACT.id, ARTIFACT.id)
    return OracleReceipt(
        receipt_id="",
        created_utc="2026-09-09T00:00:00+00:00",
        repository_adapter_id="test-adapter",
        oracle_id=result.oracle_id,
        oracle_version=result.oracle_version,
        claim=ClaimBinding(
            "claim:test", "codegen_exact", SHA_A, "subject:test", SHA_B,
            ({"address_space": "pe-va", "start": "0x00401000", "size": 4},),
        ),
        source_before=source,
        source_after=source,
        target=TargetBinding("target:test", "resources/test.exe", SHA_A, SHA_A, 4, 4),
        toolchain=ToolchainBinding(
            "toolchain:test", SHA_B, AttestationLevel.OBSERVED,
            (ComponentObservation("compiler", "file", "toolchain/cl.exe", SHA_A, 2, 1),),
            SHA_A,
        ),
        invocation=InvocationBinding("test-driver", SHA_B, coldness, (stage,), (execution,)),
        result=result,
        artifacts=(ARTIFACT,),
        native_report_ref=ARTIFACT.id,
    )


class OracleReceiptTests(unittest.TestCase):
    def test_sealed_receipt_is_content_addressed(self) -> None:
        sealed = receipt().seal()
        self.assertEqual(verify_receipt_integrity(sealed.to_dict()), sealed.receipt_id.removeprefix("receipt:"))

    def test_integrity_rejects_tampering(self) -> None:
        document = receipt().seal().to_dict()
        document["repository_adapter_id"] = "tampered"
        with self.assertRaisesRegex(ValidationError, "does not match"):
            verify_receipt_integrity(document)

    def test_acceptance_pass_rejects_incremental_replay(self) -> None:
        with self.assertRaisesRegex(ValidationError, "cold replay"):
            receipt(coldness=Coldness.INCREMENTAL)

    def test_acceptance_pass_rejects_source_mutation(self) -> None:
        base = receipt(verdict=Verdict.FAIL)
        passing = replace(base.result, verdict=Verdict.PASS)
        with self.assertRaisesRegex(ValidationError, "stable source"):
            replace(
                base,
                result=passing,
                source_after=replace(base.source_after, snapshot_sha256=SHA_B),
            )

    def test_nonpassing_receipt_preserves_acceptance_errors(self) -> None:
        base = receipt(verdict=Verdict.INCOMPLETE)
        incomplete = replace(base, acceptance_errors=("extent-unattested",)).seal()
        self.assertEqual(incomplete.result.verdict, Verdict.INCOMPLETE)


if __name__ == "__main__":
    unittest.main()
