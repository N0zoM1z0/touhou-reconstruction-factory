from __future__ import annotations

from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reconstruction_factory.acceptance import (
    AcceptanceDecision,
    AcceptancePolicy,
    build_acceptance_registry,
    load_acceptance_policy,
)
from reconstruction_factory.artifact_store import ArtifactStore
from reconstruction_factory.errors import AcceptanceError, ValidationError
from reconstruction_factory.ontology import (
    Claim,
    ClaimType,
    Coverage,
    EvidenceClass,
    Extent,
    OracleResult,
    OracleRole,
    Product,
    Project,
    RepositorySnapshot,
    Subject,
    SubjectKind,
    TargetIdentity,
    ToolchainIdentity,
    Verdict,
    to_primitive,
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
)


SHA_A = "a" * 64
SHA_B = "b" * 64


def policy(*, allow_dirty_source: bool = True) -> AcceptancePolicy:
    return AcceptancePolicy(
        id="test-live-v1",
        description="Test only policy.",
        allowed_adapter_ids=("test-adapter",),
        allowed_claim_types=(ClaimType.CODEGEN_EXACT,),
        allowed_oracle_ids=("test.function-exact",),
        allowed_driver_ids=("test-function-v1",),
        allowed_coldness=(Coldness.FORCED_RECOMPILE,),
        minimum_attestation=AttestationLevel.OBSERVED,
        allow_dirty_source=allow_dirty_source,
    )


def snapshot_and_receipt(
    store: ArtifactStore,
    *,
    dirty: bool = False,
) -> tuple[RepositorySnapshot, OracleReceipt]:
    project = Project("test", "Test")
    product = Product("test-main", project.id, "gameplay", "target:test-main")
    target = TargetIdentity(
        "target:test-main",
        project.id,
        product.id,
        "test",
        "1.00",
        "test",
        "pe",
        4,
        SHA_A,
    )
    toolchain = ToolchainIdentity(
        "toolchain:test",
        project.id,
        "msvc7",
        "Test compiler",
        SHA_B,
    )
    subject = Subject(
        "test-main:function:00401000",
        target.id,
        SubjectKind.FUNCTION,
        "TestFunction",
        (Extent("pe-va", "0x00401000", 4),),
    )
    claim = Claim(
        "claim:test-main:function:00401000:codegen-exact",
        subject.id,
        ClaimType.CODEGEN_EXACT,
        target.id,
        {"exact": True, "unit": "test-unit"},
        EvidenceClass.CORROBORATED,
        toolchain.id,
    )
    source = SourceBinding("1" * 40, "2" * 40, ".", SHA_A, 3, dirty, 1 if dirty else 0)
    artifact = store.add_json({}, producer="test")
    component = ComponentObservation(
        "compiler",
        "file",
        "$TEST/cl.exe",
        SHA_A,
        2,
        1,
    )
    component_sha256 = canonical_sha256(to_primitive((component,)))
    stage_environment_sha256 = canonical_sha256({"PATH": "/test"})
    stage_record = {
        "id": "compare",
        "argv": ("python3", "scripts/compare.py"),
        "cwd": ".",
        "environment_sha256": stage_environment_sha256,
    }
    claim_sha256 = canonical_sha256(to_primitive(claim))
    subject_sha256 = canonical_sha256(to_primitive(subject))
    stage = InvocationStage(
        id="compare",
        argv=stage_record["argv"],
        cwd=".",
        environment_sha256=stage_environment_sha256,
        input_sha256=canonical_sha256(
            {
                "claim_sha256": claim_sha256,
                "subject_sha256": subject_sha256,
                "source_sha256": SHA_A,
                "target_sha256": SHA_A,
                "toolchain_components_sha256": component_sha256,
                "environment_sha256": SHA_A,
                "runner_implementation_sha256": SHA_A,
                "driver_version": SHA_B,
                "stage": stage_record,
            }
        ),
    )
    result = OracleResult(
        id="result:test",
        oracle_id="test.function-exact",
        oracle_version=SHA_B,
        role=OracleRole.ACCEPTANCE,
        claim_id=claim.id,
        claim_type=claim.type,
        target_identity_id=target.id,
        toolchain_identity_id=toolchain.id,
        source_tree=SHA_A,
        coverage=Coverage("claimed-bytes", 4, 4, True),
        verdict=Verdict.PASS,
        evidence_refs=(artifact.id,),
    )
    receipt = OracleReceipt(
        receipt_id="",
        created_utc="2026-09-09T00:00:00+00:00",
        repository_adapter_id="test-adapter",
        oracle_id=result.oracle_id,
        oracle_version=result.oracle_version,
        claim=ClaimBinding(
            claim.id,
            claim.type.value,
            claim_sha256,
            subject.id,
            subject_sha256,
            subject.extents,
        ),
        source_before=source,
        source_after=source,
        target=TargetBinding(
            target.id,
            "resources/test.exe",
            SHA_A,
            SHA_A,
            SHA_A,
            4,
            4,
            4,
        ),
        toolchain=ToolchainBinding(
            toolchain.id,
            SHA_B,
            AttestationLevel.OBSERVED,
            (component,),
            component_sha256,
            component_sha256,
            SHA_A,
            ("PATH",),
        ),
        invocation=InvocationBinding(
            "test-function-v1",
            SHA_B,
            Coldness.FORCED_RECOMPILE,
            (stage,),
            (StageExecution("compare", 0, False, 1, artifact.id, artifact.id),),
        ),
        result=result,
        artifacts=(artifact,),
        native_report_ref=artifact.id,
        runner_implementation_sha256=SHA_A,
        runner_observed_after_sha256=SHA_A,
    ).seal()
    imported = replace(
        result,
        id="result:untrusted-import",
        verdict=Verdict.INCOMPLETE,
        evidence_refs=(),
    )
    snapshot = RepositorySnapshot(
        project,
        (product,),
        (target,),
        (toolchain,),
        (subject,),
        (claim,),
        oracle_results=(imported,),
        adapter_id="test-adapter",
    )
    return snapshot, receipt


class AcceptanceRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.repository = root / "game"
        self.repository.mkdir()
        self.store = ArtifactStore(root / "store")
        self.snapshot, self.receipt = snapshot_and_receipt(self.store)
        self.receipt_path = self.store.write_receipt(self.receipt)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def build(self, selected_policy: AcceptancePolicy | None = None, *, freshness=()):
        with (
            patch(
                "reconstruction_factory.acceptance.repository_lock",
                return_value=nullcontext(),
            ),
            patch(
                "reconstruction_factory.acceptance.verify_live_freshness",
                return_value=freshness,
            ),
        ):
            return build_acceptance_registry(
                self.store,
                selected_policy or policy(),
                {self.receipt.target.identity_id: self.repository},
            )

    def test_verified_receipt_is_accepted_and_materialized(self) -> None:
        registry = self.build()
        self.assertEqual(registry.accepted_count, 1)
        self.assertEqual(registry.entries[0].decision, AcceptanceDecision.ACCEPTED)
        with (
            patch(
                "reconstruction_factory.acceptance.repository_lock",
                return_value=nullcontext(),
            ),
            patch(
                "reconstruction_factory.acceptance.verify_live_freshness",
                return_value=(),
            ),
            patch(
                "reconstruction_factory.acceptance.inspect_repository",
                return_value=self.snapshot,
            ),
        ):
            facts = registry.accepted_facts(claim_type=ClaimType.CODEGEN_EXACT)
            materialized = registry.materialize_live_snapshot(self.repository)
        self.assertEqual(len(facts), 1)
        self.assertEqual(materialized.oracle_results, (self.receipt.result,))
        self.assertNotIn("result:untrusted-import", {
            item.id for item in materialized.oracle_results
        })
        self.assertEqual(materialized.artifacts, self.receipt.artifacts)

    def test_registry_is_content_addressed_and_deterministic(self) -> None:
        left = self.build()
        right = self.build()
        self.assertEqual(left.registry_id, right.registry_id)

    def test_invalid_candidate_contents_are_bound_into_registry_id(self) -> None:
        self.receipt_path.write_text("not json\n", encoding="utf-8")
        left = self.build()
        self.receipt_path.write_text("still not json\n", encoding="utf-8")
        right = self.build()
        self.assertNotEqual(left.registry_id, right.registry_id)

    def test_snapshot_fingerprint_ignores_unrelated_rejected_candidates(self) -> None:
        left = self.build()._materialize_snapshot(self.snapshot)
        (self.store.receipts / "bad.json").write_text("not json\n", encoding="utf-8")
        right_registry = self.build()
        right = right_registry._materialize_snapshot(self.snapshot)
        self.assertEqual(right_registry.invalid_count, 1)
        self.assertEqual(
            left.input_fingerprint_sha256,
            right.input_fingerprint_sha256,
        )

    def test_missing_repository_binding_rejects_receipt(self) -> None:
        registry = build_acceptance_registry(self.store, policy(), {})
        self.assertEqual(registry.rejected_count, 1)
        self.assertEqual(registry.entries[0].reasons, ("repository-binding-missing",))

    def test_freshness_failure_rejects_receipt(self) -> None:
        registry = self.build(freshness=("source-snapshot-stale",))
        self.assertEqual(registry.rejected_count, 1)
        self.assertEqual(
            registry.entries[0].reasons,
            ("freshness:source-snapshot-stale",),
        )

    def test_dirty_source_is_an_explicit_policy_choice(self) -> None:
        dirty_store = ArtifactStore(Path(self.temporary.name) / "dirty-store")
        _, dirty_receipt = snapshot_and_receipt(dirty_store, dirty=True)
        dirty_store.write_receipt(dirty_receipt)
        with (
            patch(
                "reconstruction_factory.acceptance.repository_lock",
                return_value=nullcontext(),
            ),
            patch(
                "reconstruction_factory.acceptance.verify_live_freshness",
                return_value=(),
            ),
        ):
            registry = build_acceptance_registry(
                dirty_store,
                policy(allow_dirty_source=False),
                {dirty_receipt.target.identity_id: self.repository},
            )
        self.assertEqual(registry.rejected_count, 1)
        self.assertIn("dirty-source-not-allowed", registry.entries[0].reasons)

    def test_missing_artifact_marks_candidate_invalid(self) -> None:
        self.store.object_path(self.receipt.artifacts[0].id).unlink()
        registry = self.build()
        self.assertEqual(registry.invalid_count, 1)
        self.assertEqual(
            registry.entries[0].reasons,
            ("receipt-artifact-integrity-failed",),
        )

    def test_symlinked_artifact_marks_candidate_invalid(self) -> None:
        object_path = self.store.object_path(self.receipt.artifacts[0].id)
        replacement = object_path.with_name("external-object")
        object_path.rename(replacement)
        object_path.symlink_to(replacement)
        registry = self.build()
        self.assertEqual(registry.invalid_count, 1)
        self.assertEqual(
            registry.entries[0].reasons,
            ("receipt-artifact-integrity-failed",),
        )

    def test_receipt_filename_must_match_content_identity(self) -> None:
        renamed = self.receipt_path.with_name("0" * 64 + ".json")
        self.receipt_path.rename(renamed)
        registry = self.build()
        self.assertEqual(registry.invalid_count, 1)
        self.assertEqual(
            registry.entries[0].reasons,
            ("receipt-storage-key-mismatch",),
        )

    def test_materialization_rechecks_normalized_claim(self) -> None:
        registry = self.build()
        changed_claim = replace(self.snapshot.claims[0], value={"exact": False})
        changed = replace(self.snapshot, claims=(changed_claim,))
        with self.assertRaisesRegex(AcceptanceError, "claim changed"):
            registry._materialize_snapshot(changed)

    def test_query_rechecks_artifacts_after_registry_build(self) -> None:
        registry = self.build()
        self.store.object_path(self.receipt.artifacts[0].id).unlink()
        with patch(
            "reconstruction_factory.acceptance.repository_lock",
            return_value=nullcontext(),
        ):
            with self.assertRaisesRegex(AcceptanceError, "artifact became invalid"):
                registry.accepted_facts()

    def test_query_rechecks_freshness_after_registry_build(self) -> None:
        registry = self.build()
        with (
            patch(
                "reconstruction_factory.acceptance.repository_lock",
                return_value=nullcontext(),
            ),
            patch(
                "reconstruction_factory.acceptance.verify_live_freshness",
                return_value=("source-snapshot-stale",),
            ),
        ):
            with self.assertRaisesRegex(AcceptanceError, "became stale"):
                registry.accepted_facts()

    def test_policy_cannot_accept_unknown_attestation(self) -> None:
        with self.assertRaisesRegex(ValidationError, "cannot be unknown"):
            replace(policy(), minimum_attestation=AttestationLevel.UNKNOWN)

    def test_policy_rejects_boolean_schema_version(self) -> None:
        with self.assertRaisesRegex(ValidationError, "schema version"):
            replace(policy(), schema_version=True)

    def test_packaged_policy_is_strict_and_loadable(self) -> None:
        path = Path(__file__).parents[1] / "policies/strict-live-v1.json"
        loaded = load_acceptance_policy(path)
        self.assertEqual(loaded.id, "strict-live-v1")
        self.assertTrue(loaded.require_live_freshness)
        self.assertIn(ClaimType.WHOLE_BUILD_CLOSED, loaded.allowed_claim_types)
        self.assertIn(
            "th095-vc71-whole-build-v1", loaded.allowed_driver_ids
        )
        self.assertNotIn(
            ClaimType.RUNTIME_SCENARIO_VALIDATED, loaded.allowed_claim_types
        )
        self.assertEqual(
            dict(loaded.driver_attestation_minimums)[
                "th04-main-owned-extent-v1"
            ],
            AttestationLevel.VERIFIED,
        )
        self.assertEqual(
            dict(loaded.driver_attestation_minimums)[
                "th095-vc71-whole-build-v1"
            ],
            AttestationLevel.VERIFIED,
        )


if __name__ == "__main__":
    unittest.main()
