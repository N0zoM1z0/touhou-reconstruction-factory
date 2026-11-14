"""Isolation and process lifecycle checks for the shared runtime entrypoint."""
import importlib.util
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('shared_runtime', ROOT / 'runtime/run.py')
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


class SharedRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='factory runtime ')
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name)
        self.tools = self.base / 'tools'
        self.patch = patch.object(runtime, 'TOOLS', self.tools)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        for name, executable in [('ghidra-test', 'support/analyzeHeadless'),
                                 ('jdk-test', 'bin/java'), ('wine', 'bin/wine'),
                                 ('wine', 'bin/winepath'), ('wine', 'bin/wineserver')]:
            path = self.tools / name / executable
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('#!/bin/sh\nexit 0\n')
            path.chmod(0o755)
        self.a = self.repository('alpha')
        self.b = self.repository('beta')

    def repository(self, name):
        root = self.base / name
        (root / '.tools').mkdir(parents=True)
        (root / runtime.SPEC).write_text(json.dumps(dict(schema_version=1,
            repository_id=name, owner_token=name + '-unique', ghidra='ghidra-test',
            jdk='jdk-test', wine_prefix='.tools/prefix', wine_arch='win32')))
        return root

    def test_java_state_is_repository_owned_and_ambient_paths_are_overridden(self):
        with patch.dict(os.environ, {'JAVA_HOME': '/wrong', 'DISPLAY': ':9',
                                    'GHIDRA_HEADLESS_JAVA_OPTIONS': '-Duser.home=/other -XX:ActiveProcessorCount=1'}):
            _, a, meta_a = runtime.prepare(self.a, 'ghidra')
            _, b, meta_b = runtime.prepare(self.b, 'ghidra')
        self.assertNotEqual(meta_a['cache'], meta_b['cache'])
        self.assertEqual(a['JAVA_HOME'], str(self.tools / 'jdk-test'))
        self.assertEqual(a['DISPLAY'], '')
        self.assertIn(str(self.a), a['JAVA_TOOL_OPTIONS'])
        self.assertNotIn('/other', a['GHIDRA_HEADLESS_JAVA_OPTIONS'])
        self.assertNotEqual(a['TMPDIR'], b['TMPDIR'])

    def test_wine_ignores_foreign_ambient_prefix_and_removes_recursive_path(self):
        with patch.dict(os.environ, {'WINEPREFIX':str(self.b / '.tools/prefix'),
              'TMPDIR':'/unusable', 'WINESERVER':'/wrong',
              'PATH':str(self.a / '.tools/factory-bin') + ':/usr/bin'}):
            _, environment, metadata = runtime.prepare(self.a, 'wine')
        self.assertEqual(metadata['prefix'], str(self.a / '.tools/prefix'))
        self.assertNotIn('TMPDIR', environment)
        self.assertNotIn('WINESERVER', environment)
        self.assertEqual(environment['PATH'], '/usr/bin')

    def test_explicit_foreign_prefix_and_symlink_are_rejected(self):
        for path in (self.b / '.tools/prefix',):
            with self.assertRaises(ValueError):
                runtime.prepare(self.a, 'wine', path)
        (self.a / 'foreign').symlink_to(self.b, target_is_directory=True)
        with self.assertRaises(ValueError):
            runtime.prepare(self.a, 'wine', self.a / 'foreign/prefix')

    def test_owner_marker_rejects_reassigned_prefix(self):
        runtime.prepare(self.a, 'wine')
        spec = json.loads((self.b / runtime.SPEC).read_text())
        spec['wine_prefix'] = str(self.a / '.tools/prefix')
        (self.b / runtime.SPEC).write_text(json.dumps(spec))
        with self.assertRaisesRegex(ValueError, 'another repository'):
            runtime.prepare(self.b, 'wine')

    def test_describe_does_not_initialize_a_prefix(self):
        runtime.prepare(self.a, 'wine', describe=True)
        self.assertFalse((self.a / '.tools/prefix').exists())

    def test_concurrent_first_use_claims_the_prefix_consistently(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: runtime.prepare(self.a, 'wine'), range(32)))
        self.assertEqual({item[2]['prefix'] for item in results}, {str(self.a / '.tools/prefix')})
        owner = json.loads((self.a / '.tools/prefix/.factory-runtime-owner.json').read_text())
        self.assertEqual(owner['owner_token'], 'alpha-unique')

    def test_local_probe_prefix_is_allowed(self):
        _, _, metadata = runtime.prepare(self.a, 'wine', Path('.analysis/probe-prefix'))
        self.assertEqual(metadata['prefix'], str(self.a / '.analysis/probe-prefix'))

    def test_distribution_names_cannot_escape_store(self):
        for name in ('..', '/tmp', 'something/else'):
            with self.assertRaises(ValueError):
                runtime.installation(name)

    def test_explicit_ghidra_version_does_not_rebind_repository_defaults(self):
        other = self.tools / 'ghidra-other/support/analyzeHeadless'
        other.parent.mkdir(parents=True)
        other.write_text('#!/bin/sh\nexit 0\n')
        executable, _, metadata = runtime.prepare(self.a, 'ghidra', ghidra_version='ghidra-other')
        self.assertEqual(executable, other)
        self.assertEqual(metadata['repository_id'], 'alpha')
        self.assertEqual(json.loads((self.a / runtime.SPEC).read_text())['ghidra'], 'ghidra-test')

    @unittest.skipUnless(hasattr(os, 'sched_getaffinity'), 'CPU affinity is unavailable')
    def test_tools_preserve_the_callers_cpu_affinity(self):
        allowed = os.sched_getaffinity(0)
        if len(allowed) < 2:
            self.skipTest('requires at least two allowed CPUs')
        factory = self.base / 'factory'
        (factory / 'runtime').mkdir(parents=True)
        (factory / '.factory').mkdir()
        (factory / '.factory/shared-tools').symlink_to(self.tools)
        script = factory / 'runtime/run.py'
        script.write_text((ROOT / 'runtime/run.py').read_text())
        for executable in self.tools.rglob('*'):
            if executable.is_file():
                executable.write_text(f'#!{sys.executable}\nimport json,os\nprint(json.dumps(sorted(os.sched_getaffinity(0))))\n')
        for cpus in (allowed, {max(allowed)}):
            for tool in ('wine', 'winepath', 'wineserver', 'java', 'ghidra'):
                with self.subTest(cpus=sorted(cpus), tool=tool):
                    result = subprocess.run([sys.executable, str(script), '--repository', str(self.a), tool],
                        preexec_fn=lambda: os.sched_setaffinity(0, cpus),
                        capture_output=True, text=True, check=True, timeout=5)
                    self.assertEqual(json.loads(result.stdout), sorted(cpus))

    def test_wine_lock_serializes_one_repository_but_not_other_repositories(self):
        # Run an isolated copy so the CLI uses this test's fake store.
        factory = self.base / 'factory'
        (factory / 'runtime').mkdir(parents=True)
        (factory / '.factory').mkdir()
        (factory / '.factory/shared-tools').symlink_to(self.tools)
        script = factory / 'runtime/run.py'
        script.write_text((ROOT / 'runtime/run.py').read_text())
        wine = self.tools / 'wine/bin/wine'
        wine.write_text('#!/usr/bin/env python3\nimport time,sys\nprint("started",flush=True)\ntime.sleep(float(sys.argv[1]))\n')
        def launch(repo, delay):
            child = subprocess.Popen([sys.executable, str(script), '--repository', str(repo),
                'wine', '--', str(delay)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.addCleanup(lambda: child.poll() is None and child.kill())
            return child
        first = launch(self.a, 30)
        self.assertEqual(first.stdout.readline().strip(), 'started')
        queued = launch(self.a, 0)
        other = launch(self.b, 0)
        self.assertEqual(other.communicate(timeout=5)[0].strip(), 'started')
        control = subprocess.run([sys.executable, str(script), '--repository', str(self.a),
                                  'wineserver', '--', '-k'], timeout=5)
        self.assertEqual(control.returncode, 0)
        self.assertIsNone(first.poll())
        time.sleep(0.1)
        self.assertIsNone(queued.poll())
        first.terminate()
        first.communicate(timeout=5)
        self.assertEqual(first.returncode, 143)
        self.assertEqual(queued.communicate(timeout=5)[0].strip(), 'started')
        self.assertEqual(queued.returncode, 0)


if __name__ == '__main__':
    unittest.main()
