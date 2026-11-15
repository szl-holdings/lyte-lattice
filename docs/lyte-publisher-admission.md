# Canonical Lyte publisher source admission

The presentation package's read-only ownership verifier admits exact Git blobs
from `szl-holdings/a11oy`. The complete 23-file closure below received agent
source review at verified commit `06fecb6a836d5c10d04e638ab91df4e6db79ce52`
on 2026-11-05 UTC. It supersedes the admission at
`d3aee5e86b57def71addc04c0510a7b23c752cff`: only the bound workflow blob changed,
from `2bd1510285ad7d40dc2af3f11420de927438b329` to
`1f0b9f80893f1df021870df3608c424a40df96ab`. The other 22 files are unchanged
and no executable dependency was added or removed. The closure analyzer,
exact-byte rejection rules and source-evidence gates are unchanged. This
records agent source review of those bytes, not a GitHub review approval,
human-owner approval, independent execution, or production authorization.

## Changes reviewed for this admission

The diff of `.github/workflows/hf-sync.yml` against the previous admitted blob
is two hunks. No Lyte publisher, entrypoint, sibling publisher, publication
target, scope, permission, secret, or Space visibility changes.

- **Canonical A11oy preflight.** In `preflight`, "Require an open deploy
  window while SQLite lives on the bucket mount" no longer warns and continues
  when the window is closed. A `PAUSED` stage or an explicit
  `open_deploy_window` dispatch still sets `open=true`. Otherwise, when the
  stage is `RUNNING`, the step reads `$CANONICAL_ORIGIN/api/build-info`
  (`https://szlholdings-a11oy.hf.space`, Space `SZLHOLDINGS/a11oy`) and sets
  `open=false` only if `build.revision` equals `GITHUB_SHA`. Every other
  closed-window state exits 1 with
  `PUBLICATION_BLOCKED_DEPLOY_WINDOW_CLOSED`. This is the canonical A11oy
  Space job, not the Lyte publisher. The hunk arrived in a11oy #3221
  (`bb950a8b65b8633a5ada713c6bc250c40a79c31b`), whose GitHub review list is
  empty. That commit's workflow blob was
  `d9a115a3f9d14e9a4129bfd3016663dcce2d488f`.
- **Flagship job action pin.** `publish-vertical-flagships` changes one
  action pin: `step-security/harden-runner` from
  `dc2769abcc0fcfbadfc1df54081c1608579ef6b2` (v2.22.2) to
  `46b06cea07f9e64621fdf066ba77ac6915163d43` (v2.22.3), still
  `egress-policy: audit`. The job condition, needs, concurrency, secrets, and
  publisher command are unchanged. The hunk arrived in a11oy #3166
  (`d0226bb82b38255bc58131a8436fd4196e320402`), a Dependabot merge whose
  GitHub review list is empty. That commit is where blob
  `1f0b9f80893f1df021870df3608c424a40df96ab` first appears. The same blob is
  still the file on `06fecb6a`.

## Previous admission

Commit `d3aee5e86b57def71addc04c0510a7b23c752cff` (2026-11-03 UTC) admitted
workflow blob `2bd1510285ad7d40dc2af3f11420de927438b329` and superseded
`deb1aa4f24252747b72edfe77905fe7567d11716`. That review is not reopened. Its
workflow delta was inside `execution-handoff`: failure outputs through
`GITHUB_OUTPUT`, a separate failure-receipt path, and split success and
blocked artifacts. `publish-vertical-flagships` was byte-identical in that
delta. The handoff helper blob `d7c7a15df68c73f6c264948e43ef3035feb92315` and
collector blob `85246d7d9b1b6057c5141889944f9a4c19b50fd8` stay outside this
closure.

Validation used the exact 23 files from `06fecb6a`. The previous registry
rejected the workflow blob; the updated registry derives the same complete
closure and rejects mutations of all 23 files, including an unknown workflow.
Offline authority and failure-receipt regressions remain required. The
fixture evidence and static closure check do not execute publisher code,
install provider SDKs, contact Hugging Face, or establish that backend
checks currently pass.

## Admitted scope: the default estate route, not Lyte alone

The `publish-vertical-flagships` job in `hf-sync.yml` runs
`scripts/hf_publish_vertical_flagships_v4.py` without `SZL_FLAGSHIP_SCOPE`.
The entrypoint therefore takes its default `estate` route. That route runs
three publishers in one Python process, loading each with `exec_module`:

1. the generated-flagship publisher (Terra, Sentra, Counsel and Finance shells);
2. the source-owned Lyte publisher;
3. the combined vertical-services intelligence publisher.

Earlier admissions covered only the Lyte files. They did not cover the sibling
publishers that run before and after Lyte in the same process. This admission
binds the whole route, plus the job's own gates: the exact-main ownership
check, the vertical plan gate and the completion helper. An explicit
`SZL_FLAGSHIP_SCOPE=lyte` runs a subset of this closure and is also admitted.
Every other scope (`finance`, `sentra`, `terra`, `counsel`) does not publish
Lyte and fails closed. So does any non-literal scope value.

| Path | Git blob | Role |
| --- | --- | --- |
| `.github/workflows/hf-sync.yml` | `1f0b9f80893f1df021870df3608c424a40df96ab` | Workflow; job invokes the entrypoint with the default scope |
| `scripts/hf_publish_vertical_flagships_v4.py` | `199cd4d30e86c6b0e01aeb7818803bb7d68d6a70` | Entrypoint and scope dispatch |
| `scripts/hf_publish_lyte_enterprise.py` | `7c533d753a2b913a77bb71074f04aa5b753b0392` | Lyte publisher (`SZLHOLDINGS/lyte`) |
| `scripts/szl_release_guard.py` | `f6c7bc02df02076388be5fa0b6949d8929cc2ba2` | Lyte release primitive |
| `scripts/lyte_enterprise_live_contract.py` | `494116f65b24ea5b8a516abde31668be2248cbf4` | Lyte live contract |
| `scripts/hf_existing_space_guard.py` | `ebab5d507ba589bb64d01a45bf32a03c2b52cb45` | Existing-Space guard on `HfApi.create_repo` |
| `scripts/hf_exact_main_ownership.py` | `6e95133ac74f0d05d5372ed68022a691ceaa15c2` | Job gate: exact protected main |
| `scripts/estate_repair_dispatch.py` | `0ba5f87268c43b60cb85fd0bcc519b6be7b94633` | Job gate: approved vertical plan |
| `scripts/estate_child_completion.py` | `202a41f5557fa5c9a121729e8e7b07fb271917e2` | Job gate: completion receipt |
| `scripts/hf_publish_vertical_flagships_v4_impl.py` | `421188ba9e1dcce78bf2503e4b10ead3e126bded` | Generated-flagship overlay (runs before Lyte) |
| `scripts/_hf_publish_vertical_flagships_v4_impl_base.py` | `419931621a3d7de4da233840762761c4207007f5` | Generated-flagship writer |
| `scripts/hf_finance_read_proxy.py` | `56ec9cd7df6eef37e59395ce35e010637487211c` | Finance projection emitted into the Space app |
| `scripts/hf_flagship_runtime_contract.py` | `d9394a81a7407ca36e55ed1b068fbf11f3b2acc8` | Generated Space Dockerfile and requirements |
| `scripts/hf_finance_workspace.py` | `6bf54deb552bdf94578cef45f84ead8a2318c3aa` | Finance presentation |
| `scripts/hf_finance_research_workspace.py` | `18ba3c0a1feb776e7f12f46c5b69b6069b597180` | Finance presentation |
| `scripts/hf_finance_signed_workspace.py` | `febc20a7dc1391d35397bb81e38222135eb3d100` | Finance presentation |
| `scripts/hf_finance_functional_gate.py` | `7d1d1bb9a7d44add13e7f06d8ed5904d8fddb21b` | Read-only Finance public witness |
| `scripts/hf_finance_projection_manifest.py` | `4d00c2d0b1005c4f23f37c810754bdeb7eff4453` | Finance manifest and immutable Hub readback |
| `scripts/hf_vertical_native_presentation.py` | `a4a1b1dc0598b08438770e8771709521b28cddbb` | Source-owned presentation projection; no provider access |
| `scripts/hf_sentra_upstream.py` | `11e799ca6c8feb270888209188088a7f86c44fe3` | Emitted Sentra observation budget and bounded cache |
| `scripts/hf_publish_vertical_services_intelligence_v4.py` | `c4191e7f6139ad934fe9c8809174476934b2eb59` | Combined publisher, intelligence layer (runs after Lyte) |
| `scripts/hf_publish_vertical_services_frontier_v3.py` | `69b19505d307f22faeee49a98d11c97a58abd603` | Combined publisher, frontier layer |
| `scripts/hf_publish_vertical_services.py` | `3f51f74299235e99d3a1fce3b1eae3163014beba` | Combined writer (`SZLHOLDINGS/vertical-services`) |

## What the sibling publishers do

- **Generated flagships.** This route writes the existing `SZLHOLDINGS/terra`,
  `sentra`, `counsel` and `finance` Spaces. Each file is a separate
  `upload_file` commit with no parent compare-and-swap, followed by
  `restart_space`. The route then polls public endpoints for up to 30 minutes.
  The entrypoint strips Lyte and Vessels from this writer.
- **Space creation on this route.** On the estate route the existing-Space guard
  reuses an existing Space. It delegates to `create_repo` only after an exact
  404, so both sibling writers can still create a missing public Space. Only
  the selected single-target scopes block creation.
- **Combined vertical-services.** This route writes `SZLHOLDINGS/vertical-services`.
  It creates the `SENTRA_SIGNING_KEY` Space secret only when absent (a random
  value, never printed) and sets the `SZL_SOURCE_REVISION` Space variable. It
  checks out `szl-holdings/vertical-services` at the tip resolved by the
  entrypoint, which must pass that repository's Python contract suite. It then
  runs a separately pinned controller,
  `szl-holdings/.github@c889276e51e7d954c4bba8b216f86fc7577721fa`
  (blob `9d5b90b8bbf04e6d46ef0f971fc65604e1323b1b`), in a subprocess.
  Publishing (`--require-default-branch-tip`), restart and attestation all
  happen in that subprocess.
- **Finance helpers.** Most of these files are presentation strings or code
  emitted into the Space. The functional gate and the projection manifest only
  read: they make fixed public HTTP requests and immutable Hub readbacks, with
  no credentials.

The Lyte publisher still targets only backend `szl-holdings/lyte-services` and
the existing Space `SZLHOLDINGS/lyte`. It requires a verified current backend
commit, all 17 source check names, the GitHub Actions app identity, and its
separately pinned controller,
`szl-holdings/.github@163a61fd9759e5ecc3c2daf13e528f7b281ff81d`
(`.github/scripts/hf_deploy_from_dockerfile.py`, blob
`3fa968416a3623d66b5b5b64abf8b830cc854e1c`). Both controllers are checked
against their blobs before execution.

## How the verifier binds the route

The verifier's offline tests require the pinned YAML parser in
`scripts/hf-ownership-requirements.txt`. Install it with
`python -I -m pip install -r scripts/hf-ownership-requirements.txt`, then run
`python -I scripts/test_hf_ownership.py`. The read-only workflow installs the
same requirement before its tests and ownership check.

Caller permissions and credential references are inspected after YAML parsing.
Workflow permissions must explicitly grant `contents: read`; job overrides may
only reduce permissions or retain read access. Duplicate keys, merge keys,
anchors, aliases and explicit tags are rejected. Secret contexts are checked in
decoded scalar values, including bracket indexing and YAML escapes. These checks
validate the declared caller contract; they do not execute or prove arbitrary
action and shell code safe. Authority JSON with duplicate keys is rejected.
Authority manifests must contain object-shaped
public bodies and policy, with canonical slugs represented as a list of nonempty
strings. These validation rules do not change the admitted publisher blobs.

Before it looks up evidence, reads checkout revisions or writes an admitted receipt, the
verifier makes four checks:

1. Every admitted path must have its exact reviewed blob; CRLF and LF bytes are
   distinct identities. The supplied workflow must equal the admitted copy.
2. The entrypoint must read `SZL_FLAGSHIP_SCOPE` exactly once, through
   `os.environ.get` or `os.getenv` with the literal default `estate`. `os` must
   be the genuine module: imported, never rebound, shadowed by a parameter,
   patched (`os.environ = ...`) or passed on. That read must be the only binding
   of its name inside a module-level function, and that function must be what
   `if __name__ == "__main__":` runs, with no exit before the selector. The
   verifier then evaluates the dispatch for each admitted value. `estate` must
   fall through every scope test to the estate route, and `lyte` must leave
   through the return of `if scope == "lyte":`. Scope tests may compare with a
   literal (`==`, `!=`) or test membership (`in`, `not in`) in a literal set or
   a single literal module constant. Anything else fails closed: an
   unevaluable test, a scope use inside a loop, `try` or nested function, or a
   branch that captures either value first. The invoking job and the
   workflow-level env may select only `estate` or `lyte`.
3. The workflow roots are every repository program the invoking job runs, and
   the closure is derived from them statically, with AST only and no
   execution. The derivation follows `__file__`-anchored paths (`HERE / "x.py"`,
   `with_name`, `parents[n]`), `scripts/...` literals, sibling imports,
   `importlib`/`runpy` targets and `-m` module arguments, transitively.
   Python, shell and JavaScript/TypeScript suffixes are all code, including
   `.jsx`, `.tsx`, `.mts` and `.cts`. The following fail closed:
   - a relative import, or a path escaping the repository;
   - any import outside the standard library and `huggingface_hub`;
   - a loader target unless it is a literal, a `__file__`-anchored path, or a
     parameter whose every same-module call site resolves the same way (the
     entrypoint's `load_module` chain). The anchor must be exact where the
     loader runs. Every binding the load can observe in its own scope must be
     an anchored assignment. An anchor in an unrelated function, or one
     overwritten by any other binding (assignment, loop, `with`, `except`,
     walrus, augmented assignment, import, `global`, parameter), does not
     count. Neither does a rebound `__file__`, a non-genuine `os.path` or a
     shadowed `pathlib` constructor;
   - any directory enumeration (`os.listdir`, `os.scandir`, `os.walk`,
     `glob.glob`/`iglob`, `Path.glob`/`rglob`/`iterdir`/`walk`), anchored or
     not, because the job runs at the repository root. Listing is recognised
     by name on any receiver, and through aliases: `import os as o`,
     `from os import listdir as ls`, `from os import *`, `L = os.listdir`, and
     by string through `getattr`, `methodcaller` or subscripts. A listing
     module may appear only as an attribute receiver or in a literal
     `getattr` probe, such as the release guard's `getattr(os, "O_NOFOLLOW", 0)`.
     Only the genuine `ast` module's `walk` is exempt. The one exception is a
     glob on an unanchored path whose literal pattern ends in a concrete,
     wildcard-free, non-code suffix. That covers the Lyte publisher's
     run-local `*.json` replay-journal check, which cannot select code.
4. The derived closure must equal the admitted registry exactly. An
   unreferenced registered file is rejected, and so is an unregistered helper.

The receipt records the closure under `publisher_execution_closure`: the
reviewed commit, workflow roots, scopes, every admitted path and blob,
`lyte_only: false`, and the repository data files the route reads without a
blob binding. Unrelated publisher-repository commits remain admissible only
while this entire closure is byte-identical; the exact checkout revision is
recorded.

## Remaining limits

The workflow opts into a separate `szl.lyte.canonical-delegation-failure/v1`
receipt with `--failure-output` when verification fails. Its state is `BLOCKED`,
source authority is unverified, and no provider write or runtime acceptance is
asserted. It records the failed stage and hashes of inputs already read before
the failure. It does not claim checkout identities or run any new subprocess,
source read or network request during failure handling. Exception text and
source contents are excluded. The original exception still exits nonzero, and
the workflow attempts artifact retention even after failure. Without this
explicit option, the CLI still writes no receipt on rejected admission. The
failure and admitted output paths must differ. A failure receipt does not admit
a new publisher blob or replace the review required below.


- Exact blob binding means any change to any of these 23 files, including
  unrelated Terra, Finance or vertical-services edits, turns this verifier red
  until it is reviewed again.
- Data inputs are disclosed, not bound. These are the Terra forge bundle under
  `deployments/vertical-forge/terra/`, the Finance component manifests under
  `verticals/puriq-markets/runtime/components/`, the run's own flagship receipt, `scripts/hf_vertical_native.css`, and the
  canonical design/icon data under `console/assets/szl/`. The descriptor-based
  native asset reads are not enumerated in `unbound_data_references`; this
  admission discloses them explicitly. The publishers parse them as data and check the Terra bundle's
  hash chain themselves.
- Out of scope: the external controller bytes (pinned by blob inside admitted
  code), the `vertical-services` and `lyte-services` sources, third-party
  actions and the `huggingface_hub` package.
- The derivation is static. It cannot see paths passed indirectly through
  helper parameters from non-literal sources, so exact-blob review remains the
  authority for that. The same applies to dynamic namespace writes
  (`globals()[...]`, `exec`), attribute names computed on objects other than
  a listing module, in-process environment mutation before the scope read,
  and what each dispatch branch's call does once reached.
- The generated-flagship publisher runs before Lyte in the same process and can
  poll for up to 30 minutes inside a 50-minute job. That is an availability
  risk for the Lyte publication, not an authority change.
- This admission records what the route does. It does not approve the sibling
  writers' create-on-absence or non-atomic per-file uploads for the other
  Spaces.

No provider code is executed by this presentation verifier. Its source checks,
current-tip recheck, canonical-target policy, read-only permissions, and
prohibition on local publisher credentials remain required. The retired
`SZLHOLDINGS/lyte-lattice` Space remains retired. A successful delegation receipt
establishes source ownership only, not runtime readiness or live deployment.
