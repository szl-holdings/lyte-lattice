#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Offline authority tests: no credentials, provider writes or network."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

path = Path(__file__).with_name('verify-hf-ownership.py')
spec = importlib.util.spec_from_file_location('lyte_hf_owner', path)
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)
REQUIRED_CHECKS = (
    'python-compile', 'lint', 'unit', 'api-contract', 'release-gates',
    'database-migrations', 'connector-contract', 'truth-and-governance',
    'security-scan', 'secret-scan', 'frontend-static-contract', 'accessibility',
    'responsive-overflow', 'bundle-budget', 'container-build', 'container-smoke',
    'source-binding',
)

class OwnershipContract(unittest.TestCase):
    def setUp(self):
        self.alignment = {'schema': 'szl.estate.alignment/v1', 'public_bodies': [{
            'id': 'lyte', 'backend_source': 'szl-holdings/lyte-services',
            'presentation_source': 'szl-holdings/lyte-lattice', 'hub_surface': 'SZLHOLDINGS/lyte'}],
            'hub_alias_policy': {'duplicate_authority_spaces_forbidden': True, 'canonical_public_space_slugs': ['lyte']}}
        self.publisher = '\n'.join([
            'SOURCE_REPOSITORY = "szl-holdings/lyte-services"',
            'SOURCE_REVISION = "' + 'a' * 40 + '"',
            'HF_REPOSITORY = "SZLHOLDINGS/lyte"',
            'ORIGIN = "https://szlholdings-lyte.hf.space"'])
        self.entry = 'LYTE_SOURCE_REVISION = "' + 'a' * 40 + '"\nSOURCE_OWNED_FLAGSHIP_SLUGS = ("lyte",)\nLYTE_IMPL = HERE / "hf_publish_lyte_enterprise.py"'
        self.workflow = 'run: python scripts/hf_publish_vertical_flagships_v4.py'
        self.caller = 'permissions:\n  contents: read\n'
        self.readme = '---\nshort_description: "Lyte package: canonical runtime"\n---\n'
    def run_contract(self):
        return owner.validate(self.alignment, self.publisher, self.entry, self.workflow, self.caller, self.readme)
    def test_current_authority_is_delegated_without_uptime_or_write_claim(self):
        result = self.run_contract()
        self.assertEqual(result['state'], 'DELEGATED')
        self.assertEqual(result['hub_surface'], 'SZLHOLDINGS/lyte')
        self.assertEqual(result['publisher_repository'], 'szl-holdings/a11oy')
        for key in ('provider_writes', 'provider_credentials_local', 'runtime_observed', 'retired_space_recreated'):
            self.assertIs(result[key], False)
    def test_retired_target_rejected(self):
        self.publisher = self.publisher.replace('SZLHOLDINGS/lyte"', 'SZLHOLDINGS/lyte-lattice"')
        with self.assertRaises(owner.ContractError): self.run_contract()
    def test_presentation_must_not_be_the_runtime_source(self):
        self.alignment['public_bodies'][0]['backend_source'] = 'szl-holdings/lyte-lattice'
        with self.assertRaises(owner.ContractError): self.run_contract()
    def test_moving_reference_rejected(self):
        self.publisher = self.publisher.replace('a' * 40, 'main')
        with self.assertRaises(owner.ContractError): self.run_contract()
    def test_mismatched_source_pins_rejected(self):
        self.entry = self.entry.replace('a' * 40, 'b' * 40)
        with self.assertRaises(owner.ContractError): self.run_contract()
    def test_generic_shell_must_not_replace_the_source_owned_runtime(self):
        self.entry = self.entry.replace('("lyte",)', '()')
        with self.assertRaises(owner.ContractError): self.run_contract()
    def test_missing_or_duplicate_body_rejected(self):
        row = self.alignment['public_bodies'][0]
        for rows in ([], [row, copy.deepcopy(row)]):
            self.alignment['public_bodies'] = rows
            with self.assertRaises(owner.ContractError): self.run_contract()
    def test_missing_entrypoint_rejected(self):
        self.workflow = 'run: echo not a publisher'
        with self.assertRaises(owner.ContractError): self.run_contract()
    def test_duplicate_authority_policy_is_required(self):
        self.alignment['hub_alias_policy']['duplicate_authority_spaces_forbidden'] = False
        with self.assertRaises(owner.ContractError): self.run_contract()
    def test_noncanonical_origin_rejected(self):
        self.publisher = self.publisher.replace('szlholdings-lyte.hf.space', 'example.invalid')
        with self.assertRaises(owner.ContractError): self.run_contract()
    def test_invalid_card_metadata_is_not_exempted_by_consolidation(self):
        for text in ('no front matter', '---\nmissing closing delimiter',
                     '---\nshort_description: ""\n---\n',
                     '---\nshort_description: ' + 'x' * 61 + '\n---\n',
                     '---\nshort_description: key: unquoted\n---\n',
                     '---\nshort_description: first\nshort_description: second\n---\n'):
            with self.subTest(text=text), self.assertRaises(owner.ContractError):
                owner.validate_card(text)
    def test_local_secrets_and_provider_writes_remain_forbidden(self):
        for addition in ('\nenv:\n  HF_TOKEN: not-a-token\n',
                         '\njobs:\n  permissions:\n    contents: write\n',
                         '\nrun: ${{ secrets.HF_ORG_TOKEN }}\n',
                         '\nuses: szl-holdings/.github/.github/workflows/reusable-hf-deploy.yml@' + 'a'*40,
                         '\nrun: api.restart_space(repo_id="SZLHOLDINGS/lyte")\n'):
            with self.subTest(addition=addition), self.assertRaises(owner.ContractError):
                owner.validate_caller(self.caller + addition)
    def test_explicit_read_only_permissions_are_required(self):
        for text in ('', 'permissions: write-all', 'permissions:\n  contents: write\n'):
            with self.subTest(text=text), self.assertRaises(owner.ContractError):
                owner.validate_caller(text)

class DynamicOwnershipContract(OwnershipContract):
    """Fixture hashes test dispatch; production hashes bind reviewed real blobs."""
    def setUp(self):
        super().setUp()
        self.publisher = self.publisher.replace('SOURCE_REVISION = "' + 'a' * 40 + '"',
            'SOURCE_VARIABLE = "LYTE_SOURCE_REVISION"\nSOURCE_REQUIRED_CHECKS = ' + repr(REQUIRED_CHECKS))
        self.entry = self.entry.replace('LYTE_SOURCE_REVISION = "' + 'a' * 40 + '"\n', '')
        self.admitted_publisher = owner.git_blob(self.publisher)
        self.admitted_entrypoint = owner.git_blob(self.entry)
        self.head = {'sha': 'a' * 40, 'commit': {'verification': {'verified': True}}}
        self.checks = {'total_count': len(REQUIRED_CHECKS), 'check_runs': [
            {'name': name, 'head_sha': 'a' * 40, 'status': 'completed',
             'conclusion': 'success', 'app': {'slug': 'github-actions'}}
            for name in REQUIRED_CHECKS]}
    def run_contract(self):
        with patch.object(owner, 'DYNAMIC_PUBLISHER_BLOB', self.admitted_publisher), \
                patch.object(owner, 'DYNAMIC_ENTRYPOINT_BLOB', self.admitted_entrypoint):
            return owner.validate(self.alignment, self.publisher, self.entry, self.workflow,
                self.caller, self.readme, source_head=self.head, source_checks=self.checks)
    def test_signed_checked_tip_is_still_an_immutable_source_authority_receipt(self):
        result = self.run_contract()
        self.assertEqual(result['backend_source_revision'], 'a' * 40)
        self.assertEqual(result['source_revision_policy'], 'reviewed-verified-current-tip')
        self.assertIs(result['backend_signature_verified'], True)
        self.assertEqual(result['required_source_checks'], list(REQUIRED_CHECKS))
        self.assertIs(result['backend_tip_reverified'], False)
        self.assertIs(result['runtime_observed'], False)
        self.assertIs(result['provider_writes'], False)
    def test_moving_reference_rejected(self):
        for revision in ('main', 'HEAD', 'v4.0.0', '0' * 40, 'A' * 40, 'a' * 39):
            with self.subTest(revision=revision), self.assertRaises(owner.ContractError):
                self.head['sha'] = revision
                self.run_contract()
    def test_mismatched_source_pins_rejected(self):
        self.checks['check_runs'][0]['head_sha'] = 'b' * 40
        with self.assertRaises(owner.ContractError): self.run_contract()
    def test_unsigned_or_ambiguous_signature_is_rejected(self):
        for signature in (False, None, 1, 'true'):
            with self.subTest(signature=signature), self.assertRaises(owner.ContractError):
                self.head['commit']['verification']['verified'] = signature
                self.run_contract()
    def test_every_exact_head_source_gate_is_required(self):
        original = copy.deepcopy(self.checks)
        for name in REQUIRED_CHECKS:
            for mutation in ('missing', 'failure', 'pending', 'skipped', 'wrong-head', 'wrong-app', 'conflicting-duplicate'):
                with self.subTest(name=name, mutation=mutation), self.assertRaises(owner.ContractError):
                    self.checks = copy.deepcopy(original)
                    row = next(row for row in self.checks['check_runs'] if row['name'] == name)
                    if mutation == 'missing': self.checks['check_runs'].remove(row)
                    elif mutation == 'failure': row['conclusion'] = 'failure'
                    elif mutation == 'pending': row['status'] = 'in_progress'
                    elif mutation == 'skipped': row['conclusion'] = 'skipped'
                    elif mutation == 'wrong-head': row['head_sha'] = 'b' * 40
                    elif mutation == 'wrong-app': row['app']['slug'] = 'untrusted-check'
                    else:
                        duplicate = copy.deepcopy(row)
                        duplicate['conclusion'] = 'failure'
                        self.checks['check_runs'].append(duplicate)
                    self.checks['total_count'] = len(self.checks['check_runs'])
                    self.run_contract()
    def test_partial_check_evidence_is_rejected(self):
        for count in (100, None, True, '17'):
            with self.subTest(count=count), self.assertRaises(owner.ContractError):
                self.checks['total_count'] = count
                self.run_contract()
    def test_changed_publisher_or_entrypoint_fails_closed(self):
        original = self.publisher
        for addition in ('\n# unreviewed publisher change\n', '\nSOURCE_VARIABLE = "OTHER"\n'):
            with self.subTest(addition=addition), self.assertRaises(owner.ContractError):
                self.publisher = original + addition
                self.run_contract()
        self.publisher = original
        self.entry += '\n# unreviewed entrypoint change\n'
        with self.assertRaises(owner.ContractError): self.run_contract()
    def test_declaring_a_resolver_without_reviewed_bytes_is_rejected(self):
        with self.assertRaises(owner.ContractError):
            owner.validate(self.alignment, self.publisher, self.entry, self.workflow,
                self.caller, self.readme, source_head=self.head, source_checks=self.checks)
    def test_source_evidence_is_required_even_for_reviewed_dynamic_bytes(self):
        with patch.object(owner, 'DYNAMIC_PUBLISHER_BLOB', self.admitted_publisher), \
                patch.object(owner, 'DYNAMIC_ENTRYPOINT_BLOB', self.admitted_entrypoint), \
                self.assertRaises(owner.ContractError):
            owner.validate(self.alignment, self.publisher, self.entry, self.workflow,
                self.caller, self.readme)
    def test_unsigned_or_moved_tip_is_rejected_by_final_recheck(self):
        with patch.object(owner, 'github_json', return_value=self.head):
            owner.require_current_source('a' * 40)
            self.head['sha'] = 'b' * 40
            with self.assertRaises(owner.ContractError): owner.require_current_source('a' * 40)
            self.head['sha'] = 'a' * 40
            self.head['commit']['verification']['verified'] = False
            with self.assertRaises(owner.ContractError): owner.require_current_source('a' * 40)
    def test_backend_evidence_reader_uses_only_fixed_read_routes(self):
        for path in ('/repos/other/repo/commits/main', '/repos/szl-holdings/lyte-services/commits/HEAD',
                     '/repos/szl-holdings/lyte-services/issues', 'https://example.invalid'):
            with self.subTest(path=path), self.assertRaises(owner.ContractError):
                owner.github_json(path)
    def test_pagination_requires_complete_unchanged_count(self):
        first = {'check_runs': self.checks['check_runs'], 'total_count': 18}
        last = {'check_runs': [copy.deepcopy(self.checks['check_runs'][0])], 'total_count': 18}
        with patch.object(owner, 'github_json', side_effect=[self.head, first, last]) as reader:
            head, checks = owner.read_source_evidence()
            self.assertEqual(owner.admit_source_checks(head, checks), 'a' * 40)
            self.assertIn('page=2', reader.call_args.args[0])
        for bad in ({'check_runs': [], 'total_count': 18},
                    {'check_runs': last['check_runs'], 'total_count': 19},
                    {'check_runs': [], 'total_count': 1001}):
            with self.subTest(bad=bad), patch.object(owner, 'github_json', side_effect=[self.head, first, bad]), \
                    self.assertRaises(owner.ContractError):
                owner.read_source_evidence()

class PublisherIsolation(unittest.TestCase):
    def test_publisher_text_is_parsed_without_execution(self):
        self.assertEqual(owner.constants('SOURCE_REVISION = "' + 'a' * 40 + '"\nraise RuntimeError("must never run")')['SOURCE_REVISION'], 'a' * 40)

if __name__ == '__main__':
    unittest.main(verbosity=2)
