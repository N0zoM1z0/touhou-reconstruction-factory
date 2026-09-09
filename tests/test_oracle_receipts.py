from __future__ import annotations

from dataclasses import replace
import unittest

from reconstruction_factory.errors import ValidationError
from reconstruction_factory.ontology import (
    ArtifactRef,
    ClaimType,
    Coverage,
    Extent,
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
    canonical_sha256,
    oracle_receipt_from_dict,
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
        coverage=Coverage("claimed-bytes", 4, 4, True),
        verdict=verdict,
        evidence_refs=(ARTIFACT.id,),
    )
    stage_record = {
        "id": "compare",
        "argv": ("python3", "scripts/compare.py"),
        "cwd": ".",
        "environment_sha256": SHA_A,
    }
    stage = InvocationStage(
        "compare",
        stage_record["argv"],
        ".",
        SHA_A,
        canonical_sha256(
            {
                "claim_sha256": SHA_A,
                "subject_sha256": SHA_B,
                "source_sha256": SHA_A,
                "target_sha256": SHA_A,
                "toolchain_components_sha256": canonical_sha256(
                    [
                        {
                            "id": "compiler",
                            "kind": "file",
                            "logical_path": "toolchain/cl.exe",
                            "sha256": SHA_A,
                            "size": 2,
                            "file_count": 1,
                        }
                    ]
                ),
                "environment_sha256": SHA_A,
                "runner_implementation_sha256": SHA_A,
                "driver_version": SHA_B,
                "stage": stage_record,
            }
        ),
    )
    execution = StageExecution("compare", 0, False, 5, ARTIFACT.id, ARTIFACT.id)
    return OracleReceipt(
        receipt_id="",
        created_utc="2026-09-09T00:00:00+00:00",
        repository_adapter_id="test-adapter",
        oracle_id=result.oracle_id,
        oracle_version=result.oracle_version,
        claim=ClaimBinding(
            "claim:test", "codegen_exact", SHA_A, "subject:test", SHA_B,
            (Extent("pe-va", "0x00401000", 4),),
        ),
        source_before=source,
        source_after=source,
        target=TargetBinding(
            "target:test", "resources/test.exe", SHA_A, SHA_A, SHA_A, 4, 4, 4
        ),
        toolchain=ToolchainBinding(
            "toolchain:test", SHA_B, AttestationLevel.OBSERVED,
            (ComponentObservation("compiler", "file", "toolchain/cl.exe", SHA_A, 2, 1),),
            canonical_sha256([
                {
                    "id": "compiler", "kind": "file", "logical_path": "toolchain/cl.exe",
                    "sha256": SHA_A, "size": 2, "file_count": 1,
                }
            ]),
            canonical_sha256([
                {
                    "id": "compiler", "kind": "file", "logical_path": "toolchain/cl.exe",
                    "sha256": SHA_A, "size": 2, "file_count": 1,
                }
            ]),
            SHA_A,
        ),
        invocation=InvocationBinding("test-driver", SHA_B, coldness, (stage,), (execution,)),
        result=result,
        artifacts=(ARTIFACT,),
        native_report_ref=ARTIFACT.id,
        runner_implementation_sha256=SHA_A,
        runner_observed_after_sha256=SHA_A,
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

    def test_receipt_rejects_stage_digest_detached_from_bindings(self) -> None:
        base = receipt(verdict=Verdict.FAIL)
        bad_stage = replace(base.invocation.stages[0], input_sha256=SHA_B)
        with self.assertRaisesRegex(ValidationError, "stage input digest"):
            replace(
                base,
                invocation=replace(base.invocation, stages=(bad_stage,)),
            )

    def test_semantic_validation_rejects_rehashed_incremental_pass(self) -> None:
        document = receipt().seal().to_dict()
        document["invocation"]["coldness"] = "incremental"
        document["receipt_id"] = ""
        document["receipt_id"] = "receipt:" + canonical_sha256(document)
        with self.assertRaisesRegex(ValidationError, "cold replay"):
            oracle_receipt_from_dict(document)

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

    def test_acceptance_pass_rejects_git_identity_change(self) -> None:
        base = receipt(verdict=Verdict.FAIL)
        with self.assertRaisesRegex(ValidationError, "stable source"):
            replace(
                base,
                result=replace(base.result, verdict=Verdict.PASS),
                source_after=replace(base.source_after, git_commit="3" * 40),
            )

    def test_acceptance_pass_rejects_runner_mutation(self) -> None:
        base = receipt(verdict=Verdict.FAIL)
        with self.assertRaisesRegex(ValidationError, "stable runner"):
            replace(
                base,
                result=replace(base.result, verdict=Verdict.PASS),
                runner_observed_after_sha256=SHA_B,
            )

    def test_receipt_rejects_artifact_id_not_derived_from_content(self) -> None:
        base = receipt(verdict=Verdict.FAIL)
        forged = replace(ARTIFACT, id="artifact:sha256:" + SHA_B)
        execution = replace(
            base.invocation.executions[0],
            stdout_ref=forged.id,
            stderr_ref=forged.id,
        )
        with self.assertRaisesRegex(ValidationError, "content-addressed"):
            replace(
                base,
                artifacts=(forged,),
                native_report_ref=forged.id,
                invocation=replace(base.invocation, executions=(execution,)),
                result=replace(base.result, evidence_refs=(forged.id,)),
            )

    def test_nonpassing_receipt_preserves_acceptance_errors(self) -> None:
        base = receipt(verdict=Verdict.INCOMPLETE)
        incomplete = replace(base, acceptance_errors=("extent-unattested",)).seal()
        self.assertEqual(incomplete.result.verdict, Verdict.INCOMPLETE)


if __name__ == "__main__":
    unittest.main()
