from __future__ import annotations

import json
from pathlib import Path
import unittest

from reconstruction_factory.errors import ValidationError
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
    Verdict,
)


TARGET_HASH = "1" * 64


def minimal_graph() -> tuple[Project, Product, TargetIdentity, Subject, Claim]:
    project = Project(id="thxx", name="Test project")
    product = Product(
        id="thxx-main",
        project_id=project.id,
        role="gameplay",
        target_identity_id="target:thxx-main",
    )
    target = TargetIdentity(
        id="target:thxx-main",
        project_id=project.id,
        product_id=product.id,
        game="thxx",
        version="1.00",
        region="test",
        format="pe",
        size=4096,
        sha256=TARGET_HASH,
    )
    subject = Subject(
        id="thxx-main:function:00401000",
        target_identity_id=target.id,
        kind=SubjectKind.FUNCTION,
        name="TestFunction",
        extents=(Extent("pe-va", "0x00401000", 16),),
    )
    claim = Claim(
        id="claim:thxx-main:function:00401000:codegen-exact",
        subject_id=subject.id,
        type=ClaimType.CODEGEN_EXACT,
        target_identity_id=target.id,
        value={"exact": True},
        evidence_class=EvidenceClass.CORROBORATED,
    )
    return project, product, target, subject, claim


class OntologyTests(unittest.TestCase):
    def test_acceptance_pass_requires_complete_coverage(self) -> None:
        *_, claim = minimal_graph()
        with self.assertRaisesRegex(ValidationError, "complete coverage"):
            OracleResult(
                id="result:test",
                oracle_id="windows.function-exact",
                oracle_version="1",
                role=OracleRole.ACCEPTANCE,
                claim_id=claim.id,
                claim_type=claim.type,
                target_identity_id=claim.target_identity_id,
                coverage=Coverage("function-bytes", 16, 8, False),
                verdict=Verdict.PASS,
                evidence_refs=("artifact:test",),
            )

    def test_acceptance_pass_requires_evidence(self) -> None:
        *_, claim = minimal_graph()
        with self.assertRaisesRegex(ValidationError, "durable evidence"):
            OracleResult(
                id="result:test",
                oracle_id="windows.function-exact",
                oracle_version="1",
                role=OracleRole.ACCEPTANCE,
                claim_id=claim.id,
                claim_type=claim.type,
                target_identity_id=claim.target_identity_id,
                coverage=Coverage("function-bytes", 16, 16, True),
                verdict=Verdict.PASS,
                evidence_refs=(),
            )

    def test_snapshot_rejects_cross_target_claim(self) -> None:
        project, product, target, subject, claim = minimal_graph()
        bad_claim = Claim(
            id=claim.id,
            subject_id=claim.subject_id,
            type=claim.type,
            target_identity_id="target:other",
            value=claim.value,
            evidence_class=claim.evidence_class,
        )
        with self.assertRaisesRegex(ValidationError, "different target"):
            RepositorySnapshot(
                project=project,
                products=(product,),
                targets=(target,),
                toolchains=(),
                subjects=(subject,),
                claims=(bad_claim,),
            )

    def test_snapshot_serialization_is_json_compatible(self) -> None:
        project, product, target, subject, claim = minimal_graph()
        snapshot = RepositorySnapshot(
            project=project,
            products=(product,),
            targets=(target,),
            toolchains=(),
            subjects=(subject,),
            claims=(claim,),
            adapter_id="test",
        )
        encoded = json.dumps(snapshot.to_dict(), sort_keys=True)
        self.assertIn('"codegen_exact"', encoded)
        self.assertIn('"pe-va"', encoded)

    def test_schema_and_python_claim_vocabularies_agree(self) -> None:
        schema_path = Path(__file__).parents[1] / "schemas/v1/truth-snapshot.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema_values = set(schema["$defs"]["claim"]["properties"]["type"]["enum"])
        self.assertEqual(schema_values, {item.value for item in ClaimType})


if __name__ == "__main__":
    unittest.main()
