#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Offline authority tests: no credentials, provider writes or network."""
import copy
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).with_name('verify-hf-ownership.py')
spec = importlib.util.spec_from_file_location('lyte_hf_owner', path)
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)

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

if __name__ == '__main__':
    unittest.main(verbosity=2)
