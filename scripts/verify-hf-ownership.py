#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify Lyte's read-only delegation; never publish or certify runtime uptime."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

SHA40 = re.compile(r'^[0-9a-f]{40}$')
SOURCE_REQUIRED_CHECKS = (
    'python-compile', 'lint', 'unit', 'api-contract', 'release-gates',
    'database-migrations', 'connector-contract', 'truth-and-governance',
    'security-scan', 'secret-scan', 'frontend-static-contract', 'accessibility',
    'responsive-overflow', 'bundle-budget', 'container-build', 'container-smoke',
    'source-binding',
)
# Reviewed immutable a11oy@88ab7ab539c779f2a026bdd6cff5193a950289c6 blobs.
# Publisher pins the reviewed controller 10cb5f7665ab5469c876c3418888a71f521fd76b.
# A new publisher/resolver or entrypoint requires a separate authority review.
DYNAMIC_PUBLISHER_BLOB = '0dfd432f5311cd6c5ed3999b7ee5dab98bbffd48'
DYNAMIC_ENTRYPOINT_BLOB = 'cdbe1577313c138d9cf8af294509e6c502d67a5b'

class ContractError(ValueError):
    """A publication authority or exact-source invariant is missing."""

def git_blob(source: str) -> str:
    payload = source.encode('utf-8')
    return hashlib.sha1(f'blob {len(payload)}\0'.encode('ascii') + payload).hexdigest()

def verified_source_revision(head: dict) -> str:
    value = head.get('sha')
    commit = head.get('commit')
    verification = commit.get('verification') if isinstance(commit, dict) else None
    if (not isinstance(value, str) or not SHA40.fullmatch(value)
            or value == '0' * 40 or not isinstance(verification, dict)
            or verification.get('verified') is not True):
        raise ContractError('Backend tip must be an exact verified nonzero Git commit')
    return value

def admit_source_checks(head: dict, evidence: dict) -> str:
    revision = verified_source_revision(head)
    checks = evidence.get('check_runs')
    count = evidence.get('total_count')
    if (not isinstance(checks, list) or type(count) is not int
            or count != len(checks)):
        raise ContractError('Complete backend check-run evidence is required')
    trusted = [row for row in checks if isinstance(row, dict)
               and row.get('head_sha') == revision and isinstance(row.get('app'), dict)
               and row['app'].get('slug') == 'github-actions']
    for name in SOURCE_REQUIRED_CHECKS:
        rows = [row for row in trusted if row.get('name') == name]
        if not rows or any(row.get('status') != 'completed'
                           or row.get('conclusion') != 'success' for row in rows):
            raise ContractError(f'Backend source gate did not pass: {name}')
    return revision

def github_json(path: str) -> dict:
    """Read only the public backend's fixed GitHub origin, without credentials."""
    allowed = r'/repos/szl-holdings/lyte-services/commits/(?:main|[0-9a-f]{40}/check-runs\?filter=latest&per_page=100&page=[1-9][0-9]?)'
    if re.fullmatch(allowed, path) is None:
        raise ContractError('Unadmitted GitHub source-evidence route')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise ContractError('GitHub source-evidence redirect refused')
    request = urllib.request.Request('https://api.github.com' + path, headers={
        'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
        'Cache-Control': 'no-cache', 'User-Agent': 'SZL-Lyte-ReadOnly-Authority/3',
    })
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=30) as response:
        payload = response.read(2_000_001)
    if len(payload) > 2_000_000:
        raise ContractError('GitHub source-evidence response exceeds its bound')
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ContractError('Duplicate GitHub evidence JSON key')
            result[key] = value
        return result
    result = json.loads(payload, object_pairs_hook=unique_object)
    if not isinstance(result, dict):
        raise ContractError('GitHub source-evidence response must be an object')
    return result

def read_source_evidence() -> tuple[dict, dict]:
    head = github_json('/repos/szl-holdings/lyte-services/commits/main')
    revision = verified_source_revision(head)
    checks = []
    count = None
    for page in range(1, 11):
        item = github_json(f'/repos/szl-holdings/lyte-services/commits/{revision}/check-runs?filter=latest&per_page=100&page={page}')
        rows, total = item.get('check_runs'), item.get('total_count')
        if (not isinstance(rows, list) or type(total) is not int or total < 0
                or total > 1000 or len(rows) > 100 or (count is not None and total != count)):
            raise ContractError('Backend check-run pagination is incomplete or changed')
        count = total
        checks.extend(rows)
        if len(checks) == count:
            return head, {'check_runs': checks, 'total_count': count}
        if not rows or len(checks) > count:
            break
    raise ContractError('Complete backend check-run pagination is required')

def require_current_source(revision: str) -> None:
    if verified_source_revision(github_json('/repos/szl-holdings/lyte-services/commits/main')) != revision:
        raise ContractError('Backend tip changed after read-only source admission')

def constants(source: str) -> dict[str, Any]:
    result = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                result[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    return result

def validate_card(text: str) -> None:
    if not text.startswith('---\n'):
        raise ContractError('README must start with Hub YAML metadata')
    end = text.find('\n---\n', 4)
    if end < 0:
        raise ContractError('README metadata closing delimiter missing')
    rows = [line.split(':', 1)[1].strip() for line in text[4:end].splitlines() if line.startswith('short_description:')]
    if len(rows) != 1:
        raise ContractError('Exactly one short_description is required')
    raw = rows[0]
    quoted = len(raw) >= 2 and raw[0] in {'"', "'"} and raw[-1] == raw[0]
    if ':' in raw and not quoted:
        raise ContractError('Colon-bearing description must be quoted')
    value = raw[1:-1] if quoted else raw
    if not value or len(value) > 60:
        raise ContractError('Description must contain 1..60 characters')

def validate_caller(text: str) -> None:
    if not re.search(r'(?m)^permissions:\s*\n  contents: read\s*$', text):
        raise ContractError('Caller must explicitly have read-only contents permission')
    forbidden = (
        r'\$\{\{\s*secrets\.',
        r'(?m)^\s+[\w-]+:\s*write\s*$',
        r'(?m)^\s+HF_[A-Z_]+:',
        r'reusable-hf-deploy\.yml@',
        r'\b(?:upload_folder|upload_file|create_repo|restart_space|pause_space)\s*\(',
    )
    if any(re.search(pattern, text) for pattern in forbidden):
        raise ContractError('Presentation caller must not own a provider credential or write lane')

def validate(alignment: dict, publisher: str, entrypoint: str, workflow: str,
             caller: str, readme: str, *, source_head: dict | None = None,
             source_checks: dict | None = None) -> dict:
    validate_card(readme)
    validate_caller(caller)
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
    dynamic = 'SOURCE_REVISION' not in owner
    if dynamic:
        if (git_blob(publisher) != DYNAMIC_PUBLISHER_BLOB
                or git_blob(entrypoint) != DYNAMIC_ENTRYPOINT_BLOB
                or owner.get('SOURCE_VARIABLE') != 'LYTE_SOURCE_REVISION'
                or owner.get('SOURCE_REQUIRED_CHECKS') != SOURCE_REQUIRED_CHECKS):
            raise ContractError('Dynamic publisher and entrypoint require reviewed exact Git blobs')
        if source_head is None or source_checks is None:
            raise ContractError('Dynamic publisher requires actual immutable source evidence')
        revision = admit_source_checks(source_head, source_checks)
    else:
        if not isinstance(revision, str) or not SHA40.fullmatch(revision) or revision == '0' * 40:
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
            'source_revision_policy': 'reviewed-verified-current-tip' if dynamic else 'matching-immutable-static-pins',
            'backend_signature_verified': dynamic,
            'required_source_checks': list(SOURCE_REQUIRED_CHECKS) if dynamic else [],
            'backend_tip_reverified': False,
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
             'workflow': args.publisher / '.github/workflows/hf-sync.yml',
             'caller': args.source / '.github/workflows/hf-deploy.yml',
             'readme': args.source / 'README.md'}
    content = {key: path.read_text(encoding='utf-8') for key, path in paths.items()}
    source = {}
    if 'SOURCE_REVISION' not in constants(content['publisher']):
        # Reject unreviewed publisher changes before even reading backend state.
        if git_blob(content['publisher']) != DYNAMIC_PUBLISHER_BLOB or git_blob(content['entrypoint']) != DYNAMIC_ENTRYPOINT_BLOB:
            raise ContractError('Dynamic publisher and entrypoint require reviewed exact Git blobs')
        source['source_head'], source['source_checks'] = read_source_evidence()
    result = validate(json.loads(content['alignment']), content['publisher'], content['entrypoint'], content['workflow'], content['caller'], content['readme'], **source)
    result['checkout_revisions'] = {'presentation': revision(args.source), 'governance': revision(args.governance), 'publisher': revision(args.publisher)}
    result['input_sha256'] = {key: hashlib.sha256(value.encode()).hexdigest() for key, value in content.items()}
    if source:
        require_current_source(result['backend_source_revision'])
        result['backend_tip_reverified'] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
