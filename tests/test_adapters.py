from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from reconstruction_factory.adapters import inspect_repository
from reconstruction_factory.adapters.common import RepositoryReader
from reconstruction_factory.errors import AdapterError
from reconstruction_factory.factory import kit_for_snapshot
from reconstruction_factory.ontology import ClaimType, ExtentRole


HASH_A = "a" * 64
HASH_B = "b" * 64


def write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def metric(snapshot, name: str, scope: str | None = None):
    scope = scope or snapshot.project.id
    return next(
        item.value
        for item in snapshot.metrics
        if item.name == name and item.scope_id == scope
    )


def make_th04(root: Path) -> None:
    write(
        root,
        "config/targets.toml",
        f'''[source]
kind = "hdi"
hdi_sha256 = "{HASH_B}"
canonicality = "candidate-local-attested"

[[artifacts]]
id = "th04-main"
game = "th04"
role = "gameplay"
dos_path = "GENSO/MAIN.EXE"
format = "mz"
size = 4096
sha256 = "{HASH_A}"
required = true

[[artifacts]]
id = "th01-smoke"
game = "th01"
role = "oracle-smoke"
format = "mz"
size = 1024
sha256 = "{HASH_B}"
required = false
''',
    )
    write(
        root,
        "config/toolchain.toml",
        f'''[exact]
family = "Borland Turbo C++ test"
compiler = "TCC.EXE"
assembler = "TASM32.EXE"
linker = "TLINK.EXE"
status = "candidate-local-attested"

[[surfaces]]
id = "compiler"
sha256 = "{HASH_A}"
required = true
''',
    )
    write(
        root,
        "config/th04_function_boundaries.csv",
        "id,artifact,segment_identity,segment_offset,analysis_linear,payload_offset,body_size,body_span,boundary_state,origin,work_queue,accepted_state,name,evidence_basis,observation\n"
        "th04-main-zero,th04-main,mz-load-module,0x0,0x10000,0x0,0x0,0x0,provisional,compiler,exclude,excluded,__AHSHIFT,map-public,map-public\n"
        "th04-main-fn,th04-main,CODE,0x10,0x10010,0x10,0x10,0x10,reviewed,authored,reconstruct,exact,GameFn,target+listing,listing\n",
    )
    write(
        root,
        "config/th04_main_authored_functions.csv",
        "id,artifact,address,file_offset,size,boundary_state,state,name,owner_unit,source,evidence_ids,notes\n"
        "fn,th04-main,0x10010,0x10,0x10,reviewed,exact,GameFn(),unit,src/main.cpp,ev-fn,exact\n",
    )
    write(
        root,
        "config/units.csv",
        "id,artifact,kind,segment,offset,file_offset,size,compare_size,boundary_state,origin,state,name,source,evidence_ids,replay_command,notes\n"
        "unit,th04-main,function,CODE,0x10,0x10,0x10,0x10,reviewed,authored,exact,GameFn,src/main.cpp,ev-unit,python replay.py,exact\n",
    )


def make_windows(
    root: Path,
    *,
    vc8: bool = False,
    bad_owner_target: bool = False,
    whole_build: bool = False,
) -> None:
    project = "th105" if vc8 else "th095"
    family = (
        "Microsoft Visual C++ 2005 (VC8)"
        if vc8
        else "Microsoft Visual C++ .NET 2003 (VC7.1)"
    )
    ltcg = "rich_utc1400_ltcg_cpp = 42\n" if vc8 else ""
    write(
        root,
        "config/target.toml",
        f'''[target]
title = "Test {project}"
version = "1.00"
region = "test"
filename = "{project}.exe"
size = 4096
sha256 = "{HASH_A}"

[pe]
machine = "i386"
image_base = "0x00400000"
entry_point = "0x00401000"
text_start = "0x00401000"
text_end = "0x00401017"

[toolchain]
family = "{family}"
{ltcg}''',
    )
    write(root, "config/tools.lock.toml", "[objdiff]\nversion = \"test\"\n")
    write(
        root,
        "config/functions.csv",
        "address,size,span_end,current_name,proposed_name,module,status,match_percent,calling_convention,signature,is_thunk,source_file,evidence,owner,notes\n"
        "0x00401000,16,0x0040100F,FUN_00401000,TestFn,engine,matching,100.00,__cdecl,void TestFn(),false,src/Test.cpp,native,root,\n"
        "0x00401010,8,0x00401017,FUN_00401010,,runtime,unclassified,0.00,__cdecl,void Unknown(),false,,,root,\n",
    )
    origins = (
        "0x00401000,authored_game,engine,authored,observed,ev-authored\n"
        "0x00401010,unknown,unknown,review,unknown,\n"
        if vc8
        else "0x00401000,authored,engine,authored,exact,ev-authored\n"
        "0x00401010,compiler,runtime,exclude,high,ev-compiler\n"
    )
    write(
        root,
        "config/function-origins.csv",
        "address,origin,subsystem,disposition,confidence,evidence_id\n" + origins,
    )
    write(
        root,
        "config/reccmp-functions.csv",
        "name,address,type\nTestFn,0x00401000,function\n",
    )
    write(root, "config/implemented.csv", "TestFn\n")
    write(
        root,
        "config/matches.csv",
        "address,name,size,status,match_percent,unit,evidence\n"
        "0x00401000,TestFn,16,matching,100.00,test-unit,native exact\n",
    )
    profile = 'profile = ["/MT", "/Od"]\n' if whole_build else ""
    write(
        root,
        "config/match-units.toml",
        f"[units.test-unit]\nsource = \"src/Test.cpp\"\n{profile}",
    )
    if whole_build:
        write(root, "scripts/build-whole.py", "raise SystemExit(0)\n")
    if vc8:
        owner_hash = HASH_B if bad_owner_target else HASH_A
        write(
            root,
            "config/function-byte-ownership.toml",
            f'''schema_version = 1
target_sha256 = "{owner_hash}"

[[functions]]
address = "0x00401000"
main_size = 16
main_end = "0x0040100F"
main_excluded_bytes = 0
extent_end = "0x00401023"
remote_bytes = 4
owned_bytes = 20
remote_exact = false
evidence = "Attested remote owner test fixture."

[[functions.chunks]]
start = "0x00401020"
end = "0x00401023"
size = 4
sha256 = "{HASH_B}"
''',
        )


def make_th08(root: Path) -> None:
    write(
        root,
        "config/target.toml",
        f'''[target]
title = "Test th08"
version = "1.00d"
region = "test"
filename = "th08.exe"
size = 4096
sha256 = "{HASH_A}"

[pe]
machine = "i386"
image_base = "0x00400000"
entry_point = "0x00401000"
text_start = "0x00401000"
text_end = "0x0040102F"

[toolchain]
family = "Microsoft Visual C++ .NET 2002 (VC7)"
compiler_build = 9466
''',
    )
    write(
        root,
        "config/mapping.csv",
        "th08::Shared,0x00401000,0x10,__cdecl,,void\n"
        "th08::Shared,0x00401010,0x10,__cdecl,,void\n"
        "LibraryFn,0x00401020,0x10,__cdecl,,void\n",
    )
    write(
        root,
        "config/reccmp-functions.csv",
        "name,address,type\n"
        "th08::Shared,0x00401000,function\n"
        "th08::Shared,0x00401010,function\n"
        "LibraryFn,0x00401020,library\n",
    )
    write(root, "config/implemented.csv", "th08::Shared\n")
    write(
        root,
        "config/matches.csv",
        "address,name,size,status,match_percent,unit,evidence\n"
        "0x00401000,th08::Shared,16,matching,100.00,shared-a,exact\n"
        "0x00401010,th08::Shared,16,matching,100.00,shared-b,exact\n",
    )
    write(
        root,
        "config/match-units.toml",
        "schema_version = 1\n"
        "[[units]]\nname = \"shared-a\"\ntarget_address = 0x00401000\n"
        "[[units]]\nname = \"shared-b\"\ntarget_address = 0x00401010\n",
    )
    write(
        root,
        "config/library-matches.csv",
        "address,name,size,status,unit,evidence\n"
        "0x00401020,LibraryFn,16,matching,library-fn,exact\n",
    )
    write(
        root,
        "config/library-match-units.toml",
        "schema_version = 1\n"
        "[[units]]\nname = \"library-fn\"\ntarget_address = 0x00401020\n",
    )
    write(
        root,
        "config/library-provenance.toml",
        f'''schema_version = 1
[[archives]]
id = "vc7-lib"
sha256 = "{HASH_B}"
''',
    )


class AdapterTests(unittest.TestCase):
    def test_th08_name_aliases_count_source_presence_by_address(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_th08(root)
            snapshot = inspect_repository(root)
            self.assertEqual(snapshot.adapter_id, "th08-vc7-ledgers-v1")
            self.assertEqual(metric(snapshot, "inventory.authored"), 2)
            self.assertEqual(metric(snapshot, "source.present-functions"), 2)
            self.assertEqual(metric(snapshot, "exact.functions"), 2)
            self.assertEqual(metric(snapshot, "library.exact-functions"), 1)
            self.assertEqual(snapshot.oracle_results, ())
            self.assertEqual(kit_for_snapshot(snapshot).toolchain.id, "msvc7")

    def test_th04_preserves_unknown_version_and_zero_extent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_th04(root)
            snapshot = inspect_repository(root)
            self.assertEqual(snapshot.adapter_id, "th04-pc98-v1")
            self.assertEqual(snapshot.targets[0].version, "unknown")
            zero = next(item for item in snapshot.subjects if item.id == "th04-main-zero")
            self.assertEqual(zero.extents, ())
            self.assertEqual(metric(snapshot, "inventory.authored-candidates"), 1)
            self.assertEqual(metric(snapshot, "exact.authored-bytes"), 16)
            self.assertEqual(kit_for_snapshot(snapshot).platform.id, "pc98-mz-omf")

    def test_windows_import_does_not_manufacture_oracle_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_windows(root)
            snapshot = inspect_repository(root)
            self.assertEqual(metric(snapshot, "exact.functions"), 1)
            self.assertEqual(snapshot.targets[0].canonicality, "manifest-declared")
            self.assertEqual(snapshot.oracle_results, ())
            exact_claims = [
                claim for claim in snapshot.claims if claim.type is ClaimType.CODEGEN_EXACT
            ]
            self.assertEqual(len(exact_claims), 1)
            self.assertEqual(kit_for_snapshot(snapshot).toolchain.id, "msvc71")

    def test_th095_declares_independent_product_build_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_windows(root, whole_build=True)
            snapshot = inspect_repository(root)
            product_subject = next(
                subject
                for subject in snapshot.subjects
                if subject.kind.value == "product"
            )
            claim = next(
                claim
                for claim in snapshot.claims
                if claim.type is ClaimType.WHOLE_BUILD_CLOSED
            )
            self.assertEqual(claim.subject_id, product_subject.id)
            self.assertEqual(claim.evidence_class.value, "unknown")
            self.assertEqual(claim.value["source_count"], 1)
            self.assertEqual(claim.value["profile_count"], 1)
            self.assertFalse(claim.value["whole_image_exact"])
            self.assertEqual(snapshot.oracle_results, ())
            self.assertIn(
                "whole-build-claim-awaits-replay",
                {diagnostic.code for diagnostic in snapshot.diagnostics},
            )

    def test_vc8_import_preserves_remote_chunks_without_exact_credit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_windows(root, vc8=True)
            snapshot = inspect_repository(root)
            function = next(
                item for item in snapshot.subjects if item.id.endswith("function:00401000")
            )
            self.assertEqual(
                [extent.role for extent in function.extents],
                [ExtentRole.PRIMARY, ExtentRole.OWNED_CHUNK],
            )
            self.assertEqual(metric(snapshot, "inventory.authored-bytes"), 20)
            self.assertEqual(metric(snapshot, "inventory.remote-authored-bytes"), 4)
            self.assertEqual(metric(snapshot, "exact.bytes"), 16)
            self.assertEqual(kit_for_snapshot(snapshot).toolchain.id, "msvc8-ltcg")

    def test_ownership_target_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_windows(root, vc8=True, bad_owner_target=True)
            with self.assertRaisesRegex(AdapterError, "target SHA-256 mismatch"):
                inspect_repository(root)

    def test_snapshot_serialization_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_windows(root)
            first = json.dumps(inspect_repository(root).to_dict(), sort_keys=True)
            second = json.dumps(inspect_repository(root).to_dict(), sort_keys=True)
            self.assertEqual(first, second)

    def test_reader_rejects_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            external = Path(outside) / "secret"
            external.write_text("outside", encoding="utf-8")
            (root / "escaped").symlink_to(external)
            with self.assertRaisesRegex(AdapterError, "escapes repository root"):
                RepositoryReader(root).path("escaped")


if __name__ == "__main__":
    unittest.main()
