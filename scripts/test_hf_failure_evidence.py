#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Offline CLI regressions: a refused admission must retain honest evidence."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import unittest.mock as mock
import urllib.error

SCRIPT = Path(__file__).with_name('verify-hf-ownership.py')
spec = importlib.util.spec_from_file_location('lyte_ownership_failure_test', SCRIPT)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class FailureEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'source'
        self.governance = self.root / 'governance'
        self.publisher = self.root / 'publisher'
        self.output = self.root / 'evidence' / 'result.json'
        self.failure_output = self.root / 'evidence' / 'failure.json'
        self.argv = [str(SCRIPT), '--source', str(self.source),
                     '--governance', str(self.governance),
                     '--publisher', str(self.publisher), '--output', str(self.output),
                     '--failure-output', str(self.failure_output)]
        self.put(self.governance / 'estate/alignment.v1.json', '{}')
        self.put(self.source / 'README.md', 'Synthetic test presentation')
        self.put(self.source / '.github/workflows/hf-deploy.yml', 'Synthetic test caller')
        self.put(self.publisher / verifier.PUBLISHER_PATH, "SOURCE_REVISION = '" + 'a' * 40 + "'\n")
        self.put(self.publisher / verifier.ENTRYPOINT_PATH, '# synthetic unadmitted entrypoint\n')
        for path in verifier.DYNAMIC_DEPENDENCY_BLOBS:
            self.put(self.publisher / path, '# synthetic unadmitted dependency\n')

    @staticmethod
    def put(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def invoke(self):
        with mock.patch.object(sys, 'argv', self.argv), contextlib.redirect_stdout(io.StringIO()):
            return verifier.main()

    def receipt(self):
        return json.loads(self.failure_output.read_text(encoding='utf-8'))

    def assert_blocked(self, stage):
        result = self.receipt()
        self.assertEqual(result['schema'], 'szl.lyte.canonical-delegation-failure/v1')
        self.assertEqual(result['state'], 'BLOCKED')
        self.assertEqual(result['failure']['stage'], stage)
        self.assertIs(result['source_authority_verified'], False)
        self.assertIs(result['provider_writes'], False)
        self.assertIs(result['provider_credentials_local'], False)
        self.assertIs(result['runtime_observed'], False)
        self.assertFalse(self.output.exists())
        return result

    def test_actual_blob_refusal_remains_an_exception_and_retains_observed_hashes(self):
        with mock.patch.object(verifier, 'revision') as checkout, \
             mock.patch.object(verifier, 'read_source_evidence') as evidence, \
             mock.patch.object(verifier, 'github_json') as network, \
             mock.patch.object(subprocess, 'check_output') as process:
            with self.assertRaises(verifier.ContractError):
                self.invoke()
        for effect in (checkout, evidence, network, process):
            effect.assert_not_called()
        result = self.assert_blocked('publisher_closure')
        self.assertNotIn('checkout_revisions', result)
        actual = (self.publisher / verifier.WORKFLOW_PATH).read_bytes()
        expected_blob = hashlib.sha1(b'blob ' + str(len(actual)).encode() + b'\0' + actual).hexdigest()
        self.assertEqual(result['publisher_dependency_blobs'][verifier.WORKFLOW_PATH], expected_blob)
        self.assertNotEqual(expected_blob, verifier.DYNAMIC_DEPENDENCY_BLOBS[verifier.WORKFLOW_PATH])
        self.assertEqual(result['input_sha256']['workflow'], hashlib.sha256(actual).hexdigest())

    def test_missing_input_keeps_failure_without_claiming_checkout_identity(self):
        (self.source / 'README.md').unlink()
        with mock.patch.object(verifier, 'revision', side_effect=verifier.ContractError('unbound')):
            with self.assertRaises(FileNotFoundError):
                self.invoke()
        result = self.assert_blocked('read_inputs')
        self.assertNotIn('checkout_revisions', result)
        self.assertNotIn('readme', result['input_sha256'])
        self.assertIn('alignment', result['input_sha256'])

    def test_original_exception_text_does_not_enter_public_failure_receipt(self):
        self.put(self.publisher / verifier.PUBLISHER_PATH, '# dynamic publisher\n')
        error = RuntimeError('SYNTHETIC_SECRET_MUST_NOT_BE_RETAINED')
        with mock.patch.object(verifier, 'validate_publisher_closure', return_value={}), \
             mock.patch.object(verifier, 'read_source_evidence', side_effect=error), \
             mock.patch.object(verifier, 'revision', return_value='c' * 40):
            with self.assertRaises(RuntimeError) as raised:
                self.invoke()
        self.assertIs(raised.exception, error)
        self.assert_blocked('backend_source_evidence')
        self.assertNotIn('SYNTHETIC_SECRET', self.failure_output.read_text(encoding='utf-8'))

    def test_authenticated_github_request_uses_fixed_read_only_headers(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'{"ok": true}'
        opener = mock.Mock()
        opener.open.return_value = response
        token = 'synthetic-actions-token'
        with mock.patch.dict(verifier.os.environ, {'GITHUB_TOKEN': token}, clear=True), \
             mock.patch.object(verifier.urllib.request, 'build_opener', return_value=opener):
            self.assertEqual(
                verifier.github_json('/repos/szl-holdings/lyte-services/commits/main'),
                {'ok': True})
        request = opener.open.call_args.args[0]
        headers = {key.lower(): value for key, value in request.header_items()}
        self.assertEqual(request.full_url,
                         'https://api.github.com/repos/szl-holdings/lyte-services/commits/main')
        self.assertEqual(headers['authorization'], f'Bearer {token}')
        self.assertEqual(headers['accept'], 'application/vnd.github+json')
        self.assertEqual(headers['x-github-api-version'], '2022-11-28')
        self.assertEqual(headers['user-agent'], 'SZL-Lyte-ReadOnly-Authority/4')
        self.assertEqual(opener.open.call_args.kwargs, {'timeout': 30})

    def test_missing_github_token_fails_before_network_and_retains_blocked_evidence(self):
        self.put(self.publisher / verifier.PUBLISHER_PATH, '# dynamic publisher\n')
        with mock.patch.object(verifier, 'validate_publisher_closure', return_value={}), \
             mock.patch.dict(verifier.os.environ, {}, clear=True), \
             mock.patch.object(verifier.urllib.request, 'build_opener') as opener:
            with self.assertRaisesRegex(
                    verifier.ContractError, 'token is unavailable or malformed'):
                self.invoke()
        opener.assert_not_called()
        self.assert_blocked('backend_source_evidence')

    def test_github_rate_limit_and_refusal_fail_closed_with_blocked_evidence(self):
        self.put(self.publisher / verifier.PUBLISHER_PATH, '# dynamic publisher\n')
        token = 'synthetic-actions-token'
        for status in (403, 429):
            opener = mock.Mock()
            opener.open.side_effect = urllib.error.HTTPError(
                'https://api.github.com/fixed', status, 'synthetic refusal', {}, None)
            with self.subTest(status=status), \
                 mock.patch.object(verifier, 'validate_publisher_closure', return_value={}), \
                 mock.patch.dict(verifier.os.environ, {'GITHUB_TOKEN': token}, clear=True), \
                 mock.patch.object(verifier.urllib.request, 'build_opener', return_value=opener):
                with self.assertRaisesRegex(
                        verifier.ContractError, 'rate limited or refused'):
                    self.invoke()
                result = self.assert_blocked('backend_source_evidence')
                self.assertNotIn(token, self.failure_output.read_text(encoding='utf-8'))
                self.assertEqual(result['failure']['code'],
                                 'SOURCE_AUTHORITY_VERIFICATION_FAILED')

    def test_invalid_alignment_json_is_not_relabelled_as_success(self):
        self.put(self.governance / 'estate/alignment.v1.json', '{broken')
        with mock.patch.object(verifier, 'validate_publisher_closure', return_value={}), \
             mock.patch.object(verifier, 'revision', return_value='d' * 40):
            with self.assertRaises(verifier.ContractError):
                self.invoke()
        self.assert_blocked('alignment_manifest')

    def test_failure_to_write_receipt_does_not_replace_original_refusal(self):
        error = verifier.ContractError('original refusal')
        stderr = io.StringIO()
        with mock.patch.object(verifier, 'validate_publisher_closure', side_effect=error), \
             mock.patch.object(verifier, 'revision', return_value='e' * 40), \
             mock.patch.object(Path, 'write_text', side_effect=OSError('synthetic disk error')), \
             contextlib.redirect_stderr(stderr):
            with self.assertRaises(verifier.ContractError) as raised:
                self.invoke()
        self.assertIs(raised.exception, error)
        self.assertIn('Failure evidence could not be retained', stderr.getvalue())

    def test_success_preserves_existing_receipt_schema_and_exit_status(self):
        admitted = {'schema': 'szl.lyte.canonical-delegation/v2', 'state': 'DELEGATED',
                    'backend_source_revision': 'a' * 40, 'runtime_observed': False}
        with mock.patch.object(verifier, 'validate_publisher_closure', return_value={'synthetic': True}), \
             mock.patch.object(verifier, 'validate', return_value=admitted.copy()), \
             mock.patch.object(verifier, 'revision', return_value='f' * 40):
            self.assertEqual(self.invoke(), 0)
        result = json.loads(self.output.read_text(encoding='utf-8'))
        self.assertFalse(self.failure_output.exists())
        self.assertEqual(result['schema'], admitted['schema'])
        self.assertEqual(result['state'], 'DELEGATED')
        self.assertNotIn('failure', result)
        self.assertEqual(result['publisher_dependency_blobs'], verifier.DYNAMIC_DEPENDENCY_BLOBS)

    def test_real_cli_missing_input_exits_nonzero_and_retains_failure(self):
        # This child never reaches network lookup or publisher execution.
        (self.source / 'README.md').unlink()
        result = subprocess.run([sys.executable, '-I', *self.argv],
                                capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assert_blocked('read_inputs')

    def test_default_cli_preserves_no_receipt_on_refusal(self):
        self.argv = self.argv[:-2]
        with self.assertRaises(verifier.ContractError):
            self.invoke()
        self.assertFalse(self.output.exists())
        self.assertFalse(self.failure_output.exists())

    def test_failure_receipt_cannot_use_admitted_output_path(self):
        self.argv[-1] = str(self.output.parent / '.' / self.output.name)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            self.invoke()
        self.assertEqual(raised.exception.code, 2)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
