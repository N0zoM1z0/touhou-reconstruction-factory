"""Small content-addressed store for replay output and sealed receipts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Any, Mapping

from .errors import ReplayError, ValidationError
from .ontology import ArtifactRef
from .oracle_receipts import (
    OracleReceipt,
    oracle_receipt_from_dict,
    verify_receipt_integrity,
)


class ArtifactStore:
    """Persist immutable evidence without trusting filenames as identity."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.objects = self.root / "objects" / "sha256"
        self.receipts = self.root / "receipts"

    def add_bytes(
        self,
        payload: bytes,
        *,
        media_type: str,
        producer: str,
        retention_class: str = "oracle-evidence",
    ) -> ArtifactRef:
        digest = hashlib.sha256(payload).hexdigest()
        destination = self.object_path(digest)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            self._verify_object(destination, digest, len(payload))
        else:
            with tempfile.NamedTemporaryFile(
                dir=destination.parent,
                prefix=".incoming-",
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.replace(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
        return ArtifactRef(
            id=f"artifact:sha256:{digest}",
            sha256=digest,
            media_type=media_type,
            size=len(payload),
            retention_class=retention_class,
            producer=producer,
        )

    def add_json(
        self,
        value: Any,
        *,
        producer: str,
        retention_class: str = "oracle-evidence",
    ) -> ArtifactRef:
        payload = (
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        return self.add_bytes(
            payload,
            media_type="application/json",
            producer=producer,
            retention_class=retention_class,
        )

    def object_path(self, digest_or_ref: str) -> Path:
        digest = digest_or_ref.removeprefix("artifact:sha256:")
        if len(digest) != 64 or any(value not in "0123456789abcdef" for value in digest):
            raise ValidationError("artifact object key must be a lowercase SHA-256 digest")
        return self.objects / digest[:2] / digest

    def write_receipt(self, receipt: OracleReceipt) -> Path:
        if not receipt.receipt_id:
            raise ValidationError("cannot store an unsealed receipt")
        document = receipt.to_dict()
        digest = verify_receipt_integrity(document)
        for artifact in receipt.artifacts:
            self._verify_object(
                self.object_path(artifact.sha256), artifact.sha256, artifact.size
            )
        self.receipts.mkdir(parents=True, exist_ok=True)
        destination = self.receipts / f"{digest}.json"
        payload = (
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        if destination.exists():
            if destination.read_bytes() != payload:
                raise ReplayError(f"receipt object collision: {destination}")
            return destination
        with tempfile.NamedTemporaryFile(
            dir=self.receipts,
            prefix=".incoming-",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return destination

    def verify_receipt_document(self, path: str | Path) -> Mapping[str, Any]:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValidationError("receipt document must be an object")
        verify_receipt_integrity(document)
        receipt = oracle_receipt_from_dict(document)
        self.verify_receipt_artifacts(receipt)
        return document

    def verify_receipt_artifacts(self, receipt: OracleReceipt) -> None:
        """Require every artifact named by a semantically valid receipt."""

        for artifact in receipt.artifacts:
            self._verify_object(
                self.object_path(artifact.sha256),
                artifact.sha256,
                artifact.size,
            )

    @staticmethod
    def _verify_object(path: Path, expected_sha256: str, expected_size: int) -> None:
        try:
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        except FileNotFoundError as error:
            raise ReplayError(f"artifact object is missing: {path}") from error
        except OSError as error:
            raise ReplayError(f"artifact object cannot be opened safely: {path}") from error
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ReplayError(f"artifact object is not a regular file: {path}")
            payload = stream.read()
        actual = hashlib.sha256(payload).hexdigest()
        if len(payload) != expected_size or actual != expected_sha256:
            raise ReplayError(f"artifact object failed integrity verification: {path}")
