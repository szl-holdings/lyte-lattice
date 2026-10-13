#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Offline authority tests: no credentials, provider writes or network."""
import contextlib
import copy
import importlib.util
import json
from pathlib import Path
import sys
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

# Independent inventory of the reviewed a11oy estate-route execution closure.
# Literal on purpose: it is never derived from the production registry it checks.
EXPECTED_PUBLISHER = 'scripts/hf_publish_lyte_enterprise.py'
EXPECTED_ENTRYPOINT = 'scripts/hf_publish_vertical_flagships_v4.py'
EXPECTED_WORKFLOW = '.github/workflows/hf-sync.yml'
EXPECTED_DEPENDENCIES = (
    '.github/workflows/hf-sync.yml',
    'scripts/szl_release_guard.py',
    'scripts/lyte_enterprise_live_contract.py',
    'scripts/hf_existing_space_guard.py',
    'scripts/hf_exact_main_ownership.py',
    'scripts/estate_repair_dispatch.py',
    'scripts/estate_child_completion.py',
    'scripts/hf_publish_vertical_flagships_v4_impl.py',
    'scripts/_hf_publish_vertical_flagships_v4_impl_base.py',
    'scripts/hf_finance_read_proxy.py',
    'scripts/hf_flagship_runtime_contract.py',
    'scripts/hf_finance_workspace.py',
    'scripts/hf_finance_research_workspace.py',
    'scripts/hf_finance_signed_workspace.py',
    'scripts/hf_finance_functional_gate.py',
    'scripts/hf_finance_projection_manifest.py',
    'scripts/hf_publish_vertical_services_intelligence_v4.py',
    'scripts/hf_publish_vertical_services_frontier_v3.py',
    'scripts/hf_publish_vertical_services.py',
)
EXPECTED_WORKFLOW_ROOTS = (
    'scripts/estate_child_completion.py',
    'scripts/estate_repair_dispatch.py',
    'scripts/hf_exact_main_ownership.py',
    'scripts/hf_publish_vertical_flagships_v4.py',
)
EXPECTED_CODE = tuple(sorted({EXPECTED_PUBLISHER, EXPECTED_ENTRYPOINT,
                              *EXPECTED_DEPENDENCIES} - {EXPECTED_WORKFLOW}))
HEADER = 'from pathlib import Path\nHERE = Path(__file__).resolve().parent\n'


def sibling(name):
    return f'Path(__file__).with_name("{name}")'


def synthetic_sources():
    """Inert stand-ins with the reviewed reference shapes; never real publisher code."""
    sources = {path: f'# inert reviewed fixture: {path}\n'
               for path in EXPECTED_DEPENDENCIES if path != EXPECTED_WORKFLOW}
    sources['scripts/hf_publish_vertical_flagships_v4_impl.py'] = (
        'import importlib.util\nfrom pathlib import Path\n'
        f'BASE = {sibling("_hf_publish_vertical_flagships_v4_impl_base.py")}\n'
        + ''.join(f'_spec = importlib.util.spec_from_file_location("m", {sibling(name)})\n'
                  for name in ('hf_finance_read_proxy.py', 'hf_flagship_runtime_contract.py',
                               'hf_finance_workspace.py', 'hf_finance_functional_gate.py',
                               'hf_finance_projection_manifest.py')))
    sources['scripts/_hf_publish_vertical_flagships_v4_impl_base.py'] = (
        'from pathlib import Path\nfrom huggingface_hub import HfApi\n'
        'ROOT = Path(__file__).resolve().parents[1]\n'
        'BUNDLE = ROOT / "deployments" / "fixture"\n'
        'SPACE_FILES = ("app.py", "Dockerfile")\n'
        'def page():\n    return (BUNDLE / "index.html").read_text()\n')
    sources['scripts/hf_finance_workspace.py'] = (
        'import importlib.util\nfrom pathlib import Path\n'
        f'_a = importlib.util.spec_from_file_location("a", {sibling("hf_finance_research_workspace.py")})\n'
        f'_b = importlib.util.spec_from_file_location("b", {sibling("hf_finance_signed_workspace.py")})\n')
    sources['scripts/hf_finance_functional_gate.py'] = (
        'import importlib.util\nfrom pathlib import Path\n'
        'def projection():\n'
        f'    return importlib.util.spec_from_file_location("p", {sibling("hf_finance_read_proxy.py")})\n')
    sources['scripts/hf_publish_vertical_services_intelligence_v4.py'] = (
        HEADER + 'V3_IMPL = HERE / "hf_publish_vertical_services_frontier_v3.py"\n')
    sources['scripts/hf_publish_vertical_services_frontier_v3.py'] = (
        'import importlib.util\n' + HEADER + 'BASE_IMPL = HERE / "hf_publish_vertical_services.py"\n'
        'def load():\n    return importlib.util.spec_from_file_location("b", BASE_IMPL)\n')
    sources['scripts/hf_publish_vertical_services.py'] = (
        'import subprocess\nimport sys\nfrom pathlib import Path\n'
        'def deploy(td):\n'
        '    controller = Path(td) / "hf_deploy_from_dockerfile.py"\n'
        '    subprocess.run([sys.executable, "-m", "pip", "--version"], check=False)\n'
        '    return controller\n')
    return sources


SYNTHETIC_WORKFLOW = '''name: inert synthetic publisher workflow
on: workflow_dispatch
permissions:
  contents: read
env:
  CANONICAL_SPACE: SZLHOLDINGS/a11oy
jobs:
  unrelated:
    runs-on: ubuntu-latest
    steps:
      - run: python -I -B scripts/unrelated_fixture_tool.py
  publish-vertical-flagships:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
      - run: python3 -I -B scripts/hf_exact_main_ownership.py --receipt "$RUNNER_TEMP/owner.json"
      - run: python -I -B scripts/estate_repair_dispatch.py > "$RUNNER_TEMP/plan.json"
      - run: python -I -m pip install "huggingface_hub==1.31.0"
      - run: python -I -B scripts/hf_publish_vertical_flagships_v4.py
      - run: python -I -B scripts/estate_child_completion.py
'''

SYNTHETIC_ENTRYPOINT = '''import importlib.util
import os
from pathlib import Path
HERE = Path(__file__).resolve().parent
SOURCE_OWNED_FLAGSHIP_SLUGS = ("lyte",)
FLAGSHIP_IMPL = HERE / "hf_publish_vertical_flagships_v4_impl.py"
LYTE_IMPL = HERE / "hf_publish_lyte_enterprise.py"
COMBINED_IMPL = HERE / "hf_publish_vertical_services_intelligence_v4.py"
SPACE_GUARD_IMPL = HERE / "hf_existing_space_guard.py"
RELEASE_GUARD_IMPL = HERE / "szl_release_guard.py"
def _load_from_path(name, path):
    return importlib.util.spec_from_file_location(name, path)
def load_module(name, path):
    if path != LYTE_IMPL:
        return _load_from_path(name, path)
    _load_from_path("release_guard", RELEASE_GUARD_IMPL)
    return _load_from_path(name, path)
def run_publisher(name, path, *, finance_only=False):
    return load_module(name, path)
def publish_lyte_only():
    return run_publisher("lyte", LYTE_IMPL)
def main():
    load_module("guard", SPACE_GUARD_IMPL)
    scope = os.environ.get("SZL_FLAGSHIP_SCOPE", "estate")
    if scope == "lyte":
        return publish_lyte_only()
    run_publisher("flagships", FLAGSHIP_IMPL, finance_only=False)
    run_publisher("lyte", LYTE_IMPL)
    return run_publisher("combined", COMBINED_IMPL)
'''


class DynamicOwnershipContract(OwnershipContract):
    """Fixture hashes test dispatch; production hashes bind reviewed real blobs."""
    def setUp(self):
        super().setUp()
        self.publisher = self.publisher.replace('SOURCE_REVISION = "' + 'a' * 40 + '"',
            'SOURCE_VARIABLE = "LYTE_SOURCE_REVISION"\nSOURCE_REQUIRED_CHECKS = ' + repr(REQUIRED_CHECKS))
        self.publisher = ('from pathlib import Path\nfrom szl_release_guard import run_bounded\n'
            + self.publisher + '\nCONTRACT_PATH = Path(__file__).resolve().with_name('
            '"lyte_enterprise_live_contract.py")\ndef controller(td):\n'
            '    return Path(td) / "controller.py"\n'
            'EVIDENCE_DIRECTORY = Path("hf-lyte-release-evidence")\n'
            'def retained(intent):\n    return list(intent.parent.glob("*.json"))\n')
        self.entry = SYNTHETIC_ENTRYPOINT
        self.workflow = SYNTHETIC_WORKFLOW
        self.dependencies = {path: text for path, text in synthetic_sources().items()}
        self.dependencies[EXPECTED_WORKFLOW] = self.workflow
        self.admit()
        self.head = {'sha': 'a' * 40, 'commit': {'verification': {'verified': True}}}
        self.checks = {'total_count': len(REQUIRED_CHECKS), 'check_runs': [
            {'name': name, 'head_sha': 'a' * 40, 'status': 'completed',
             'conclusion': 'success', 'app': {'slug': 'github-actions'}}
            for name in REQUIRED_CHECKS]}
    def admit(self):
        """Admit the current fixture bytes, as a reviewed registry update would."""
        self.admitted_publisher = owner.git_blob(self.publisher)
        self.admitted_entrypoint = owner.git_blob(self.entry)
        self.admitted_dependencies = {path: owner.git_blob(text)
                                      for path, text in self.dependencies.items()}
    def set_workflow(self, text):
        self.workflow = text
        self.dependencies[EXPECTED_WORKFLOW] = text
        self.admit()
    def registry(self):
        return (patch.object(owner, 'DYNAMIC_PUBLISHER_BLOB', self.admitted_publisher),
                patch.object(owner, 'DYNAMIC_ENTRYPOINT_BLOB', self.admitted_entrypoint),
                patch.object(owner, 'DYNAMIC_DEPENDENCY_BLOBS', self.admitted_dependencies))
    def run_contract(self):
        first, second, third = self.registry()
        with first, second, third:
            return owner.validate(self.alignment, self.publisher, self.entry, self.workflow,
                self.caller, self.readme, source_head=self.head, source_checks=self.checks,
                publisher_dependencies=self.dependencies)
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
        original_publisher, original_entry = self.publisher, self.entry
        for name, change in (('publisher', lambda text: text + '\n# unreviewed publisher change\n'),
                             ('publisher', lambda text: text + '\nSOURCE_VARIABLE = "OTHER"\n'),
                             ('publisher', lambda text: text.replace('\n', '\r\n')),
                             ('entrypoint', lambda text: text + '\n# unreviewed entrypoint change\n'),
                             ('entrypoint', lambda text: text.replace('\n', '\r\n'))):
            with self.subTest(name=name), self.assertRaisesRegex(owner.ContractError, 'reviewed exact Git blobs'):
                self.publisher, self.entry = original_publisher, original_entry
                if name == 'publisher': self.publisher = change(self.publisher)
                else: self.entry = change(self.entry)
                self.run_contract()
    def test_declaring_a_resolver_without_reviewed_bytes_is_rejected(self):
        with self.assertRaises(owner.ContractError):
            owner.validate(self.alignment, self.publisher, self.entry, self.workflow,
                self.caller, self.readme, source_head=self.head, source_checks=self.checks,
                publisher_dependencies=self.dependencies)
    def test_every_reviewed_dependency_and_workflow_is_bound(self):
        original = dict(self.dependencies)
        for path in EXPECTED_DEPENDENCIES:
            for mutation in ('changed', 'missing', 'not-text', 'crlf'):
                with self.subTest(path=path, mutation=mutation), self.assertRaises(owner.ContractError):
                    self.dependencies = dict(original)
                    if mutation == 'missing': self.dependencies.pop(path)
                    elif mutation == 'not-text': self.dependencies[path] = None
                    elif mutation == 'crlf': self.dependencies[path] = original[path].replace('\n', '\r\n')
                    else: self.dependencies[path] += '# unreviewed change\n'
                    self.run_contract()
        self.dependencies = dict(original, unexpected='not admitted')
        with self.assertRaises(owner.ContractError): self.run_contract()
    def test_crlf_and_lf_bytes_are_distinct_reviewed_identities(self):
        text = 'line one\nline two\n'
        self.assertNotEqual(owner.git_blob(text), owner.git_blob(text.replace('\n', '\r\n')))
    def test_supplied_workflow_must_match_the_admitted_workflow_bytes(self):
        self.workflow += '# unreviewed workflow\n'
        with self.assertRaises(owner.ContractError): self.run_contract()
    def test_source_evidence_is_required_even_for_reviewed_dynamic_bytes(self):
        first, second, third = self.registry()
        with first, second, third, \
                self.assertRaisesRegex(owner.ContractError, 'actual immutable source evidence'):
            owner.validate(self.alignment, self.publisher, self.entry, self.workflow,
                self.caller, self.readme, publisher_dependencies=self.dependencies)
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

    # --- Independent inventory and statically derived execution closure ---
    def test_independent_inventory_equals_the_production_registry(self):
        self.assertEqual(owner.PUBLISHER_PATH, EXPECTED_PUBLISHER)
        self.assertEqual(owner.ENTRYPOINT_PATH, EXPECTED_ENTRYPOINT)
        self.assertEqual(owner.WORKFLOW_PATH, EXPECTED_WORKFLOW)
        self.assertEqual(len(EXPECTED_DEPENDENCIES), len(set(EXPECTED_DEPENDENCIES)))
        self.assertEqual(set(owner.DYNAMIC_DEPENDENCY_BLOBS), set(EXPECTED_DEPENDENCIES))
        self.assertNotIn(EXPECTED_PUBLISHER, owner.DYNAMIC_DEPENDENCY_BLOBS)
        self.assertNotIn(EXPECTED_ENTRYPOINT, owner.DYNAMIC_DEPENDENCY_BLOBS)
        for blob in (owner.DYNAMIC_PUBLISHER_BLOB, owner.DYNAMIC_ENTRYPOINT_BLOB,
                     *owner.DYNAMIC_DEPENDENCY_BLOBS.values()):
            self.assertRegex(blob, r'^[0-9a-f]{40}$')
        self.assertEqual(owner.ADMITTED_DEFAULT_SCOPE, 'estate')
        self.assertEqual(owner.ADMITTED_SCOPES, ('estate', 'lyte'))
    def test_derived_closure_equals_the_independent_inventory(self):
        self.assertEqual(owner.workflow_job_roots(self.workflow), list(EXPECTED_WORKFLOW_ROOTS))
        sources = dict(synthetic_sources(), **{EXPECTED_PUBLISHER: self.publisher,
                                               EXPECTED_ENTRYPOINT: self.entry})
        closure, data = owner.derive_execution_closure(EXPECTED_WORKFLOW_ROOTS, sources)
        self.assertEqual(closure, list(EXPECTED_CODE))
        self.assertEqual(data, ['deployments/fixture/index.html'])
    def test_receipt_records_the_admitted_estate_route_not_lyte_only(self):
        closure = self.run_contract()['publisher_execution_closure']
        self.assertEqual(closure['entrypoint_default_scope'], 'estate')
        self.assertEqual(closure['workflow_scopes'], ['estate'])
        self.assertEqual(closure['admitted_scopes'], ['estate', 'lyte'])
        self.assertIs(closure['lyte_only'], False)
        self.assertTrue(closure['route'].startswith('estate-default'))
        self.assertEqual(closure['derivation'], 'STATIC_AST_NO_EXECUTION')
        self.assertEqual(set(closure['admitted_blobs']),
                         {EXPECTED_PUBLISHER, EXPECTED_ENTRYPOINT, *EXPECTED_DEPENDENCIES})
        self.assertEqual(closure['workflow_roots'], list(EXPECTED_WORKFLOW_ROOTS))
    def test_unregistered_neutral_helper_is_rejected_by_derivation(self):
        forms = (
            'HELPER = HERE / "neutral_fixture_helper.py"\n',
            f'HELPER = {sibling("neutral_fixture_helper.py")}\n',
            'import neutral_fixture_helper\n',
            'from neutral_fixture_helper import inert\n',
            'import importlib\nimportlib.import_module("neutral_fixture_helper")\n',
            'import importlib.util\nimportlib.util.spec_from_file_location("n", "scripts/neutral_fixture_helper.py")\n',
            'ARGV = ["python", "-m", "neutral_fixture_helper"]\n',
            'HELPER = "scripts/neutral_fixture_helper.py"\n',
            'HELPER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "neutral_fixture_helper.py")\n',
            'HELPER = Path(HERE, "neutral_fixture_helper.py")\n',
            'HELPER = HERE.joinpath("neutral_fixture_helper.py")\n',
            'import importlib.util\nimportlib.util.spec_from_file_location("n", location=HERE / "neutral_fixture_helper.py")\n',
        )
        original_entry = self.entry
        original_v3 = self.dependencies['scripts/hf_publish_vertical_services_frontier_v3.py']
        for target in ('entrypoint', 'transitive-sibling'):
            for form in forms:
                with self.subTest(target=target, form=form), \
                        self.assertRaisesRegex(owner.ContractError, 'unreviewed repository path'):
                    self.entry = original_entry
                    self.dependencies['scripts/hf_publish_vertical_services_frontier_v3.py'] = original_v3
                    if target == 'entrypoint': self.entry = original_entry + form
                    else: self.dependencies['scripts/hf_publish_vertical_services_frontier_v3.py'] = original_v3 + form
                    self.admit()
                    self.run_contract()
    def test_registered_but_unreachable_file_is_rejected(self):
        self.dependencies['scripts/orphan_fixture.py'] = '# inert orphan fixture\n'
        self.admit()
        with self.assertRaisesRegex(owner.ContractError, 'differs from the derived execution closure'):
            self.run_contract()
    def test_workflow_scope_must_agree_with_the_admitted_closure(self):
        job = '  publish-vertical-flagships:\n    runs-on: ubuntu-latest\n'
        accepted = {
            'omitted': (SYNTHETIC_WORKFLOW, ['estate']),
            'explicit-lyte': (SYNTHETIC_WORKFLOW.replace(job, job + '    env:\n      SZL_FLAGSHIP_SCOPE: lyte\n'),
                              ['estate', 'lyte']),
            'explicit-estate': (SYNTHETIC_WORKFLOW.replace(job, job + "    env:\n      SZL_FLAGSHIP_SCOPE: 'estate'\n"),
                                ['estate']),
            'unrelated-job': (SYNTHETIC_WORKFLOW.replace('  unrelated:\n    runs-on: ubuntu-latest\n',
                '  unrelated:\n    runs-on: ubuntu-latest\n    env:\n      SZL_FLAGSHIP_SCOPE: finance\n'), ['estate']),
        }
        for name, (text, scopes) in accepted.items():
            with self.subTest(name=name):
                self.set_workflow(text)
                self.assertEqual(self.run_contract()['publisher_execution_closure']['workflow_scopes'], scopes)
        rejected = {scope: SYNTHETIC_WORKFLOW.replace(job, job + f'    env:\n      SZL_FLAGSHIP_SCOPE: {scope}\n')
                    for scope in ('finance', 'sentra', 'terra', 'counsel', '${{ inputs.flagship_scope }}', '""')}
        rejected['workflow-env'] = SYNTHETIC_WORKFLOW.replace('env:\n  CANONICAL_SPACE', 'env:\n  SZL_FLAGSHIP_SCOPE: finance\n  CANONICAL_SPACE')
        rejected['github-env'] = SYNTHETIC_WORKFLOW.replace(
            '      - run: python -I -B scripts/hf_publish_vertical_flagships_v4.py\n',
            '      - run: echo "SZL_FLAGSHIP_SCOPE=sentra" >> "$GITHUB_ENV"\n'
            '      - run: python -I -B scripts/hf_publish_vertical_flagships_v4.py\n')
        rejected['mention-only'] = SYNTHETIC_WORKFLOW.replace(job, job + '    # SZL_FLAGSHIP_SCOPE stays unset here\n')
        for name, text in rejected.items():
            with self.subTest(name=name), self.assertRaises(owner.ContractError):
                self.set_workflow(text)
                self.run_contract()
    def test_entrypoint_must_keep_the_reviewed_default_estate_selector(self):
        selector = 'os.environ.get("SZL_FLAGSHIP_SCOPE", "estate")'
        for variant in ('os.environ.get("SZL_FLAGSHIP_SCOPE", "finance")',
                        'os.environ.get("SZL_FLAGSHIP_SCOPE", "lyte")',
                        'os.environ.get("SZL_FLAGSHIP_SCOPE")',
                        'os.environ.get("SZL_FLAGSHIP_SCOPE", DEFAULT)',
                        'os.environ.get("SZL_FLAGSHIP_SCOPE", default="estate")',
                        'os.environ.get("OTHER_SCOPE", "estate")',
                        selector + ' or os.environ["SZL_FLAGSHIP_SCOPE"]'):
            with self.subTest(variant=variant), self.assertRaisesRegex(owner.ContractError, 'default estate scope'):
                self.entry = SYNTHETIC_ENTRYPOINT.replace(selector, variant)
                self.admit()
                self.run_contract()
    def test_uncomputable_repository_references_fail_closed(self):
        for addition in ('import importlib.util\nNAME = "x"\nimportlib.util.spec_from_file_location("x", HERE / f"{NAME}.py")\n',
                         'NAME = "x.py"\nHELPER = HERE / NAME\n',
                         'import importlib\nNAME = "x"\nimportlib.import_module(NAME)\n',
                         'import importlib.util\nimportlib.util.spec_from_file_location("x", "scripts/" + "x.py")\n',
                         'from . import sibling_fixture\n',
                         'ESCAPE = Path(__file__).resolve().parents[9] / "x.py"\n',
                         'FOUND = list(HERE.glob("*.py"))\n',
                         'import sys\nNAME = "x"\nARGV = [sys.executable, "-m", NAME]\n',
                         'HELPER = HERE.with_name(NAME_FROM_ELSEWHERE)\n',
                         'ESCAPE = HERE / "/fixture/absolute.py"\n',
                         'ESCAPE = HERE / "..\\\\fixture.py"\n',
                         'N = 1\nUP = Path(__file__).parents[N]\n',
                         'FOUND = os.listdir(HERE)\n',
                         'import importlib\nimportlib.import_module(".neutral_fixture_helper")\n',
                         'import importlib.util\nimportlib.util.spec_from_file_location("x", location="scripts/" + "x.py")\n',
                         'import runpy\nrunpy.run_path("scripts/" + "x.py")\n',
                         'from importlib.machinery import SourceFileLoader\nSourceFileLoader("x", "scripts/" + "x.py")\n'):
            with self.subTest(addition=addition), self.assertRaises(owner.ContractError):
                self.entry = SYNTHETIC_ENTRYPOINT + addition
                self.admit()
                self.run_contract()
    def test_workflow_job_must_run_only_admitted_repository_programs(self):
        step = '      - run: python -I -B scripts/estate_child_completion.py\n'
        accepted = SYNTHETIC_WORKFLOW.replace('scripts/unrelated_fixture_tool.py', 'scripts/other_unrelated_tool.py')
        self.set_workflow(accepted)
        self.assertEqual(self.run_contract()['publisher_execution_closure']['workflow_roots'],
                         list(EXPECTED_WORKFLOW_ROOTS))
        for name, text in {
                'unregistered-step': SYNTHETIC_WORKFLOW.replace(step, step + '      - run: bash scripts/new_fixture_step.sh\n'),
                'local-action': SYNTHETIC_WORKFLOW.replace(step, step + '      - uses: ./.github/actions/fixture\n'),
                'unreviewed-module': SYNTHETIC_WORKFLOW.replace(step, step + '      - run: python -m fixture_tool\n'),
                'second-invoking-job': SYNTHETIC_WORKFLOW.replace('scripts/unrelated_fixture_tool.py', EXPECTED_ENTRYPOINT),
                'no-invocation': SYNTHETIC_WORKFLOW.replace('scripts/hf_publish_vertical_flagships_v4.py', 'scripts/elsewhere.py'),
                'no-jobs': 'name: fixture\non: workflow_dispatch\n'}.items():
            with self.subTest(name=name), self.assertRaises(owner.ContractError):
                self.set_workflow(text)
                self.run_contract()
    def test_malformed_admitted_closure_source_is_a_contract_error(self):
        with self.assertRaisesRegex(owner.ContractError, 'not parseable'):
            owner.entrypoint_default_scope('def broken(:\n')
        for path in ('scripts/hf_finance_workspace.py', EXPECTED_ENTRYPOINT):
            with self.subTest(path=path), self.assertRaisesRegex(owner.ContractError, 'not parseable'):
                self.setUp()
                if path == EXPECTED_ENTRYPOINT: self.entry = 'def broken(:\n'
                else: self.dependencies[path] = 'def broken(:\n'
                self.admit()
                self.run_contract()

    def assert_entry_rejected(self, entry, message=None):
        self.entry = entry
        self.admit()
        if message is None:
            with self.assertRaises(owner.ContractError): self.run_contract()
        else:
            with self.assertRaisesRegex(owner.ContractError, message): self.run_contract()
    def test_loader_targets_must_resolve_to_anchored_paths(self):
        """Thread 1: a Name/Attribute loader target is admitted only when resolved."""
        loader = 'importlib.util.spec_from_file_location'
        for addition in (f'{loader}("x", UNRESOLVED_TARGET)\n',
                         f'{loader}("x", settings.target)\n',
                         f'def fixture_load(target):\n    return {loader}("x", target)\nfixture_load(UNRESOLVED_TARGET)\n',
                         f'def fixture_load(target):\n    return {loader}("x", target)\n',
                         f'def fixture_load(target):\n    return {loader}("x", target)\nfixture_load(LYTE_IMPL)\nCALLBACK = fixture_load\n',
                         f'def fixture_load(target):\n    return {loader}("x", target)\nfixture_load(*[LYTE_IMPL])\n',
                         f'def fixture_load(target):\n    target = UNRESOLVED_TARGET\n    return {loader}("x", target)\nfixture_load(LYTE_IMPL)\n',
                         f'def fixture_load(target=LYTE_IMPL):\n    return {loader}("x", target)\nfixture_load()\n',
                         f'def fixture_load(target):\n    return {loader}("x", target)\n'
                         f'def fixture_load(target):\n    return {loader}("x", target)\nfixture_load(LYTE_IMPL)\n',
                         'import runpy\nrunpy.run_path(UNRESOLVED_TARGET)\n'):
            with self.subTest(addition=addition):
                self.assert_entry_rejected(SYNTHETIC_ENTRYPOINT + addition, 'computed module path')
        for resolved in (f'def fixture_load(target):\n    return {loader}("x", target)\nfixture_load(target=LYTE_IMPL)\n',
                         f'def fixture_load(*, target):\n    return {loader}("x", target)\nfixture_load(target=LYTE_IMPL)\n',
                         f'def fixture_load(target, depth):\n    if depth:\n        return fixture_load(target, depth - 1)\n'
                         f'    return {loader}("x", target)\nfixture_load(LYTE_IMPL, 1)\n'):
            with self.subTest(resolved=resolved):
                self.entry = SYNTHETIC_ENTRYPOINT + resolved
                self.admit()
                self.assertEqual(self.run_contract()['state'], 'DELEGATED')
    def test_directory_enumeration_fails_closed_without_an_anchor(self):
        """Thread 2: the workflow CWD is the repository root."""
        for addition in ('FOUND = os.listdir("scripts")\n', 'FOUND = os.walk("scripts")\n',
                         'FOUND = os.scandir(".")\n', 'import glob\nFOUND = glob.glob("scripts/*.py")\n',
                         'import glob\nFOUND = glob.iglob("*")\n', 'FOUND = Path("scripts").glob("*.py")\n',
                         'FOUND = Path(".").rglob("*")\n', 'FOUND = Path("scripts").iterdir()\n',
                         'FOUND = Path("scripts").walk()\n', 'FOUND = Path("evidence").glob(PATTERN)\n',
                         'FOUND = Path("evidence").glob("*.js")\n', 'FOUND = Path("evidence").glob("*.j*")\n',
                         'FOUND = HERE.glob("*.json")\n', 'from os import listdir\nFOUND = listdir("scripts")\n'):
            with self.subTest(addition=addition):
                self.assert_entry_rejected(SYNTHETIC_ENTRYPOINT + addition, 'enumerates a repository directory')
        # A literal, wildcard-free data suffix cannot select code (the Lyte
        # publisher's run-local replay journal guard); AST traversal is not I/O.
        self.entry = SYNTHETIC_ENTRYPOINT + (
            'import ast\nNODES = list(ast.walk(ast.parse("x = 1")))\n'
            'def retained(intent):\n    return list(intent.parent.glob("*.json"))\n')
        self.admit()
        self.assertEqual(self.run_contract()['state'], 'DELEGATED')
    def test_javascript_and_typescript_references_are_code(self):
        """Thread 3: the analyzer and workflow roots share one code-suffix set."""
        for suffix in ('.mjs', '.cjs', '.js', '.ts'):
            self.assertIn(suffix, owner.CODE_SUFFIXES)
            with self.subTest(suffix=suffix):
                self.assert_entry_rejected(SYNTHETIC_ENTRYPOINT + f'ASSET = HERE / "fixture_bundle{suffix}"\n',
                                           'unreviewed repository path')
    def test_scope_selector_must_be_os_environ_and_drive_the_dispatch(self):
        """Thread 4: bind the real selector shape, not any `.get(...)` mention."""
        selector = 'scope = os.environ.get("SZL_FLAGSHIP_SCOPE", "estate")'
        dispatch = '    if scope == "lyte":\n'
        for name, entry in {
                'decoy-receiver': SYNTHETIC_ENTRYPOINT.replace(selector,
                    'scope = settings.get("SZL_FLAGSHIP_SCOPE", "estate")'),
                'decoy-environ-name': SYNTHETIC_ENTRYPOINT.replace(selector,
                    'scope = environ.get("SZL_FLAGSHIP_SCOPE", "estate")'),
                'unassigned': SYNTHETIC_ENTRYPOINT.replace(selector,
                    'os.environ.get("SZL_FLAGSHIP_SCOPE", "estate")\n    scope = "lyte"'),
                'not-dispatched': SYNTHETIC_ENTRYPOINT.replace(dispatch, '    if other_scope == "lyte":\n'),
                'reassigned': SYNTHETIC_ENTRYPOINT.replace(dispatch, '    scope = "lyte"\n' + dispatch),
                'module-level': SYNTHETIC_ENTRYPOINT.replace('    ' + selector + '\n', '') + selector + '\n'}.items():
            with self.subTest(name=name):
                self.assert_entry_rejected(entry, 'default estate scope selector')
        self.entry = SYNTHETIC_ENTRYPOINT.replace('os.environ.get(', 'os.getenv(')
        self.admit()
        self.assertEqual(self.run_contract()['publisher_execution_closure']['entrypoint_default_scope'], 'estate')

    # --- Production CLI ordering: reject before evidence, checkout reads or receipt ---
    def cli_inputs(self):
        inputs = {f'publisher/{path}': text for path, text in self.dependencies.items()}
        inputs.update({f'publisher/{EXPECTED_PUBLISHER}': self.publisher,
                       f'publisher/{EXPECTED_ENTRYPOINT}': self.entry,
                       'governance/estate/alignment.v1.json': json.dumps(self.alignment),
                       'source/.github/workflows/hf-deploy.yml': self.caller,
                       'source/README.md': self.readme})
        return inputs
    @contextlib.contextmanager
    def cli(self, inputs, *, admitted=True):
        reads = []
        def read_bytes(path):
            reads.append(path.as_posix())
            return inputs[path.as_posix()].encode()
        with contextlib.ExitStack() as stack:
            if admitted:
                for item in self.registry():
                    stack.enter_context(item)
            stack.enter_context(patch.object(sys, 'argv', ['verify-hf-ownership.py', '--source', 'source',
                '--governance', 'governance', '--publisher', 'publisher', '--output', 'evidence/receipt.json']))
            stack.enter_context(patch.object(Path, 'read_bytes', autospec=True, side_effect=read_bytes))
            stack.enter_context(patch('builtins.print'))
            mocks = {'evidence': stack.enter_context(patch.object(owner, 'read_source_evidence',
                         return_value=(self.head, self.checks))),
                     'checkout': stack.enter_context(patch.object(owner, 'revision', return_value='c' * 40)),
                     'tip': stack.enter_context(patch.object(owner, 'github_json', return_value=self.head)),
                     'mkdir': stack.enter_context(patch.object(Path, 'mkdir')),
                     'receipt': stack.enter_context(patch.object(Path, 'write_text')),
                     'reads': reads}
            yield mocks
    def assert_nothing_after_rejection(self, mocks):
        for name in ('evidence', 'checkout', 'tip', 'mkdir', 'receipt'):
            mocks[name].assert_not_called()
    def test_cli_reaches_mocked_evidence_and_records_the_admitted_closure(self):
        with self.cli(self.cli_inputs()) as mocks:
            self.assertEqual(owner.main(), 0)
        mocks['evidence'].assert_called_once_with()
        self.assertEqual(mocks['checkout'].call_count, 3)
        mocks['tip'].assert_called_once()
        self.assertLessEqual({f'publisher/{path}' for path in (EXPECTED_PUBLISHER, EXPECTED_ENTRYPOINT,
                              *EXPECTED_DEPENDENCIES)}, set(mocks['reads']))
        receipt = json.loads(mocks['receipt'].call_args.args[0])
        self.assertIs(receipt['backend_tip_reverified'], True)
        closure = receipt['publisher_execution_closure']
        self.assertEqual(closure['workflow_scopes'], ['estate'])
        self.assertIs(closure['lyte_only'], False)
        self.assertEqual(set(closure['admitted_blobs']),
                         {EXPECTED_PUBLISHER, EXPECTED_ENTRYPOINT, *EXPECTED_DEPENDENCIES})
        self.assertEqual(closure['unbound_data_references'], ['deployments/fixture/index.html'])
        self.assertEqual(set(receipt['publisher_dependency_blobs']), set(EXPECTED_DEPENDENCIES))
    def test_cli_rejects_unreviewed_bytes_before_evidence_or_receipt(self):
        original_publisher, original_entry = self.publisher, self.entry
        for changed in ('publisher', 'entrypoint', 'static-pin', 'line-endings'):
            with self.subTest(changed=changed):
                self.publisher, self.entry = original_publisher, original_entry
                if changed == 'publisher': self.publisher += '\n# unreviewed publisher\n'
                if changed == 'entrypoint': self.entry += '\n# unreviewed entrypoint\n'
                if changed == 'static-pin': self.publisher += '\nSOURCE_REVISION = "' + 'a' * 40 + '"\n'
                if changed == 'line-endings': self.publisher = original_publisher.replace('\n', '\r\n')
                inputs = self.cli_inputs()
                self.publisher, self.entry = original_publisher, original_entry
                with self.cli(inputs) as mocks, \
                        self.assertRaisesRegex(owner.ContractError, 'reviewed exact Git blobs'):
                    owner.main()
                self.assert_nothing_after_rejection(mocks)
    def test_cli_rejects_changed_dependency_before_network_or_receipt(self):
        for path in EXPECTED_DEPENDENCIES:
            for mutation in ('changed', 'crlf'):
                inputs = self.cli_inputs()
                key = f'publisher/{path}'
                inputs[key] = inputs[key] + '# unreviewed dependency\n' if mutation == 'changed' \
                    else inputs[key].replace('\n', '\r\n')
                with self.subTest(path=path, mutation=mutation), self.cli(inputs) as mocks, \
                        self.assertRaises(owner.ContractError):
                    owner.main()
                self.assert_nothing_after_rejection(mocks)
    def test_cli_rejects_invalid_closure_before_evidence_or_receipt(self):
        job = '  publish-vertical-flagships:\n    runs-on: ubuntu-latest\n'
        original_entry, original_workflow = self.entry, self.workflow
        for name in ('neutral-helper', 'finance-scope', 'orphan'):
            with self.subTest(name=name):
                self.setUp()
                if name == 'neutral-helper':
                    self.entry = original_entry + 'HELPER = HERE / "neutral_fixture_helper.py"\n'
                elif name == 'finance-scope':
                    self.set_workflow(original_workflow.replace(job, job + '    env:\n      SZL_FLAGSHIP_SCOPE: finance\n'))
                else:
                    self.dependencies['scripts/orphan_fixture.py'] = '# inert orphan fixture\n'
                self.admit()
                with self.cli(self.cli_inputs()) as mocks, self.assertRaises(owner.ContractError):
                    owner.main()
                self.assert_nothing_after_rejection(mocks)


class PublisherIsolation(unittest.TestCase):
    def test_publisher_text_is_parsed_without_execution(self):
        self.assertEqual(owner.constants('SOURCE_REVISION = "' + 'a' * 40 + '"\nraise RuntimeError("must never run")')['SOURCE_REVISION'], 'a' * 40)

if __name__ == '__main__':
    unittest.main(verbosity=2)
