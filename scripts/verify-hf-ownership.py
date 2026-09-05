#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify Lyte's read-only delegation; this script never publishes or probes uptime."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

SHA40 = re.compile(r'^[0-9a-f]{40}$')

class ContractError(ValueError):
    """A publication authority or exact-source invariant is missing."""

def constants(source: str) -> dict[str, Any]:
    result = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                result[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    return result

def validate(alignment: dict, publisher: str, entrypoint: str, workflow: str) -> dict:
    if alignment.get('schema') != 'szl.estate.alignment/v1':
        raise ContractError('Unrecognized estate authority schema')
    rows = [row for row in alignment.get('public_bodies', []) if row.get('id') == 'lyte']
    if len(rows) != 1:
        raise ContractError('Lyte must have exactly one public body')
    expected = {'backend_source': 'szl-holdings/lyte-services', 'presentation_source': 'szl-holdings/lyte-lattice', 'hub_surface': 'SZLHOLDINGS/lyte'}
    if any(rows[0].get(key) != value for key, value in expected.items()):
        raise ContractError('Lyte runtime, presentation, or Hub authority changed')
    policy = alignment.get('hub_alias_policy', {})
    if policy.get('duplicate_authority_spaces_forbidden') is not True or 'lyte' not in policy.get('canonical_public_space_slugs', []):
        raise ContractError('Canonical Space / duplicate-authority policy missing')
    owner = constants(publisher)
    entry = constants(entrypoint)
    if owner.get('SOURCE_REPOSITORY') != expected['backend_source'] or owner.get('HF_REPOSITORY') != expected['hub_surface']:
        raise ContractError('Publisher does not target the admitted backend and Space')
    revision = owner.get('SOURCE_REVISION')
    if not isinstance(revision, str) or not SHA40.fullmatch(revision):
        raise ContractError('Backend revision must be an immutable Git commit')
    if entry.get('LYTE_SOURCE_REVISION') != revision:
        raise ContractError('Vertical entrypoint and Lyte source pins disagree')
    if entry.get('SOURCE_OWNED_FLAGSHIP_SLUGS') != ('lyte',):
        raise ContractError('Lyte must remain source-owned, not a generic generated shell')
    if 'hf_publish_lyte_enterprise.py' not in entrypoint or 'hf_publish_vertical_flagships_v4.py' not in workflow:
        raise ContractError('Canonical workflow no longer invokes the owned publisher')
    if owner.get('ORIGIN') != 'https://szlholdings-lyte.hf.space':
        raise ContractError('Unexpected runtime origin')
    return {'schema': 'szl.lyte.canonical-delegation/v2', 'state': 'DELEGATED',
            **expected, 'backend_source_revision': revision,
            'publisher_repository': 'szl-holdings/a11oy',
            'publisher_workflow': '.github/workflows/hf-sync.yml',
            'publisher_entrypoint': 'scripts/hf_publish_vertical_flagships_v4.py',
            'source_owned_publisher': 'scripts/hf_publish_lyte_enterprise.py',
            'retired_space': 'SZLHOLDINGS/lyte-lattice',
            'retired_space_recreated': False, 'provider_writes': False,
            'provider_credentials_local': False, 'runtime_observed': False,
            'scope': 'SOURCE_AUTHORITY_ONLY_NOT_RUNTIME_ACCEPTANCE'}

def revision(root: Path) -> str:
    value = subprocess.check_output(['git', '-C', str(root), 'rev-parse', '--verify', 'HEAD'], text=True).strip()
    if not SHA40.fullmatch(value):
        raise ContractError('Checkout is not bound to a full commit identity')
    return value

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--governance', type=Path, required=True)
    parser.add_argument('--publisher', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    paths = {'alignment': args.governance / 'estate/alignment.v1.json',
             'publisher': args.publisher / 'scripts/hf_publish_lyte_enterprise.py',
             'entrypoint': args.publisher / 'scripts/hf_publish_vertical_flagships_v4.py',
             'workflow': args.publisher / '.github/workflows/hf-sync.yml'}
    content = {key: path.read_text(encoding='utf-8') for key, path in paths.items()}
    result = validate(json.loads(content['alignment']), content['publisher'], content['entrypoint'], content['workflow'])
    result['checkout_revisions'] = {'presentation': revision(args.source), 'governance': revision(args.governance), 'publisher': revision(args.publisher)}
    result['input_sha256'] = {key: hashlib.sha256(value.encode()).hexdigest() for key, value in content.items()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
